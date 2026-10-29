"""
Reporting: a formatted Excel workbook for stakeholders, a Markdown summary, and an
evaluation against the generator's ground truth.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from recon.engine import ROOT, Result

HEADER = PatternFill("solid", fgColor="1F3A5F")
RED, GREEN, AMBER = PatternFill("solid", fgColor="F8D7DA"), PatternFill("solid", fgColor="D4EDDA"), PatternFill("solid", fgColor="FFF3CD")


def evaluate(result: Result, truth_path: Path = ROOT / "data" / "ground_truth.csv") -> pd.DataFrame:
    """Detection recall / precision per issue type (check id == injected issue type)."""
    truth = pd.read_csv(truth_path)
    rows = []
    for issue, g in truth.groupby("issue_type"):
        found = set(result.exceptions.loc[result.exceptions["check"] == issue, "encounter_id"])
        expected = set(g["encounter_id"])
        tp = len(found & expected)
        rows.append({"issue_type": issue, "injected": len(expected), "flagged": len(found), "caught": tp,
                     "recall": tp / len(expected), "precision": tp / len(found) if found else float("nan")})
    return pd.DataFrame(rows)


def _style(ws, widths: dict[int, int] | None = None) -> None:
    for c in ws[1]:
        c.fill, c.font = HEADER, Font(color="FFFFFF", bold=True)
        c.alignment = Alignment(vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    for i, col in enumerate(ws.columns, 1):
        width = (widths or {}).get(i) or min(60, max(10, max(len(str(c.value or "")) for c in col) + 2))
        ws.column_dimensions[get_column_letter(i)].width = width


def write_excel(result: Result, path: Path) -> None:
    gate = pd.DataFrame({"item": ["Release gate", "Period", "EHR encounters", "Billing claims", "Finance payments",
                                  "Total exceptions", "Blocking reasons"],
                         "value": ["PASS" if result.gate_passed else "FAIL - do not publish reports",
                                   "2026-09-01 to 2026-09-30", result.source_counts["ehr"],
                                   result.source_counts["billing"], result.source_counts["finance"],
                                   len(result.exceptions), "; ".join(result.gate_reasons) or "none"]})
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        gate.to_excel(xw, sheet_name="Release gate", index=False)
        result.summary.to_excel(xw, sheet_name="Checks summary", index=False)
        result.exceptions.to_excel(xw, sheet_name="Exceptions", index=False)
        result.tieout.to_excel(xw, sheet_name="Dept tie-out", index=False)
    wb = load_workbook(path)
    _style(wb["Release gate"], {1: 22, 2: 110})
    wb["Release gate"]["B2"].fill = GREEN if result.gate_passed else RED
    _style(wb["Checks summary"])
    ws = wb["Checks summary"]
    for row in ws.iter_rows(min_row=2):
        if row[5].value is True:
            for c in row:
                c.fill = RED
    _style(wb["Exceptions"], {4: 14, 8: 55, 9: 45})
    _style(wb["Dept tie-out"])
    ws = wb["Dept tie-out"]
    n = ws.max_row
    for col in ("F", "G"):
        ws.conditional_formatting.add(f"{col}2:{col}{n}", CellIsRule(operator="notBetween", formula=["-0.5", "0.5"], fill=AMBER))
    wb.save(path)


def write_markdown(result: Result, evaluation: pd.DataFrame, path: Path) -> str:
    lines = [f"# Month-end reconciliation - September 2026", "",
             f"**Release gate: {'PASS' if result.gate_passed else 'FAIL - hold reports'}**", ""]
    lines += [f"- {r}" for r in result.gate_reasons] + [""]
    lines += ["| Check | Severity | Owner | Exceptions | $ impact | Blocks release |", "|---|---|---|---|---|---|"]
    for r in result.summary.itertuples():
        lines.append(f"| {r.check} | {r.severity} | {r.owner} | {r.exceptions} | ${r.amount_impact:,.0f} | {'yes' if r.blocks_release else ''} |")
    lines += ["", "## Detection vs. injected ground truth", "",
              "| Issue | Injected | Flagged | Caught | Recall | Precision |", "|---|---|---|---|---|---|"]
    for r in evaluation.itertuples():
        lines.append(f"| {r.issue_type} | {r.injected} | {r.flagged} | {r.caught} | {r.recall:.0%} | {r.precision:.0%} |")
    text = "\n".join(lines) + "\n"
    path.write_text(text)
    return text
