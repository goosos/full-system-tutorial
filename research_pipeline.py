"""
research_pipeline.py — the full Part 1-9 pipeline in one script.

Runs MA(20,50) on SPY through every stage of the series:

    Stage 0  data.py        load & clean prices
    Stage 1  backtest.py    vectorized backtest, honest costs
    Stage 2  costs.py       TradeCost honesty tiers
    Stage 3  metrics.py     full metrics table (beyond Sharpe)
    Stage 4  validation.py  walk-forward out-of-sample check
    Stage 5  overfitting.py Deflated Sharpe + PBO (selection bias)
    Stage 6  sizing.py      Kelly / fixed-fractional sizing
    Stage 7  portfolio.py   combine with RSI(14) diversifier
    Stage 8  robustness.py  plateau vs peak check

Each stage prints its verdict. The final verdict is printed at the end.

Usage:
    python research_pipeline.py          # runs everything (~2-3 min)
"""
import sys
import numpy as np
import pandas as pd
import vectorbt as vbt

sys.path.insert(0, ".")
from quant_toolkit.data import load_and_clean
from quant_toolkit.backtest import run_backtest, ma_crossover_signals
from quant_toolkit.validation import run_walk_forward
from costs import TradeCost, COST_TIERS
from metrics import metrics_table
from overfitting import deflated_sharpe, pbo
from sizing import half_kelly, fixed_fractional
from portfolio import strategy_corr_matrix, sharpe_weight, combine_returns
from robustness import plateau_neighbors

SYMBOL = "SPY"
START = "2023-10-09"
FAST, SLOW = 20, 50

results = {}


def stage0_data():
    df = load_and_clean(SYMBOL, start=START)
    price = df["Close"]
    if hasattr(price, "iloc") and price.ndim > 1:
        price = price.iloc[:, 0]
    n = len(price)
    print(f"[0] data: {SYMBOL} daily, {n} bars, "
          f"{price.index[0].date()} -> {price.index[-1].date()}")
    results["price"] = price
    results["n"] = n


def stage1_backtest():
    price = results["price"]
    entries, exits = ma_crossover_signals(price, FAST, SLOW)
    pf = run_backtest(price, entries, exits)
    rets = pd.Series(np.asarray(pf.returns()).ravel(), index=price.index)
    results["returns"] = rets
    results["n_trades"] = int(pf.trades.count())
    gross = float(pf.total_return())
    print(f"[1] backtest: MA({FAST},{SLOW}) gross return {gross:+.2%}, "
          f"{results['n_trades']} trades")


def stage2_costs():
    honest = COST_TIERS["honest"]
    price = results["price"]
    entries, exits = ma_crossover_signals(price, FAST, SLOW)
    pf = run_backtest(price, entries, exits, **honest.to_backtest_kwargs())
    rets = pd.Series(np.asarray(pf.returns()).ravel(), index=price.index)
    results["returns"] = rets  # net of honest costs from here on
    net = float(pf.total_return())
    print(f"[2] costs: honest tier ({honest.round_trip_pct()*1e4:.0f} bps "
          f"round-trip) -> net return {net:+.2%}")
    results["net_return"] = net


def stage3_metrics():
    t = metrics_table(results["returns"])
    results["metrics"] = t
    print(f"[3] metrics: Sharpe {t['sharpe']:+.2f} | "
          f"Sortino {t['sortino']:+.2f} | Calmar {t['calmar']:+.2f} | "
          f"maxDD {t['max_drawdown']:.2%} ({t['max_drawdown_duration_bars']} bars)")


def stage4_validation():
    price = results["price"]
    entries, exits = ma_crossover_signals(price, FAST, SLOW)
    n = len(price)
    wf = run_walk_forward(price, entries, exits,
                          train_size=n // 2, test_size=n // 4,
                          **COST_TIERS["honest"].to_backtest_kwargs())
    oos = wf["sharpe"].mean()
    results["oos_sharpe"] = oos
    verdict = "holds up" if oos > 0 else "BREAKS out-of-sample"
    print(f"[4] validation: {len(wf)} walk-forward folds, "
          f"mean OOS Sharpe {oos:+.2f} -> {verdict}")


def _trial_grid():
    """Small MA grid: trial Sharpes + returns matrix for stages 5 & 8."""
    price = results["price"]
    fasts = [15, 20, 25, 30]
    slows = [40, 50, 60, 70]
    sharpes, rets_list, params = [], [], []
    kw = COST_TIERS["honest"].to_backtest_kwargs()
    for f in fasts:
        for s in slows:
            if f >= s:
                continue
            e, x = ma_crossover_signals(price, f, s)
            pf = run_backtest(price, e, x, **kw)
            r = pd.Series(np.asarray(pf.returns()).ravel(), index=price.index)
            sr = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0
            sharpes.append(sr)
            rets_list.append(r.values)
            params.append((f, s))
    results["trial_sharpes"] = np.array(sharpes)
    results["trial_returns"] = np.array(rets_list)
    results["trial_params"] = params
    return sharpes


