"""Catch malformed indentation in bounded report serialization scans."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / "src/app/report_output_serialization_helpers.elisa").read_text(encoding="utf-8")

assert "-> (complete: bool, index: usize):\n    for candidate in 0..<names.count" in text
assert "-> (complete: bool, contains: bool):\n    for prior in 0..<count" in text
assert "\n        return (false, names.count) if not proof_replay_fact_origin_text_compare_charge(names[candidate], name, work)" in text
assert "\n        return (false, false) if not proof_replay_fact_origin_work_charge(1, work)" in text

print("report serialization loop layout: bounded scans remain correctly nested")
