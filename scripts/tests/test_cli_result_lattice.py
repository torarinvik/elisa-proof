"""Selected-proof CLI results are successful only for complete, admitted kernel proofs."""

import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / "build/elisa-proof"


def invoke(*args):
    return subprocess.run([str(BINARY), *map(str, args)], capture_output=True, text=True, timeout=90)


def report_for(source):
    result = invoke("--json", source)
    report = json.loads(result.stdout)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as handle:
        handle.write(result.stdout)
        handle.flush()
        classified = subprocess.run(
            ["python3", str(ROOT / "scripts/report_exit_status.py"), handle.name],
            capture_output=True, text=True, timeout=30,
        )
    assert classified.returncode == 0, classified.stderr
    assert result.returncode == int(classified.stdout.strip()), (result.returncode, report)
    return result.returncode, report


def check(block, source):
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".proof") as handle:
        handle.write(block)
        handle.flush()
        result = invoke("--check-proof", handle.name, source)
    return result.returncode, json.loads(result.stdout)


# Pick two independently proved source files with a common goal index. The first exercises a
# complete/admissible success; the second makes the first file's otherwise-valid block foreign.
complete_sources = []
for name in ("early_return_index_guard.elisa", "verified.elisa", "comparison_chain.elisa"):
    source = ROOT / "examples" / name
    code, report = report_for(source)
    proven = [goal for goal in report["goals"] if goal["proven"]]
    if code == 0 and report.get("verification_state") == "proved" and proven:
        complete_sources.append((source, report, proven))
assert complete_sources, "need a complete, source-admissible positive fixture"
positive_source, positive_report, positive_goals = complete_sources[0]
selected_goal = next((goal for goal in positive_goals if goal["rule"] == "index-upper"), positive_goals[0])
selected = selected_goal["goal_id"]

plain_complete = invoke(positive_source)
assert plain_complete.returncode == 0 and "verification state: proved" in plain_complete.stdout, plain_complete.stdout

goal_result = invoke("--goal", selected, positive_source)
goal_json = json.loads(goal_result.stdout)
assert goal_result.returncode == 0 and goal_json["status"] == "proved", goal_json
assert goal_json["goal"]["proven"] is True and goal_json["goal"]["replay_status"] == "replayed", goal_json

proof_result = invoke("--proof", selected, positive_source)
assert proof_result.returncode == 0, proof_result.stderr
proof_text = proof_result.stdout
assert f"\nproof {selected_goal['name']}_{selected}:\n" in proof_text, proof_text
assert "\nqed\n" in proof_text and "by kernel certificate" in proof_text, proof_text
if selected_goal["rule"] == "index-upper":
    assert "    show index < values.count\n" in proof_text, proof_text
    assert "    given not (index >= values.count)" in proof_text, proof_text
    assert "branch-condition" in proof_text, proof_text
check_code, faithful = check(proof_text, positive_source)
assert check_code == 0 and faithful["status"] == "matches", faithful
assert faithful["verification_state"] == "proved" and faithful["difference_count"] == 0, faithful

# This fixture intentionally has a replayed selected goal and unrelated open obligations. An
# incomplete source may not turn even that selected certificate into a CLI success.
partial_source = ROOT / "examples" / "tactic_repair_target.elisa"
partial_code, partial_report = report_for(partial_source)
assert partial_code == 1 and partial_report["verification_state"] != "proved", partial_report
plain_partial = invoke(partial_source)
assert plain_partial.returncode == 1 and "verification state: unknown" in plain_partial.stdout, plain_partial.stdout
partial_proven = next(goal for goal in partial_report["goals"] if goal["proven"])
open_goal = next(goal for goal in partial_report["goals"] if not goal["proven"])
partial_goal_result = invoke("--goal", partial_proven["goal_id"], partial_source)
partial_goal = json.loads(partial_goal_result.stdout)
assert partial_goal_result.returncode == 1 and partial_goal["status"] != "proved", partial_goal
assert partial_goal["goal"]["proven"] is False and partial_goal["goal"]["replay_status"] == "replayed", partial_goal

unsupported_source = ROOT / "examples" / "rejected_confined_lend_extent.elisa"
unsupported_code, unsupported_report = report_for(unsupported_source)
assert unsupported_code == 1 and unsupported_report["verification_state"] == "unsupported", unsupported_report
unsupported_goal = next(goal for goal in unsupported_report["goals"] if not goal["proven"])
unsupported_result = invoke("--goal", unsupported_goal["goal_id"], unsupported_source)
unsupported_json = json.loads(unsupported_result.stdout)
assert unsupported_result.returncode == 1 and unsupported_json["status"] != "proved", unsupported_json
assert unsupported_json["goal"]["proven"] is False, unsupported_json

partial_proof_result = invoke("--proof", partial_proven["goal_id"], partial_source)
assert partial_proof_result.returncode == 1, partial_proof_result.stdout
assert "\nunchecked " in partial_proof_result.stdout and "\nqed\n" not in partial_proof_result.stdout
incomplete_code, incomplete = check(partial_proof_result.stdout, partial_source)
assert incomplete_code == 1 and incomplete["status"] == "matches", incomplete
assert incomplete["verification_state"] != "proved", incomplete

