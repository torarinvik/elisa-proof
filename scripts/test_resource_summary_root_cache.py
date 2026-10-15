#!/usr/bin/env python3
"""Guard exact-owner resource-summary root caching and its O(1) lookup path."""

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


places = ROOT / "src/proof/resources/places_and_calls.elisa"
states = ROOT / "src/proof/resources/state_and_regions.elisa"
statements = ROOT / "src/proof/resources/statement_checker.elisa"
schedule = ROOT / "src/proof/check/function_verification_schedule.elisa"
region_flow = ROOT / "src/proof/resources/region_flow.elisa"

lookup = body(places, "proof_resource_summary_root_for_function")
for requirement in (
    "function_index >= functions.lookup.source.names.count",
    "function_index >= functions.lookup.source.owner_modules.count",
    "function_index >= functions.summaries.verified.count",
    "not functions.summaries.verified[function_index]",
    "function_index >= functions.summaries.resource_summary_roots.count",
    "function_index >= functions.summaries.resource_summary_root_valid.count",
    "not functions.summaries.resource_summary_root_valid[function_index]",
    'node.kind != "resource-safety" or node.name != name or node.operator != "resource-v2" or node.secondary_name != owner',
    "proof_source_index_work_charge(report, sview_len(owner))",
):
    assert requirement in lookup, requirement
assert "for candidate_root" not in lookup

finish = body(states, "proof_resource_finish")
node_admitted = finish.index("if root >= report.analysis_1.kernel.nodes.count")
cache_write = finish.index("functions.summaries.resource_summary_roots[function_index] <- root")
assert node_admitted < cache_write
assert "functions.summaries.resource_summary_root_valid[function_index] <- true" in finish

check = body(statements, "proof_check_resource_safety")
assert "functions.summaries.resource_summary_root_valid[function_index] <- false" in check
assert check.index("resource_summary_root_valid[function_index] <- false") < check.index(
    "for parameter in parameters"
)

schedule_body = body(schedule, "proof_compute_verified_functions")
for requirement in (
    "functions.summaries.resource_summary_roots.clear()",
    "functions.summaries.resource_summary_root_valid.clear()",
    "functions.summaries.resource_summary_roots.push(0)",
    "functions.summaries.resource_summary_root_valid.push(false)",
):
    assert requirement in schedule_body, requirement

flow = region_flow.read_text(encoding="utf-8")
assert flow.count("proof_resource_summary_root_for_function(functions, report, function_index)") == 3
assert "for candidate_root" not in flow

print("resource summary cache: function-slot roots are invalidated, admitted, and identity-checked")
