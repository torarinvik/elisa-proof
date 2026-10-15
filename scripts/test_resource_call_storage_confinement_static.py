"""Guard the source-recomputed storage premises for resource-call lending."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def function_body(path: Path, name: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.lstrip().startswith(f"def {name}"):
            indent = len(line) - len(line.lstrip())
            body = []
            for following in lines[index + 1 :]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                body.append(following.strip())
            return "\n".join(body)
    raise AssertionError(f"function {name} not found in {path}")


resource_source_path = ROOT / "src/proof/replay/resource_call_source_validation.elisa"
resource_lend_return_guard = function_body(resource_source_path, "proof_replay_resource_lend_return_is_confined")
assert "proof_type_is_reference_free_with_work(declared_return_type" in resource_lend_return_guard
assert "return false if not return_reference_free" in resource_lend_return_guard
assert "proof_type_contains_borrowed_view_with_work(declared_return_type" in resource_lend_return_guard

resource_lend_storage_guard = function_body(resource_source_path, "proof_replay_resource_lend_storage_is_confined_with_work")
assert "proof_replay_thread_type_mentions_owner_generic_with_work" in resource_lend_storage_guard
assert "proof_type_is_reference_free_with_work(target_type.target" in resource_lend_storage_guard
assert "proof_replay_thread_type_contains_borrowed_storage(target_type.target" in resource_lend_storage_guard
assert "not borrowed.complete or borrowed.borrowed" in resource_lend_storage_guard

resource_call_argument_guard = function_body(resource_source_path, "proof_replay_resource_call_arguments_match_with_work")
assert "proof_replay_resource_lend_storage_is_confined_with_work(report, parameters, parameter_markers_by_index" in resource_call_argument_guard

resource_purity_path = ROOT / "src/proof/replay/resource_call_pure_source.elisa"
resource_scalar_guard = function_body(resource_purity_path, "proof_replay_resource_call_scalar_type_with_work")
assert "proof_replay_resource_scalar_type_with_work(expression, report, source_work, 0)" in resource_scalar_guard
assert "not scalar.complete or not scalar.scalar" in resource_scalar_guard
assert "proof_replay_control_match_guard_scalar_type(expression)" in resource_scalar_guard
resource_purity_function = function_body(resource_purity_path, "proof_replay_resource_call_pure_function")
assert "proof_structural_typed_operator_statements_have_overload(body, parameters, declaration_line, operator_source, 0, entry.owner, true)" in resource_purity_function
assert "or overloaded_operator" in resource_purity_function
resource_name_counts = function_body(ROOT / "src/proof/replay/resource_call_name_counts.elisa", "proof_replay_resource_call_name_counts_match")
assert "proof_replay_resource_call_name_is_irrelevant_with_work(report, operator_source" in resource_name_counts
resource_coverage = function_body(resource_source_path, "proof_replay_resource_call_coverage_for_owner_with_work")
assert "proof_replay_resource_call_name_counts_match(source_calls, event_names, report, cache.scratch" in resource_coverage

resource_lend_producer = function_body(ROOT / "src/proof/resources/call_region_lending.elisa", "proof_resource_call_lend_storage_is_confined")
assert "return_borrowed_view_free" in resource_lend_producer
assert "all_parameter_target_borrowed_view_free" in resource_lend_producer

function_collection = function_body(ROOT / "src/proof/check/function_index.elisa", "proof_collect_functions")
assert "proof_type_contains_borrowed_view_with_work" in function_collection
assert "all_parameter_target_borrowed_view_free" in function_collection
assert "return_borrowed_view_free" in function_collection

print("resource-call lend replay recomputes reference and borrowed-view storage confinement")
