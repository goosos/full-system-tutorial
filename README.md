# Full System Tutorial (Part 10)

**Part 10 of [Build Your Own Quant Research System](https://goosos.com) — the capstone.**

No new module. No new theory. Just assembly: `research_pipeline.py` runs
MA(20,50) on SPY through all nine stages of the series — data to verdict —
in one command.

## What it does

```
[0] data         load & clean SPY (data.py)
[1] backtest     MA(20,50), gross (backtest.py)
[2] costs        honest tier (costs.py)
[3] metrics      full table (metrics.py)
[4] validation   walk-forward OOS (validation.py)
[5] overfitting  DSR + PBO (overfitting.py)
[6] sizing       Kelly check (sizing.py)
[7] portfolio    + RSI diversifier (portfolio.py)
[8] robustness   plateau test (robustness.py)
```

Final verdict on our MA strategy: **4/5 checks passed → MARGINAL**
(paper-trade first). The pipeline works as designed.

## Run it

```bash
pip install -r requirements.txt
python research_pipeline.py
```

Takes ~2-3 minutes (downloads SPY data on first run).

## Files

| File | What |
|---|---|
| `research_pipeline.py` | The full pipeline, one function per stage |
| `make_charts.py` | Generates the two article diagrams |
| `article.md` | The tutorial text |
| `pipeline_output.txt` | Reference output from a real run |

## Dependencies

The pipeline imports all seven toolkit modules. For this standalone repo,
the module files are vendored alongside `research_pipeline.py`
(`backtest.py`, `data.py`, `validation.py`, `overfitting.py`,
`metrics.py`, `costs.py`, `sizing.py`, `portfolio.py`, `robustness.py`,
plus the `quant_toolkit` package). In the real toolkit they live in
[goosos/quant-toolkit](https://github.com/goosos/quant-toolkit).

## Article

**[From Zero to Research System: Putting It All Together](https://goosos.com/assembling-full-quant-system)**