open_proof_result = invoke("--proof", open_goal["goal_id"], partial_source)
assert open_proof_result.returncode == 1 and "\nopen " in open_proof_result.stdout
assert "\nqed\n" not in open_proof_result.stdout
open_check_code, open_check = check(open_proof_result.stdout, partial_source)
assert open_check_code == 1 and open_check["status"] == "matches", open_check
assert open_check["verification_state"] != "proved", open_check

# Any altered block, even one that retains a valid goal id or adds a plausible `qed`, is not a
# successful proof artifact. The check status distinguishes textual fidelity from proof status.
extra = proof_text.replace("    show ", "    given 999 == 1000\n    show ", 1)
extra_code, extra_check = check(extra, positive_source)
assert extra_code == 1 and extra_check["status"] == "diverges", extra_check
assert extra_check["verification_state"] != "proved" and extra_check["difference_count"] > 0, extra_check

forged = open_proof_result.stdout.replace("\nopen ", "\nproof ", 1)
forged = "\n".join(line for line in forged.splitlines() if not line.startswith("    unproved:")) + "\nqed\n"
forged_code, forged_check = check(forged, partial_source)
assert forged_code == 1 and forged_check["status"] == "diverges", forged_check
assert forged_check["verification_state"] != "proved", forged_check

with tempfile.TemporaryDirectory(prefix="elisa-proof-foreign-source-") as directory:
    foreign_source = Path(directory) / positive_source.name
    foreign_source.write_text(positive_source.read_text(encoding="utf-8") + "\n# distinct source identity\n", encoding="utf-8")
    foreign_source_code, foreign_source_report = report_for(foreign_source)
    assert foreign_source_code == 0 and foreign_source_report["verification_state"] == "proved", foreign_source_report
    foreign_code, foreign = check(proof_text, foreign_source)
assert foreign_code == 1 and foreign["status"] == "diverges", foreign
assert foreign["verification_state"] != "proved", foreign

missing_id = 999999999
missing_goal_result = invoke("--goal", missing_id, positive_source)
missing_goal = json.loads(missing_goal_result.stdout)
assert missing_goal_result.returncode == 2 and missing_goal["status"] == "not_found", missing_goal
missing_proof_result = invoke("--proof", missing_id, positive_source)
assert missing_proof_result.returncode == 2 and "does not exist" in missing_proof_result.stdout
missing_block = proof_text.replace(f"# goal {selected} of", f"# goal {missing_id} of", 1)
missing_check_code, missing_check = check(missing_block, positive_source)
assert missing_check_code == 2 and missing_check["status"] == "not_found", missing_check
assert missing_check["verification_state"] != "proved", missing_check

junk_code, junk = check("not a proof block\n", positive_source)
assert junk_code == 2 and junk["status"] == "unreadable", junk
assert junk["verification_state"] != "proved", junk

# A recorded certificate that failed replay is explicitly non-successful on every selected-proof
# surface, even when `--check-proof` confirms the renderer faithfully prints that gap.
gap_contract_source = ROOT / "examples" / "loop_counter_invariant.elisa"
gap_contract_code, gap_contract_report = report_for(gap_contract_source)
assert gap_contract_code == 1, gap_contract_report
assert gap_contract_report["status"] == "proved_with_replay_gaps", gap_contract_report
assert gap_contract_report["verification_state"] == "unknown", gap_contract_report
assert gap_contract_report["replay"]["gaps"] > 0, gap_contract_report
plain_gap = invoke(gap_contract_source)
assert plain_gap.returncode == 1 and "verification state: unknown" in plain_gap.stdout, plain_gap.stdout
assert " gaps" in plain_gap.stdout, plain_gap.stdout

gap_source = ROOT / "examples" / "condition_call_positions.elisa"
gap_code, gap_report = report_for(gap_source)
gap_goals = [goal for goal in gap_report["goals"] if goal["replay_status"] == "gap"]
assert gap_code == 1 and gap_goals, gap_report
gap_id = gap_goals[0]["goal_id"]
gap_goal_result = invoke("--goal", gap_id, gap_source)
gap_goal = json.loads(gap_goal_result.stdout)
assert gap_goal_result.returncode == 1 and gap_goal["status"] != "proved", gap_goal
assert gap_goal["goal"]["proven"] is False and gap_goal["goal"]["replay_status"] == "gap", gap_goal
gap_proof_result = invoke("--proof", gap_id, gap_source)
assert gap_proof_result.returncode == 1 and "\nunchecked " in gap_proof_result.stdout
assert "\nqed\n" not in gap_proof_result.stdout
gap_check_code, gap_check = check(gap_proof_result.stdout, gap_source)
assert gap_check_code == 1 and gap_check["status"] == "matches", gap_check
assert gap_check["verification_state"] != "proved", gap_check

print("CLI result lattice: proved-only success, exact match-vs-proof status, incomplete/open/gap and forged/foreign/junk/missing refusals verified")
