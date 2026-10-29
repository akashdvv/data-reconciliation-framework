"""
Run the month-end reconciliation and write the release report.

    python data/generate.py          # once: create the three source extracts
    python run_reconciliation.py     # -> reports/reconciliation_2026-09.xlsx and .md
"""
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from recon.engine import ROOT, run
from recon.report import evaluate, write_excel, write_markdown

BLUE, RED, INK_2, GRID = "#2a78d6", "#e34948", "#52514e", "#e4e3df"


def chart(summary) -> None:
    s = summary[summary.exceptions > 0].sort_values("amount_impact")
    fig, ax = plt.subplots(figsize=(9, 3.8))
    colors = [RED if b else BLUE for b in s.blocks_release]
    ax.barh(s["check"], s.amount_impact / 1000, color=colors, height=0.6)
    for y, (amt, n) in enumerate(zip(s.amount_impact, s.exceptions)):
        ax.text(amt / 1000 + 0.6, y, f"${amt / 1000:,.1f}K  ({n})", va="center", fontsize=9, color=INK_2)
    ax.set_xlabel("Dollar impact ($K); red = blocks report release")
    ax.set_title("Exceptions by check, September 2026 close", loc="left", fontweight="bold")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.set_xlim(0, s.amount_impact.max() / 1000 * 1.3)
    ax.xaxis.grid(True, color=GRID)
    ax.set_axisbelow(True)
    fig.tight_layout()
    (ROOT / "images").mkdir(exist_ok=True)
    fig.savefig(ROOT / "images" / "exceptions_by_check.png", dpi=150)


def main() -> int:
    result = run()
    evaluation = evaluate(result)
    (ROOT / "reports").mkdir(exist_ok=True)
    write_excel(result, ROOT / "reports" / "reconciliation_2026-09.xlsx")
    print(write_markdown(result, evaluation, ROOT / "reports" / "reconciliation_2026-09.md"))
    chart(result.summary)
    return 0 if result.gate_passed else 1     # non-zero exit lets a scheduler stop downstream reports


if __name__ == "__main__":
    sys.exit(main())
