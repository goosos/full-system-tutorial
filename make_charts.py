"""make_charts.py — diagrams for Part 10."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# 1. Pipeline flowchart
fig, ax = plt.subplots(figsize=(12, 3))
ax.set_xlim(0, 10)
ax.set_ylim(0, 2)
ax.axis("off")

stages = [
    (0.5, "data.py\nClean"),
    (1.6, "backtest.py\nTest"),
    (2.7, "costs.py\nHonest costs"),
    (3.8, "metrics.py\nFull picture"),
    (4.9, "validation.py\nWalk-forward"),
    (6.0, "overfitting.py\nDSR / PBO"),
    (7.1, "sizing.py\nHow much"),
    (8.2, "portfolio.py\nCombine"),
    (9.3, "robustness.py\nPlateau?"),
]
for x, label in stages:
    box = mpatches.FancyBboxPatch((x - 0.45, 0.5), 0.9, 1.0,
                                  boxstyle="round,pad=0.05",
                                  facecolor="#1a2332", edgecolor="#4a9eff",
                                  linewidth=1.5)
    ax.add_patch(box)
    ax.text(x, 1.0, label, ha="center", va="center", fontsize=8,
            color="white", weight="bold")
    if x > 0.5:
        ax.annotate("", xy=(x - 0.45, 1.0), xytext=(x - 0.65, 1.0),
                    arrowprops=dict(arrowstyle="->", color="#4a9eff", lw=1.5))

ax.set_title("The Quant Research Pipeline — 9 stages, 7 modules, 1 verdict",
             fontsize=12, weight="bold", color="white", pad=15)
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#0d1117")
plt.tight_layout()
plt.savefig("pipeline_flow.png", dpi=150, facecolor="#0d1117",
            bbox_inches="tight")
print("pipeline_flow.png saved")

# 2. Final verdict scorecard
fig2, ax2 = plt.subplots(figsize=(10, 4))
ax2.set_xlim(0, 10)
ax2.set_ylim(0, 6)
ax2.axis("off")

checks = [
    ("Positive net return (+26.9%)", True),
    ("Walk-forward OOS Sharpe +2.10", True),
    ("Deflated Sharpe 0.85 (> 0.5)", True),
    ("PBO 0.75 (< 0.5 needed)", False),
    ("On a plateau, not a peak (100%)", True),
]
for i, (label, ok) in enumerate(checks):
    y = 5 - i
    color = "#3fb950" if ok else "#f85149"
    symbol = "✓" if ok else "✗"
    ax2.add_patch(mpatches.Circle((0.7, y), 0.28, facecolor=color,
                                  edgecolor="white", linewidth=1))
    ax2.text(0.7, y, symbol, ha="center", va="center", fontsize=14,
             color="white", weight="bold")
    ax2.text(1.3, y, label, ha="left", va="center", fontsize=11,
             color="white")

ax2.text(5, 0.3, "4/5 PASS  →  MARGINAL: paper-trade first",
         ha="center", fontsize=13, weight="bold", color="#d29922",
         bbox=dict(boxstyle="round,pad=0.4", facecolor="#1a2332",
                   edgecolor="#d29922"))
ax2.set_title("Pipeline Verdict: MA(20,50) on SPY",
              fontsize=13, weight="bold", color="white", pad=12)
fig2.patch.set_facecolor("#0d1117")
ax2.set_facecolor("#0d1117")
plt.tight_layout()
plt.savefig("verdict_scorecard.png", dpi=150, facecolor="#0d1117",
            bbox_inches="tight")
print("verdict_scorecard.png saved")
