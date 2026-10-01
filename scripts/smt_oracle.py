"""SMT linear oracle (BACKLOG W-01).

Runs `elisa-proof --json` on a source, and for every unproven goal whose near-miss carries
`linear_rows` asks Z3 for integer Farkas multipliers refuting the negated goal. The answers are
written as a `--linear-hints` file and the source is checked again with them. Z3 is untrusted:
each hint becomes an ordinary `__elisa_linear_certificate` that the checker and the kernel decide,
so a wrong answer only fails to prove, and replay never needs Z3.

usage: smt_oracle.py [--hints-out FILE] [--json] <file.elisa>
"""
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
Z3 = os.environ.get("ELISA_PROOF_Z3", shutil.which("z3") or "z3")
MULTIPLIER = 1048576  # ProofLinearCertificateLimit::MULTIPLIER
PREMISES = 15         # ProofLinearCertificateLimit::PREMISES
TIMEOUT_MS = 2000


def run_json(path, hints=None):
    command = [str(BINARY)] + (["--linear-hints", str(hints)] if hints else ["--json"]) + [str(path)]
    result = subprocess.run(command, capture_output=True, text=True)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def unproven_problems(report):
    found = {}
    stack = [report]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            near = node.get("near_miss")
            if isinstance(near, dict) and isinstance(near.get("linear_rows"), dict) and "goal_id" in node:
                found[node["goal_id"]] = near["linear_rows"]
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return found


def smt_query(problem):
    atoms, rows = problem["atoms"], problem["rows"]
    lines = ["(set-logic QF_LIA)", f"(set-option :timeout {TIMEOUT_MS})"]
    for index, row in enumerate(rows):
        lines.append(f"(declare-const l{index} Int)")
        low = 1 if row["fact"] < 0 else (-MULTIPLIER if row["equality"] else 0)
        lines.append(f"(assert (<= {low} l{index} {MULTIPLIER}))")
    def weighted(values):
        terms = [f"(* {value} l{index})" for index, value in enumerate(values) if value != 0]
        return "(+ 0 " + " ".join(terms) + ")" if terms else "0"
    for atom in range(len(atoms)):
        lines.append(f"(assert (= {weighted([row['coefficients'][atom] for row in rows])} 0))")
    lines.append(f"(assert (>= {weighted([row['constant'] for row in rows])} 1))")
    used = [f"(ite (= l{index} 0) 0 1)" for index, row in enumerate(rows) if row["fact"] >= 0]
    if used:
        lines.append(f"(assert (<= (+ 0 {' '.join(used)}) {PREMISES}))")
    lines += ["(check-sat)", "(get-value (" + " ".join(f"l{index}" for index in range(len(rows))) + "))"]
    return "\n".join(lines) + "\n"


def parse_model(text, count):
    if not text.startswith("sat"):
        return None
    values = {}
    for match in re.finditer(r"\(l(\d+)\s+(?:\(-\s*(\d+)\)|(\d+))\)", text):
        values[int(match.group(1))] = -int(match.group(2)) if match.group(2) else int(match.group(3))
    return values if len(values) == count else None


def solve(problem):
    try:
        result = subprocess.run([Z3, "-in"], input=smt_query(problem), capture_output=True, text=True,
                                timeout=TIMEOUT_MS / 1000 + 5)
    except (OSError, subprocess.TimeoutExpired):
        return None  # no solver, no hint: the plain report stands
    values = parse_model(result.stdout.strip(), len(problem["rows"]))
    if values is None:
        return None
    premises = [(row["fact"], values[index]) for index, row in enumerate(problem["rows"])
                if row["fact"] >= 0 and values[index] != 0]
    goal = [values[index] for index, row in enumerate(problem["rows"]) if row["fact"] < 0]
    if len(goal) != 1 or goal[0] <= 0 or not premises:
        return None
    return goal[0], premises


def main(argv):
    hints_out, as_json = None, False
    while argv and argv[0].startswith("--"):
        if argv[0] == "--hints-out" and len(argv) > 1:
            hints_out, argv = Path(argv[1]), argv[2:]
        elif argv[0] == "--json":
            as_json, argv = True, argv[1:]
        else:
            break
    if len(argv) != 1:
        sys.stderr.write(__doc__)
        return 2
    source = Path(argv[0])
    before = run_json(source)
    if before is None:
        sys.stderr.write("smt_oracle: elisa-proof produced no report\n")
        return 1
    hints = []
    for goal_id, problem in sorted(unproven_problems(before).items()):
        answer = solve(problem)
        if answer is not None:
            goal_multiplier, premises = answer
            fields = [goal_id, goal_multiplier, len(premises)] + [value for pair in premises for value in pair]
            hints.append(" ".join(str(field) for field in fields))
    hints_path = hints_out or source.with_suffix(".linear-hints")
    hints_path.write_text("".join(line + "\n" for line in hints))
    after = run_json(source, hints_path) if hints else before
    if after is None:
        sys.stderr.write("smt_oracle: elisa-proof refused the hints\n")
        return 1
    summary = {"source": str(source), "hints": len(hints), "hints_file": str(hints_path),
               "proven_before": before["summary"].get("proven"), "proven_after": after["summary"].get("proven"),
               "obligations": after["summary"].get("obligations")}
    sys.stdout.write((json.dumps(summary) if as_json else
                      f"{source}: {summary['proven_before']} -> {summary['proven_after']} proven "
                      f"of {summary['obligations']} ({len(hints)} hints)") + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
