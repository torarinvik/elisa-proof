#!/usr/bin/env python3
"""Guard trust labels on the portable theorem-package admission route.

This is a source inventory check, not a proof of the decoder, kernel, or source adapter. It ties
the portable result's deliberately limited trust classifications to the input schema and checks
that a successful package result can only follow whole-arena admission and successful per-theorem
replay.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
READER = ROOT / "src/portable/package_reader.elisa"
CHECKER = ROOT / "src/portable/package_checker.elisa"


def body(source: str, name: str) -> str:
    lines = source.splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(name)}(?:\[|\s|\()", line):
            indent = len(line) - len(line.lstrip())
            for end in range(index + 1, len(lines)):
                if lines[end].strip() and len(lines[end]) - len(lines[end].lstrip()) <= indent:
                    return "\n".join(lines[index + 1 : end])
            return "\n".join(lines[index + 1 :])
    raise AssertionError(f"function {name} not found")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


reader = READER.read_text(encoding="utf-8")
checker = CHECKER.read_text(encoding="utf-8")
header = body(reader, "proof_package_read_header")
check_theorem = body(checker, "proof_package_check_theorem")
replay = body(checker, "proof_package_replay")
push_result = body(checker, "proof_package_push_result")

# The format only accepts adapter-supplied hypotheses/correspondence and an identity-hint digest;
# source authentication must remain false. These are exactly the labels the result may report.
require('trust_keys: darray[sview] = ["hypotheses", "source_correspondence", "fingerprints"]' in header,
        "portable input trust schema changed; review and inventory the new fields")
for field in ("hypotheses", "source_correspondence"):
    require(f'proof_package_string_is(proof_package_string_field(trust.value, "{field}"), "adapter")' in header,
            f"portable reader no longer restricts {field} to adapter trust")
require('proof_package_string_is(proof_package_string_field(trust.value, "fingerprints"), "identity-hint")' in header,
        "portable reader no longer restricts fingerprints to identity-hint")
require("or authenticated.value" in header,
        "portable input schema no longer refuses authenticated-source claims")
for label in ('\\"kernel\\":\\"checked\\"', '\\"package_reader\\":\\"trusted\\"',
              '\\"hypotheses\\":\\"adapter\\"', '\\"source_correspondence\\":\\"adapter\\"',
              '\\"fingerprints\\":\\"identity-hint\\"', '\\"source_authenticated\\":false'):
    require(label in push_result, f"portable output trust classification changed: {label}")

# A theorem's successful status is emitted only for an empty verdict from the checker, whose
# final success follows range/schema/identity checks and kernel replay of the supplied roots.
ordered_checks = [
    "proof_package_has_exactly(theorem, keys)",
    "root >= nodes.count",
    "conclusion.value >= nodes.count",
    "proof_portable_sequent_identity",
    "proof_package_replay_rule(nodes, children, rule.value, facts, conclusion.value, workspace)",
]
positions = [check_theorem.find(part) for part in ordered_checks]
require(all(position >= 0 for position in positions) and positions == sorted(positions),
        "portable theorem admission no longer checks schema, root ranges, identity, then kernel replay")
require('if sview_len(checked.verdict.status) == 0:\n            proof_push(&results, "\\\"replayed\\\",\\\"reason\\\":null}")' in replay,
        "portable theorem result no longer derives replayed status from the checker verdict")

# A bounded theorem-envelope preflight intentionally runs before arena admission. The actual
# theorem replay loop must follow admission of the complete arena; empty packages and any theorem
# failure exit through the failure branch.
arena_gate = replay.find("proof_kernel_replay_arena_all_report")
theorem_loop = replay.find("for index in 0..<theorem_list.count", arena_gate)
failure_return = replay.find("if sview_len(verdict.status) > 0:")
success_return = replay.find("proof_package_push_result(out, final_verdict")
require(arena_gate >= 0 and theorem_loop > arena_gate,
        "portable theorem checks no longer follow whole-arena admission")
require("if theorem_list.count == 0:" in replay and failure_return > theorem_loop and success_return > failure_return,
        "portable package success path no longer rejects empty or failed theorem sets")
require("return 1" in replay[failure_return:success_return],
        "portable package failure branch no longer exits unsuccessfully")

print("portable trust inventory: adapter trust labels and admitted-root success gate: ok")
