import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from recon.engine import load_config, run  # noqa: E402
from recon.report import evaluate  # noqa: E402

spec = importlib.util.spec_from_file_location("generate", ROOT / "data" / "generate.py")
generate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate)


def config_for(folder: Path) -> dict:
    cfg = load_config()
    for name, src in cfg["sources"].items():
        src["file"] = str(folder / Path(src["file"]).name)
    return cfg


@pytest.fixture(scope="module")
def dirty(tmp_path_factory):
    d = tmp_path_factory.mktemp("dirty")
    generate.main(out=d, inject=True)
    return d, run(config_for(d), root=Path("/"))


def test_clean_data_passes_the_release_gate(tmp_path):
    generate.main(out=tmp_path, inject=False)
    r = run(config_for(tmp_path), root=Path("/"))
    assert r.gate_passed, r.gate_reasons
    assert len(r.exceptions) == 0


def test_every_injected_issue_is_caught_with_no_false_positives(dirty):
    folder, r = dirty
    ev = evaluate(r, folder / "ground_truth.csv")
    assert (ev.recall == 1.0).all() and (ev.precision == 1.0).all()


def test_rounding_inside_tolerance_is_not_an_exception(dirty):
    _, r = dirty
    assert (r.exceptions.query("check == 'amount_mismatch'").amount_impact.abs() > 0.05).all()


def test_key_format_drift_is_explained_not_reported_as_missing(dirty):
    folder, r = dirty
    import pandas as pd
    drifted = set(pd.read_csv(folder / "ground_truth.csv").query("issue_type == 'key_format'").encounter_id)
    missing = set(r.exceptions.query("check == 'missing_in_billing'").encounter_id)
    assert drifted and not drifted & missing
    assert len(r.exceptions.query("check == 'orphan_claim'")) == 0


def test_dirty_data_fails_the_gate_for_the_right_reasons(dirty):
    _, r = dirty
    assert not r.gate_passed
    assert any("duplicate_claim" in x for x in r.gate_reasons)
    assert any("status_conflict" in x for x in r.gate_reasons)
