"""
Config-driven reconciliation engine.

1. Load each source into DuckDB and add a normalised key column (`key_norm`).
2. Run every check in config/reconciliation.yml. Each check is a SQL file that returns
   (encounter_id, detail, amount_impact); the engine attaches severity, owner, root cause and
   recommended action from the config, so every exception explains itself.
3. Run the department tie-out and decide the release gate: PASS only if no blocking exceptions
   and every department total is within tolerance.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "reconciliation.yml"


@dataclass
class Result:
    exceptions: pd.DataFrame
    summary: pd.DataFrame
    tieout: pd.DataFrame
    gate_passed: bool
    gate_reasons: list[str]
    source_counts: dict


def load_config(path: Path = CONFIG) -> dict:
    return yaml.safe_load(path.read_text())


def connect(cfg: dict, root: Path = ROOT) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    norm = cfg["key_normalisation"]
    for name, src in cfg["sources"].items():
        path = (root / src["file"]).as_posix()
        if "key" in src:
            con.execute(f"create table {name} as select *, {norm.format(col=src['key'])} as key_norm "
                        f"from read_csv_auto('{path}')")
        else:
            con.execute(f"create table {name} as select * from read_csv_auto('{path}')")
    return con


def render(sql_path: Path, cfg: dict) -> str:
    return (ROOT / sql_path).read_text().format(
        amount_abs=cfg["tolerance"]["amount_abs"],
        period_start=cfg["period"]["start"], period_end=cfg["period"]["end"])


def run(cfg: dict | None = None, root: Path = ROOT) -> Result:
    cfg = cfg or load_config()
    con = connect(cfg, root)
    counts = {n: con.execute(f"select count(*) from {n}").fetchall()[0][0] for n in cfg["sources"]}

    frames, rows = [], []
    for chk in cfg["checks"]:
        df = con.execute(render(Path(chk["sql"]), cfg)).df()
        for field in ("severity", "owner", "root_cause", "action"):
            df[field] = chk[field]
        df.insert(0, "check", chk["id"])
        frames.append(df)
        rows.append({"check": chk["id"], "severity": chk["severity"], "owner": chk["owner"],
                     "exceptions": len(df), "amount_impact": round(float(df["amount_impact"].abs().sum()), 2),
                     "blocks_release": chk["id"] in cfg["release_gate"]["block_on"] and len(df) > 0})
    exceptions = pd.concat(frames, ignore_index=True)
    summary = pd.DataFrame(rows)

    tieout = con.execute(render(Path("sql/10_dept_tieout.sql"), cfg)).df()
    limit = cfg["release_gate"]["max_total_variance_pct"]
    reasons = [f"{r.check}: {r.exceptions} blocking exception(s)" for r in summary.itertuples() if r.blocks_release]
    for r in tieout.itertuples():
        for col in ("billing_variance_pct", "finance_variance_pct"):
            v = getattr(r, col)
            if pd.isna(v) or abs(v) > limit:
                reasons.append(f"{r.dept} {col.split('_')[0]} total off by {v}% (limit {limit}%)")
    return Result(exceptions, summary, tieout, not reasons, reasons, counts)