def stage5_overfitting():
    sharpes = _trial_grid()
    best = max(sharpes)
    dsr = deflated_sharpe(best, sharpes, results["n"])
    pb = pbo(results["trial_returns"], n_partitions=8)
    results["dsr"] = dsr
    results["pbo"] = pb["pbo"]
    print(f"[5] overfitting: {len(sharpes)} trials, best Sharpe {best:+.2f} "
          f"-> DSR {dsr:.2f}, PBO {pb['pbo']:.2f}")


def stage6_sizing():
    r = results["returns"]
    wins = r[r > 0]
    win_prob = len(wins) / (r != 0).sum()
    b = wins.mean() / (-r[r < 0].mean())
    hk = half_kelly(win_prob, b)
    size = fixed_fractional(100_000, 0.5)
    results["half_kelly"] = hk
    print(f"[6] sizing: win rate {win_prob:.0%}, half-Kelly {hk:.1%}, "
          f"fixed 50% on $100k = ${size:,.0f}")


def _rsi_signals(price, window=14, oversold=30, overbought=70):
    rsi = vbt.RSI.run(price, window=window).rsi
    entries = rsi.vbt.crossed_above(oversold).vbt.signals.fshift(1)
    exits = rsi.vbt.crossed_below(overbought).vbt.signals.fshift(1)
    return entries, exits


def stage7_portfolio():
    price = results["price"]
    kw = COST_TIERS["honest"].to_backtest_kwargs()

    def strat_rets(entries, exits):
        pf = run_backtest(price, entries, exits, **kw)
        return pd.Series(np.asarray(pf.returns()).ravel(), index=price.index)

    e, x = ma_crossover_signals(price, FAST, SLOW)
    ma_rets = strat_rets(e, x)
    e, x = _rsi_signals(price)
    rsi_rets = strat_rets(e, x)

    corr = strategy_corr_matrix({"MA": ma_rets, "RSI": rsi_rets})
    rho = corr.loc["MA", "RSI"]
    w = sharpe_weight([results["metrics"]["sharpe"],
                       float(ma_rets.mean() / ma_rets.std() * np.sqrt(252))
                       if ma_rets.std() > 0 else 0.0])
    port = combine_returns({"MA": ma_rets, "RSI": rsi_rets}, w)
    psr = float(port.mean() / port.std() * np.sqrt(252))
    results["portfolio_sharpe"] = psr
    print(f"[7] portfolio: MA/RSI correlation {rho:+.2f}, "
          f"weights {[f'{v:.2f}' for v in w]} -> portfolio Sharpe {psr:+.2f}")


def stage8_robustness():
    import pandas as _pd

    grid = _pd.DataFrame({
        "fast": [p[0] for p in results["trial_params"]],
        "slow": [p[1] for p in results["trial_params"]],
        "sharpe": results["trial_sharpes"],
    }).pivot(index="slow", columns="fast", values="sharpe")
    nb_frac, nb_verdict = plateau_neighbors(grid, param=(SLOW, FAST),
                                              frac=0.9, radius=1,
                                              reference="local")
    frac = nb_frac
    verdict = "PLATEAU" if nb_verdict == "plateau" else nb_verdict.upper()
    results["plateau_frac"] = frac
    print(f"[8] robustness: {frac:.0%} of MA({FAST},{SLOW}) neighbors "
          f"within 90% -> {verdict}")


def final_verdict():
    m = results["metrics"]
    checks = [
        ("positive net return", results["net_return"] > 0),
        ("OOS Sharpe > 0", results["oos_sharpe"] > 0),
        ("DSR > 0.5 (better than coin flip)", results["dsr"] > 0.5),
        ("PBO < 0.5 (selection not random)", results["pbo"] < 0.5),
        ("on a plateau, not a peak", results["plateau_frac"] >= 0.8),
    ]
    print("\n=== FINAL VERDICT: MA(20,50) on SPY ===")
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    n_pass = sum(ok for _, ok in checks)
    print(f"\n  {n_pass}/{len(checks)} checks passed.")
    if n_pass == len(checks):
        print("  Verdict: TRADEABLE with half-Kelly sizing "
              f"({results['half_kelly']:.0%}) and honest costs.")
    elif n_pass >= 3:
        print("  Verdict: MARGINAL — paper-trade first, "
              "re-check in 6 months.")
    else:
        print("  Verdict: NOT TRADEABLE — the pipeline caught it "
              "before your money did.")
    print(f"\n  Portfolio kicker: MA+RSI Sharpe "
          f"{results['portfolio_sharpe']:+.2f} vs single "
          f"{m['sharpe']:+.2f}.")


def main():
    stage0_data()
    stage1_backtest()
    stage2_costs()
    stage3_metrics()
    stage4_validation()
    stage5_overfitting()
    stage6_sizing()
    stage7_portfolio()
    stage8_robustness()
    final_verdict()


if __name__ == "__main__":
    main()
