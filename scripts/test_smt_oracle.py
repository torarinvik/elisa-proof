"""SMT linear oracle (BACKLOG W-01): Z3 multipliers fed back through `--linear-hints`.

Positive: the fixture's eight-name goal is unproven alone and proves, replayed by the kernel, with
the oracle's hints. Adversarial: forged multipliers, a wrong premise and an out-of-range fact index
are each only unproven. Malformed: truncated records, non-numbers, a premise count past the limit
and an unreadable file are refused before checking. Budget: without Z3 the oracle writes no hints
and the report is unchanged.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
SOURCE = ROOT / "examples/smt_linear_oracle.elisa"
WORK = Path(tempfile.mkdtemp(prefix="elisa-proof-smt-"))
failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


def run_hints(text):
    path = WORK / "hints.txt"
    path.write_text(text)
    result = subprocess.run([str(BINARY), "--linear-hints", str(path), str(SOURCE)], capture_output=True, text=True)
    try:
        return result.returncode, json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.returncode, None


def goal(report, goal_id):
    return next(item for item in report["goals"] if item["goal_id"] == goal_id)


plain = json.loads(subprocess.run([str(BINARY), "--json", str(SOURCE)], capture_output=True, text=True).stdout)
unproven = [item["goal_id"] for item in plain["goals"] if not item["proven"]]
check(len(unproven) == 1, f"expected one unproven goal without hints, got {unproven}")
target = unproven[0] if unproven else 0

hints_path = WORK / "oracle.txt"
oracle = subprocess.run([sys.executable, str(ROOT / "scripts/smt_oracle.py"), "--json", "--hints-out", str(hints_path), str(SOURCE)],
                        capture_output=True, text=True)
summary = json.loads(oracle.stdout or "{}")
check(summary.get("hints") == 1 and summary.get("proven_after") == summary.get("obligations"),
      f"oracle did not close the goal: {summary} {oracle.stderr}")
hint = hints_path.read_text().split()
code, report = run_hints(" ".join(hint))
check(report is not None and goal(report, target)["proven"] and goal(report, target)["replay_status"] == "replayed",
      "hinted goal is not proven and replayed")
check(code == 0, f"valid hint invocation exited {code}; stderr/argument routing must not bypass checking")
check(report is not None and "linear-certificate" in json.dumps(report), "hinted proof carries no linear certificate")

for arguments in (("--linear-hints",), ("--linear-hints", str(hints_path)),
                  ("--linear-hints", str(hints_path), str(SOURCE), "extra")):
    invalid = subprocess.run([str(BINARY), *arguments], capture_output=True, text=True, timeout=60)
    check(invalid.returncode == 2, f"invalid hint argument count accepted: {arguments}")

# Forgeries only fail to prove.
values = [int(field) for field in hint]
forged = {
    "zero goal multiplier": [values[0], 0] + values[2:],
    "doubled premise multiplier": values[:4] + [values[4] * 2] + values[5:],
    "dropped premise": [values[0], values[1], values[2] - 1] + values[3:-2],
    "fact index out of range": values[:3] + [9999] + values[4:],
    "negative inequality multiplier": values[:4] + [-1] + values[5:],
    "other goal id": [target + 7] + values[1:],
}
for label, fields in forged.items():
    code, report = run_hints(" ".join(str(field) for field in fields))
    check(report is not None and code == 1 and not goal(report, target)["proven"], f"forged hint did not reach a checked refusal: {label} (exit {code})")

# Malformed files are refused before checking.
for label, text in {"truncated": f"{target} 1 2 32 1", "not a number": "x 1 1 0 1",
                    "too many premises": f"{target} 1 16 " + "0 1 " * 16, "negative count": f"{target} 1 -1",
                    "long number": "1" * 30}.items():
    code, report = run_hints(text)
    check(code == 2 and report is None, f"malformed hints accepted: {label}")
missing = subprocess.run([str(BINARY), "--linear-hints", str(WORK / "absent.txt"), str(SOURCE)], capture_output=True, text=True)
check(missing.returncode == 2, "unreadable hints file accepted")
code, report = run_hints("# no hints\n")
check(report is not None and not goal(report, target)["proven"], "empty hints changed the verdict")

# Without a solver the oracle proposes nothing.
environment = dict(os.environ, ELISA_PROOF_Z3=str(WORK / "no-z3"))
offline = subprocess.run([sys.executable, str(ROOT / "scripts/smt_oracle.py"), "--json", "--hints-out", str(WORK / "none.txt"), str(SOURCE)],
                         capture_output=True, text=True, env=environment)
offline_summary = json.loads(offline.stdout or "{}")
check(offline_summary.get("hints") == 0 and offline_summary.get("proven_after") == offline_summary.get("proven_before"),
      f"oracle without z3 changed the report: {offline_summary}")

for failure in failures:
    print("FAIL:", failure)
print("smt oracle tests:", "ok" if not failures else f"{len(failures)} failures")
sys.exit(1 if failures else 0)
