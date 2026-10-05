"""A conditional postcondition must never be admitted with a replay gap."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
CASES = (
    (ROOT / "test/repro/minimal_conditional_ensure_replay_gap.elisa", {"certificates": 2, "replayed": 2, "gaps": 0}),
    (ROOT / "test/repro/minimal_conditional_positive_conjunct_replay.elisa", {"certificates": 2, "replayed": 2, "gaps": 0}),
    (ROOT / "test/repro/minimal_conditional_signed_unit_shift_replay.elisa", {"certificates": 2, "replayed": 2, "gaps": 0}),
    (ROOT / "test/repro/minimal_conditional_signed_unit_shift_near_max.elisa", {"certificates": 2, "replayed": 2, "gaps": 0}),
    (ROOT / "test/repro/minimal_slide_inner_replay_gap.elisa", {"certificates": 6, "replayed": 6, "gaps": 0}),
)

reports = {}
for source, current_replay in CASES:
    run = subprocess.run([BINARY, "--json", str(source)], capture_output=True, text=True, timeout=20)
    report = json.loads(run.stdout)
    reports[source.name] = report
    replay = report["replay"]
    declaration = next(
        item for item in report["declaration_details"]
        if item.get("kind") == "function" and item.get("name") == "inner"
    )

    if replay["gaps"]:
        # Keep each current gap explicitly refused; a future fix must replay all certificates.
        assert report["status"] == "proved_with_replay_gaps", (source, report)
        assert run.returncode == 1, (source, run.returncode, report["status"])
        assert replay == current_replay, (source, replay)
        assert report["verification_state"] != "proved", (source, report["verification_state"])
        assert declaration["verified"] is False, (source, declaration)
        assert declaration["verification_reason"] == "replay-gap", (source, declaration)
    else:
        assert report["status"] == "proved", (source, report["status"])
        assert run.returncode == 0, (source, run.returncode, report["status"])
        assert replay["certificates"] == replay["replayed"], (source, replay)
        assert declaration["verified"] is True, (source, declaration)

slide_roots = {item.get("kernel_goal"): item.get("replayed")
               for item in reports["minimal_slide_inner_replay_gap.elisa"]["certificates"]}
assert slide_roots[48] is True and slide_roots[51] is True, slide_roots

bad_source = ROOT / "test/repro/minimal_conditional_ensure_bad_guard.elisa"
bad_run = subprocess.run([BINARY, "--json", str(bad_source)], capture_output=True, text=True, timeout=20)
bad_report = json.loads(bad_run.stdout)
bad_declaration = next(
    item for item in bad_report["declaration_details"]
    if item.get("kind") == "function" and item.get("name") == "inner"
)
assert bad_run.returncode == 1, (bad_source, bad_run.returncode, bad_report["status"])
assert bad_report["status"] == "failed", (bad_source, bad_report["status"])
assert bad_report["replay"]["gaps"] == 0, (bad_source, bad_report["replay"])
assert bad_declaration["verified"] is False, (bad_source, bad_declaration)
assert any(
    item.get("kind") == "ensure-unproven" and item.get("name") == "inner"
    for item in bad_report["findings"]
), (bad_source, bad_report["findings"])

for name in ("minimal_conditional_missing_conjunct_refusal.elisa",
             "minimal_conditional_overflow_refusal.elisa",
             "minimal_conditional_signed_unit_shift_wrong_bound_refusal.elisa",
             "minimal_conditional_signed_unit_shift_overflow_guard_refusal.elisa",
             "minimal_conditional_signed_unit_shift_missing_premise_refusal.elisa",
             "minimal_conditional_signed_unit_shift_near_max_refusal.elisa",
             "minimal_conditional_signed_unit_shift_near_min_refusal.elisa",
             "minimal_conditional_signed_unit_shift_wrong_width_refusal.elisa",
             "minimal_conditional_signed_unit_shift_wrong_sort_refusal.elisa"):
    source = ROOT / "test/repro" / name
    run = subprocess.run([BINARY, "--json", str(source)], capture_output=True, text=True, timeout=20)
    report = json.loads(run.stdout)
    declaration = next(
        item for item in report["declaration_details"]
        if item.get("kind") == "function" and item.get("name") == "inner"
    )
    expected_status = "proved_with_replay_gaps" if name == "minimal_conditional_signed_unit_shift_wrong_sort_refusal.elisa" else "failed"
    assert run.returncode == 1 and report["status"] == expected_status, (source, report)
    # The unsigned-sort mutation currently exposes a producer/replay disagreement: the
    # producer emits an unsigned certificate, which independent replay rejects. Keep that
    # visible as a gap while still checking fail-closed admission. All signed controls must
    # replay completely so their refusal comes from the proof obligation, not a replay gap.
    if name == "minimal_conditional_signed_unit_shift_wrong_sort_refusal.elisa":
        assert report["verification_state"] != "proved", (source, report["verification_state"])
        assert report["declaration_details"][0]["verification_reason"] == "replay-gap", report["declaration_details"][0]
    else:
        assert report["replay"]["gaps"] == 0 and report["replay"]["certificates"] == report["replay"]["replayed"], (source, report["replay"])
        assert declaration["verification_reason"] != "replay-gap", (source, declaration)
    assert declaration["verified"] is False, (source, declaration)
    if name != "minimal_conditional_signed_unit_shift_wrong_sort_refusal.elisa":
        assert any(item.get("kind") == "ensure-unproven" and item.get("name") == "inner"
                   for item in report["findings"]), (source, report["findings"])

print("positive conditional conjunct and range-checked signed unit shift replay; Slide.inner roots 48 and 51 close; missing-conjunct, premise, overflow, near-min/max, wrong-width, wrong-sort and wrong-bound controls remain unadmitted")
