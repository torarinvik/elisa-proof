"""Keep resource event identities tied to parser-owned binding scopes."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def function_body(path: Path, name: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(name)}\b", line):
            indent = len(line) - len(line.lstrip())
            body = []
            for following in lines[index + 1 :]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                body.append(following)
            return "\n".join(body)
    raise AssertionError(f"missing function {name} in {path}")


resource_identity_path = ROOT / "src/proof/replay/resource_binding_identity_validation.elisa"
resource_identity = resource_identity_path.read_text(encoding="utf-8")
resource_owner = function_body(
    ROOT / "src/proof/replay/resource_call_source_validation.elisa",
    "proof_replay_resource_safety_owner_valid_with_work",
)
assert "proof_replay_resource_binding_position_index_build_with_work(report, root, source_work)" in resource_owner
assert "proof_replay_resource_binding_identities_source_valid_with_work(report, root, resource_positions.index, parameters, body, source_work)" in resource_owner
resource_identity_pass = function_body(
    resource_identity_path, "proof_replay_resource_binding_identities_source_valid_with_work"
)
assert 'report.analysis_1.kernel.nodes[event_root].auxiliary <- 0' in resource_identity_pass
assert "proof_replay_resource_binding_statements_covered_with_work(report, index, names, binders, body" in resource_identity_pass
resource_event_walk = function_body(
    resource_identity_path, "proof_replay_resource_binding_positions_at_with_work"
)
assert 'event.kind in {"resource-safety", "resource-scope", "resource-alternatives"}' in resource_event_walk
resource_scope_mark = function_body(
    resource_identity_path, "proof_replay_resource_binding_scope_mark_with_work"
)
resource_scope_restore = function_body(
    resource_identity_path, "proof_replay_resource_binding_scope_restore_with_work"
)
assert "names.count != binders.count" in resource_scope_mark
assert "(true, names.count)" in resource_scope_mark
assert "mark > names.count" in resource_scope_restore
assert "names <- names.truncate(mark)" in resource_scope_restore
assert "binders <- binders.truncate(mark)" in resource_scope_restore
resource_statement_walk = function_body(
    resource_identity_path, "proof_replay_resource_binding_statements_covered_with_work"
)
assert "branch_scope.mark, source_work" in resource_statement_walk
assert "nested_scope.mark, source_work" in resource_statement_walk
assert "proof_replay_resource_binding_range_shape_with_work(iterable, source_work, 0)" in resource_statement_walk
assert 'proof_replay_resource_binding_position_find_with_work(report, index, "resource-bind", iterable_position.end_offset.usize(), variable' in resource_statement_walk
for operation in ("resource-use", "resource-write", "resource-move"):
    assert f'"{operation}"' in resource_identity_pass
assert 'proof_replay_resource_binding_position_find_with_work(report, index, "resource-bind", position.end_offset.usize(), name' in resource_identity
assert 'proof_replay_resource_binding_event_annotate_with_work(report, index, "resource-write"' in resource_identity
resource_kernel = (ROOT / "src/proof/kernel_replay/resource_events.elisa").read_text(encoding="utf-8")
assert resource_kernel.count("proof_kernel_replay_resource_binding_event_identity_matches(state, nodes, slot, node.auxiliary)") >= 3
resource_identity_kernel = function_body(
    ROOT / "src/proof/kernel_replay/resource_state.elisa",
    "proof_kernel_replay_resource_binding_event_identity_matches",
)
assert 'nodes[root].kind not in {"resource-bind", "resource-region-alloc", "resource-region-bind", "resource-call-result"}' in resource_identity_kernel
assert "nodes[root].name == state.bindings.binding_names[slot]" in resource_identity_kernel

print("resource binding identity guard: parser scopes and kernel live slots remain linked")
