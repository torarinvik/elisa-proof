#!/usr/bin/env python3
"""Pattern-binder scans must debit their enclosing source-analysis work meter."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def body(path: Path, name: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(name)}\b", line):
            indent = len(line) - len(line.lstrip())
            end = index + 1
            while end < len(lines):
                following = lines[end]
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                end += 1
            return "\n".join(lines[index:end])
    raise AssertionError(f"missing {name} in {path}")


local_writes = ROOT / "src/proof/replay/source_local_writes.elisa"
compat = body(local_writes, "proof_replay_source_pattern_binds")
assert "work: mutable usize = 0" in compat
assert "proof_replay_source_pattern_binds_with_work(pattern, name, &work, depth)" in compat
metered = body(local_writes, "proof_replay_source_pattern_binds_with_work")
assert "proof_replay_call_pattern_bindings_with_work(pattern, &bindings, work, 0)" in metered
assert "proof_replay_call_work_add(work, sview_len(name))" in metered
assert "proof_replay_call_string_compare_charge(bound, name, work)" in metered

for path, caller in (
    (ROOT / "src/proof/replay/source_binding_validation/loop_scopes.elisa", "proof_replay_nested_local_expression"),
    (ROOT / "src/proof/replay/source_binding_validation/loop_scopes.elisa", "proof_replay_nested_local_declarations"),
    (ROOT / "src/proof/replay/summary_local_alias_sites.elisa", "proof_replay_local_alias_site"),
):
    source = body(path, caller)
    assert "proof_replay_source_pattern_binds_with_work(" in source, caller
    assert "proof_replay_source_pattern_binds(" not in source, caller

print("source pattern scans: binder traversal and name matching share the enclosing work meter")
