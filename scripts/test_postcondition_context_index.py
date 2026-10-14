"""Guard the bounded linear-build shape of postcondition typing contexts."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/proof/check/kernel_proposition_postcondition_environment.elisa"


def function_body(name: str) -> str:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(name)}\b", line):
            indent = len(line) - len(line.lstrip())
            body = [line]
            for following in lines[index + 1 :]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                body.append(following)
            return "\n".join(body)
    raise AssertionError(f"function {name} not found")


build = function_body("proof_source_kernel_postcondition_context_index_build")
collect_owners = function_body("proof_source_kernel_postcondition_owner_contexts_collect")
collect_constants = function_body("proof_source_kernel_postcondition_constants_collect")
owner_lookup = function_body("proof_source_kernel_postcondition_owner_index_slot")
module_lookup = function_body("proof_source_kernel_postcondition_module_scope_index_slot")

# Build traverses declarations once for owners, indexes generic metadata once, then traverses
# declarations once for constants. No per-owner declaration or generic-row scan may return.
assert "proof_source_kernel_postcondition_owner_contexts_collect(declarations" in build
assert "proof_source_kernel_postcondition_constants_collect(declarations" in build
assert "for generic_index in 0..<generic_param_lines.count" in build
assert "for owner_index in 0..<index.owners.count" in build
assert "proof_source_kernel_postcondition_owner_validate" not in build
assert "proof_source_kernel_collect_scope_constants" not in build
assert "for generic_index" not in collect_owners
assert "proof_source_kernel_postcondition_owner_contexts_collect(nested" in collect_owners
assert "proof_source_kernel_postcondition_constants_collect(nested" in collect_constants
assert "proof_source_kernel_charge_work" in collect_owners
assert "proof_source_kernel_charge_work" in collect_constants

# Identity, module-path and line queries use bounded open-addressed indexes. In-place path
# comparison avoids copying a scope's potentially large constant arrays for every lookup.
assert "owner_index_values" in owner_lookup and "PROOF_NAME_INDEX_MAX_CLUSTER" in owner_lookup
assert "module_scope_index_values" in module_lookup and "PROOF_NAME_INDEX_MAX_CLUSTER" in module_lookup
assert "ProofSourceKernelPostconditionModuleScope = index.module_scopes[row]" not in module_lookup
assert "index.module_scopes[row].path" in module_lookup
assert "line_index_values" in function_body("proof_source_kernel_postcondition_line_index_slot")

print("postcondition context index guards passed")
