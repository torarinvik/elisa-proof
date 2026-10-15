#!/usr/bin/env python3
"""Check KERNEL_INVENTORY.md against the closed sets in the Elisa sources.

Each inventory table lists one closed set in its first column. This script extracts the same set
from the implementation and requires exact equality, so a kind, rule, trace kind or cross-tier
call cannot be added or removed without updating the reviewed inventory.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
PROOF = SRC / "proof"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def strip_comments(text: str) -> str:
    # Elisa comments run from `#` to end of line; string literals in the scanned code never
    # contain `#`, so a plain cut is exact for these files.
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def function_body(text: str, name: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(name)}\b", line):
            indent = len(line) - len(line.lstrip())
            body = []
            for following in lines[index + 1:]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                body.append(following)
            return "\n".join(body)
    raise AssertionError(f"function {name} not found")


def match_arms(body: str) -> set[str]:
    arms: set[str] = set()
    for line in body.splitlines():
        stripped = line.strip()
        if re.fullmatch(r'"[^"]+"(\s+or\s+"[^"]+")*:', stripped):
            arms.update(re.findall(r'"([^"]+)"', stripped))
    return arms


def doc_table(doc: str, name: str) -> set[str]:
    match = re.search(rf"<!-- inventory:{name} -->\n(.*?)<!-- /inventory:{name} -->", doc, re.S)
    if match is None:
        raise AssertionError(f"inventory table {name} missing")
    values: list[str] = []
    for line in match.group(1).splitlines():
        cell = re.match(r"\|\s*`([^`]+)`\s*\|", line)
        if cell:
            values.append(cell.group(1))
    if len(values) != len(set(values)):
        raise AssertionError(f"inventory table {name} has duplicate rows")
    return set(values)


def elisa_files(*roots: Path) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        files.extend([root] if root.is_file() else sorted(root.rglob("*.elisa")))
    return files


def defined_functions(files: list[Path]) -> set[str]:
    return {m.group(1) for path in files for m in re.finditer(r"\bdef (\w+)", read(path))}


def kernel_source_files() -> list[Path]:
    """Return the transitive source closure actually included by the kernel entry modules."""
    roots = (PROOF / "kernel_core.elisa", PROOF / "kernel_replay.elisa")
    pending = list(roots)
    seen: set[Path] = set()
    while pending:
        path = pending.pop()
        resolved = path.resolve()
        if resolved in seen:
            continue
        if PROOF.resolve() not in resolved.parents:
            raise AssertionError(f"kernel include escapes proof/: {path}")
        if not resolved.is_file():
            raise AssertionError(f"kernel include is missing: {path}")
        seen.add(resolved)
        text = strip_comments(read(resolved))
        for include in re.findall(r'^\s*include\s+"([^"]+)"', text, re.MULTILINE):
            pending.append(resolved.parent / include)
    return sorted(seen)


def called_functions(files: list[Path]) -> set[str]:
    calls: set[str] = set()
    for path in files:
        text = strip_comments(read(path))
        calls.update(re.findall(r"(?<![:\w.])(proof_\w+)\s*[\(\[]", text))
    return calls


def node_kinds() -> set[str]:
    text = strip_comments(read(PROOF / "kernel_replay" / "arena_shapes.elisa"))
    kinds = set(re.findall(r'kind == "([^"]+)"', text))
    for membership in re.findall(r'node\.kind\s+in\s*\{([^}]*)\}', text):
        literals = re.findall(r'"([^"]+)"', membership)
        if not literals or re.sub(r'"[^"]+"|[\s,]', "", membership):
            raise AssertionError("arena node-kind membership is not a literal set")
        kinds.update(literals)
    kinds |= match_arms(function_body(text, "proof_kernel_replay_arena_resource_region_shape"))
    return kinds


def certificate_rules() -> set[str]:
    text = read(PROOF / "replay" / "certificate_validation_integrated_helpers.elisa")
    return match_arms(function_body(text, "proof_replay_certificate_rule_valid"))


def certificate_producer_functions() -> set[str]:
    producers: set[str] = set()
    for path in elisa_files(PROOF):
        lines = strip_comments(read(path)).splitlines()
        for index, line in enumerate(lines):
            definition = re.match(r"\s*def (\w+)\b", line)
            if not definition:
                continue
            indent = len(line) - len(line.lstrip())
            body = []
            for following in lines[index + 1:]:
                if following.strip() and len(following) - len(following.lstrip()) <= indent:
                    break
                body.append(following)
            text = "\n".join(body)
            if re.search(r"report(?:\.[A-Za-z_]\w*)*\.certificates\.push\s*\(", text) and "ProofGoalCertificate{" in text:
                producers.add(definition.group(1))
    return producers


def public_certificate_producers() -> set[str]:
    """Find certificate appending functions declared in a public section."""
    public: set[str] = set()
    for path in elisa_files(PROOF):
        lines = strip_comments(read(path)).splitlines()
        section_visibility: str | None = None
        section_indent = -1
        for index, line in enumerate(lines):
            section = re.match(r"(\s*)(public|private):\s*$", line)
            if section:
                section_visibility = section.group(2)
                section_indent = len(section.group(1))
                continue
            definition = re.match(r"(\s*)def (\w+)\b", line)
            if definition and len(definition.group(1)) > section_indent:
                name = definition.group(2)
                indent = len(definition.group(1))
                body = []
                for following in lines[index + 1:]:
                    if following.strip() and len(following) - len(following.lstrip()) <= indent:
                        break
                    body.append(following)
                text = "\n".join(body)
                if re.search(r"report(?:\.[A-Za-z_]\w*)*\.certificates\.push\s*\(", text) and "ProofGoalCertificate{" in text and section_visibility == "public":
                    public.add(name)
            # A sibling section ends the preceding section; sections at the same indentation
            # replace its visibility for following declarations.
            elif line.strip() and len(line) - len(line.lstrip()) <= section_indent and not section:
                section_visibility = None
                section_indent = -1
    return public


def boundary_trace_kinds() -> set[str]:
    text = read(PROOF / "replay" / "certificate_validation.elisa") + read(PROOF / "replay" / "boundary_trace_shapes.elisa")
    return match_arms(function_body(text, "proof_replay_boundary_trace_kind"))


def derived_trace_kinds() -> set[str]:
    text = strip_comments(read(PROOF / "replay" / "certificate_validation.elisa") + read(PROOF / "replay" / "boundary_trace_shapes.elisa"))
    lists = [set(re.findall(r'trace\.kind != "([^"]+)"', line))
             for line in text.splitlines() if 'trace.kind != "proof-step"' in line]
    if not lists or any(kinds != lists[0] for kinds in lists):
        raise AssertionError(f"derived trace kind lists disagree: {lists}")
    return lists[0]


def summary_trace_kinds() -> set[str]:
    text = strip_comments(read(PROOF / "replay" / "certificate_validation.elisa") + read(PROOF / "replay" / "boundary_trace_shapes.elisa"))
    return set(re.findall(r'if trace\.kind == "([^"]+-summary)":', text))


def typing_kinds() -> set[str]:
    text = read(PROOF / "kernel_replay" / "type_environment.elisa")
    body = function_body(text, "proof_kernel_replay_typing_binding_valid")
    return set(re.findall(r'(?:el)?if binding\.kind == "([^"]+)":', body))


def resource_fact_free_leaves() -> set[str]:
    text = read(PROOF / "replay" / "certificate_validation.elisa")
    body = strip_comments(function_body(text, "proof_replay_resource_event_facts_with_owner"))
    lines = body.splitlines()
    for index, line in enumerate(lines):
        if index + 1 >= len(lines) or lines[index + 1].strip() != "return true":
            continue
        equality = re.fullmatch(r'\s*if node\.kind == "([^"]+)":\s*', line)
        if equality:
            return {equality.group(1)}
        membership = re.fullmatch(r'\s*if node\.kind in \{([^}]*)\}:\s*', line)
        if membership:
            literals = re.findall(r'"([^"]+)"', membership.group(1))
            if not literals or re.sub(r'"[^"]+"|[\s,]', "", membership.group(1)):
                raise AssertionError("resource fact-free leaf membership is not a literal set")
            if len(literals) != len(set(literals)):
                raise AssertionError("resource fact-free leaf membership has duplicate kinds")
            return set(literals)
    # An empty allow-list is meaningful: every resource-event leaf now has an explicit
    # source validator or is rejected. Keep that closed state visible in the inventory.
    return {"<none>"}


def replay_external_calls() -> set[str]:
    replay = elisa_files(PROOF / "replay")
    own = defined_functions(replay + [PROOF / "replay.elisa"])
    kernel_public = defined_functions(kernel_source_files())
    # Kernel entry points are called qualified (`ElisaProofKernelReplay::...`) and so never
    # match the unqualified pattern; anything left is a call into a non-kernel tier.
    return called_functions(replay) - own - kernel_public


def correspondence_external_calls() -> set[str]:
    checker = elisa_files(SRC / "correspondence")
    kernel_public = defined_functions(kernel_source_files())
    return called_functions(checker) - defined_functions(checker) - kernel_public


def kernel_external_calls() -> set[str]:
    kernel = kernel_source_files()
    return kernel_call_target_violations(kernel)


def kernel_member_calls(files: list[Path] | None = None) -> set[str]:
    kernel = kernel_source_files() if files is None else files
    calls: set[str] = set()
    member_call = re.compile(r"\.([A-Za-z_]\w*)[ \t]*\(")
    for path in kernel:
        text = _mask_comments_and_strings(read(path))
        calls.update(member_call.findall(text))
    return calls


KERNEL_CALL_SYNTAX = frozenset({
    "and", "assert", "cast", "elif", "else", "for", "if", "is", "match",
    "ensure", "implies", "mutable", "not", "or", "return", "sizeof", "sview_at",
    "sview_len", "typeof", "when", "while",
})


def _mask_comments_and_strings(text: str) -> str:
    """Blank comments and literals while preserving line boundaries and token positions."""
    chars = list(text)
    quote: str | None = None
    escaped = False
    in_comment = False
    for index, char in enumerate(chars):
        if in_comment:
            if char == "\n":
                in_comment = False
            else:
                chars[index] = " "
            continue
        if quote is not None:
            if char != "\n":
                chars[index] = " "
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char == "#":
            chars[index] = " "
            in_comment = True
        elif char in {'"', "'"}:
            chars[index] = " "
            quote = char
    return "".join(chars)


def kernel_call_target_violations(files: list[Path]) -> set[str]:
    """Require every kernel helper call to resolve within its declared kernel module."""
    module_for_line: dict[Path, list[str | None]] = {}
    definitions: set[tuple[str, str]] = set()
    masked: dict[Path, str] = {}
    module_pattern = re.compile(r"^\s*(?:module|extend)\s+([A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)\s*:")
    definition_pattern = re.compile(r"^\s*def\s+(\w+)\b")

    for path in files:
        text = _mask_comments_and_strings(read(path))
        masked[path] = text
        owners: list[str | None] = []
        owner: str | None = None
        for line in text.splitlines():
            module = module_pattern.match(line)
            if module:
                owner = module.group(1)
            owners.append(owner)
            definition = definition_pattern.match(line)
            if definition and owner is not None:
                definitions.add((owner, definition.group(1)))
        module_for_line[path] = owners

    violations: set[str] = set()
    bare_call = re.compile(r"(?<![:\w.])([A-Za-z_]\w*)[ \t]*\(")
    qualified_call = re.compile(r"(?<![\w.])([A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)::([A-Za-z_]\w*)[ \t]*\(")
    for path, text in masked.items():
        for line_number, line in enumerate(text.splitlines()):
            owner = module_for_line[path][line_number]
            for qualified_owner, name in qualified_call.findall(line):
                if (qualified_owner, name) not in definitions:
                    violations.add(f"{qualified_owner}::{name}")
            for name in bare_call.findall(line):
                if name in KERNEL_CALL_SYNTAX:
                    continue
                if owner is None or (owner, name) not in definitions:
                    violations.add(f"{owner or '<unscoped>'}::{name}")
    return violations


def main() -> int:
    doc = read(ROOT / "KERNEL_INVENTORY.md")
    checks = {
        "node-kinds": node_kinds(),
        "typing-kinds": typing_kinds(),
        "certificate-rules": certificate_rules(),
        "certificate-producers": certificate_producer_functions(),
        "boundary-trace-kinds": boundary_trace_kinds(),
        "derived-trace-kinds": derived_trace_kinds(),
        "summary-trace-kinds": summary_trace_kinds(),
        "resource-fact-free-leaves": resource_fact_free_leaves(),
        "replay-external-calls": replay_external_calls(),
        "correspondence-external-calls": correspondence_external_calls(),
        "kernel-member-calls": kernel_member_calls(),
    }
    failures: list[str] = []
    public_producers = public_certificate_producers()
    if public_producers:
        failures.append(f"certificate producers are public: {sorted(public_producers)}")
    for table, source in checks.items():
        if not source:
            failures.append(f"{table}: extracted an empty set from source")
            continue
        documented = doc_table(doc, table)
        if documented != source:
            failures.append(f"{table}: undocumented {sorted(source - documented)}, stale {sorted(documented - source)}")

    kinds = checks["node-kinds"]
    if checks["resource-fact-free-leaves"] != {"<none>"} and not checks["resource-fact-free-leaves"] <= kinds:
        failures.append("resource-fact-free-leaves: names a kind the arena does not admit")
    if checks["boundary-trace-kinds"] & (checks["derived-trace-kinds"] | checks["summary-trace-kinds"]):
        failures.append("boundary trace kinds overlap derived or summary kinds")
    shapes = read(PROOF / "kernel_replay" / "arena_shapes.elisa")
    resource_lend = read(PROOF / "kernel_replay" / "resource_call_lend.elisa")
    lend_shape = function_body(shapes, "proof_kernel_replay_resource_call_lend_child_counts_valid")
    lend_transition = function_body(resource_lend, "proof_kernel_replay_resource_lend")
    if "node.auxiliary >= PROOF_KERNEL_REPLAY_MAX_RESOURCE_CHILDREN" not in lend_shape or "node.children_count - node.right == node.auxiliary * 2" not in lend_shape:
        failures.append("resource-call-lend arena shape must stage its bounded, overflow-safe count equation")
    if "return false if lend_root >= nodes.count\n            lend_node:" not in lend_transition or "proof_kernel_replay_resource_call_lend_child_counts_valid(lend_node)" not in lend_transition or "nodes[lend_root].auxiliary * 2 + nodes[lend_root].right" in lend_transition:
        failures.append("resource-call-lend transition must reuse the staged arena count validator")
    effect_replay = read(PROOF / "kernel_replay" / "resource_model_integrated_helpers.elisa")
    effect_contains = function_body(effect_replay, "proof_kernel_replay_effect_row_contains_with_work")
    effect_within = function_body(effect_replay, "proof_kernel_replay_effect_row_within_with_work")
    effect_goal = function_body(effect_replay, "proof_kernel_replay_effect_goal")
    if effect_contains.index("row_root >= nodes.count") > effect_contains.index("nodes[row_root].kind") or "row_root >= nodes.count or nodes[row_root]" in effect_contains:
        failures.append("effect-row membership must validate its root before indexing")
    if effect_within.index("inner_root >= nodes.count") > effect_within.index("nodes[inner_root].kind") or "inner_root >= nodes.count or nodes[inner_root]" in effect_within:
        failures.append("effect-row containment must validate its root before indexing")
    if effect_goal.index("goal_root >= nodes.count") > effect_goal.index("nodes[goal_root].kind") or effect_goal.index("declared_row >= nodes.count") > effect_goal.index("nodes[declared_row].kind"):
        failures.append("effect-goal replay must validate roots before indexing")
    if "member.value >= nodes.count or nodes[member.value]" in effect_contains + effect_within or "entry.value >= nodes.count or nodes[entry.value]" in effect_goal:
        failures.append("effect replay must validate child roots before indexing")
    if "return false" not in function_body(shapes, "proof_kernel_replay_arena_float_scalar_shape").strip().splitlines()[-1]:
        failures.append("float scalar shape is no longer unconditionally rejected; update the inventory")
    structural_protocol = {
        PROOF / "check" / "flow_and_type_model.elisa",
        PROOF / "certificate_admission.elisa",
        PROOF / "replay" / "structural_source_cache_validation.elisa",
    }
    for path in structural_protocol:
        source = read(path)
        if '"structural-v2"' not in source or '"structural-v1"' in source:
            failures.append(f"structural-safety protocol version drift in {path.relative_to(ROOT)}")
    structural_row = next((line for line in doc.splitlines() if "| `structural-safety` | structural |" in line), "")
    structural_certificate_row = next((line for line in doc.splitlines() if "| `structural-safety` | `proof_kernel_replay_structural_report_with_workspace`" in line), "")
    if "`structural-v2`" not in structural_row or "`structural-v2`" not in structural_certificate_row:
        failures.append("structural-safety version is missing or stale in the inventory")
    encoder = read(PROOF / "kernel_encode.elisa")
    encoder_wrapper = function_body(encoder, "proof_kernel_encode_annotated_depth")
    if "nodes.count > ElisaProofKernelCore::PROOF_KERNEL_NODE_BUDGET" not in encoder_wrapper or "children.count > ElisaProofKernelCore::PROOF_KERNEL_CHILD_BUDGET" not in encoder_wrapper:
        failures.append("kernel encoder does not reject an oversized shared arena before using its invalid-root sentinel")
    if "nodes <- nodes.truncate(node_start)" not in encoder_wrapper or "children <- children.truncate(child_start)" not in encoder_wrapper:
        failures.append("kernel encoder refusal no longer rolls back both shared-arena suffixes")
    resource_events = read(PROOF / "kernel_replay" / "resource_events.elisa")
    resource_history = read(PROOF / "kernel_replay" / "resource_scope_history.elisa")
    resource_copy = read(PROOF / "kernel_replay" / "resource_state_copy.elisa")
    alternative_merge = function_body(resource_history, "proof_kernel_replay_resource_scope_event_history_merge_alternative")
    history_adopt = function_body(resource_history, "proof_kernel_replay_resource_scope_event_history_adopt")
    if "proof_kernel_replay_resource_scope_history_validate_prefix_ids(target.scope.resource_call_events, child.scope.resource_call_events" not in alternative_merge or "proof_kernel_replay_resource_scope_history_validate_prefix_ids(baseline.scope.resource_call_events, child.scope.resource_call_events" not in alternative_merge:
        failures.append("alternative call-result availability allows branch-local calls to escape their lexical bindings")
    if "proof_kernel_replay_resource_scope_history_validate_prefix_ids(target.scope.resource_call_allocations, child.scope.resource_call_allocations" not in alternative_merge or "proof_kernel_replay_resource_scope_history_validate_prefix_ids(baseline.scope.resource_call_allocations, child.scope.resource_call_allocations" not in alternative_merge:
        failures.append("child-local call allocations escape alternative arms")
    if "proof_kernel_replay_resource_scope_history_validate_prefix_ids(target.scope.resource_return_witnesses, child.scope.resource_return_witnesses" not in alternative_merge or "proof_kernel_replay_resource_scope_history_validate_prefix_ids(baseline.scope.resource_return_witnesses, child.scope.resource_return_witnesses" not in alternative_merge:
        failures.append("child-local return witnesses escape alternative arms")
    if 'proof_kernel_replay_resource_scope_history_union_ids_tracked(&target.scope.resource_call_events_seen,' not in alternative_merge:
        failures.append("alternative duplicate-call history does not include events seen on any arm")
    if "proof_kernel_replay_resource_scope_history_validate_prefix_ids(parent.scope.resource_call_events, child.scope.resource_call_events" not in history_adopt or "proof_kernel_replay_resource_scope_history_validate_prefix_ids(parent.scope.resource_call_allocations, child.scope.resource_call_allocations" not in history_adopt or "proof_kernel_replay_resource_scope_history_validate_prefix_ids(parent.scope.resource_return_witnesses, child.scope.resource_return_witnesses" not in history_adopt or "&parent.scope.resource_call_events_seen, &child.scope.resource_call_events_seen" not in history_adopt:
        failures.append("nested scope adoption leaks child-local call, allocation, or return availability")
    call_transitions = function_body(resource_events, "proof_kernel_replay_resource_events_remaining")
    if call_transitions.count("proof_kernel_replay_resource_usize_sorted_membership(state.scope.resource_call_events_seen") < 2 or call_transitions.count("proof_kernel_replay_resource_record_call_event(state, root)") < 2:
        failures.append("call and lend transitions do not reject and record repeated event roots")
    staged_resource_reads = (
        ("return false if node.left >= nodes.count", "nodes[node.left].kind != \"resource-use\""),
        ("return false if value_slot >= state.bindings.binding_reference.count", "state.bindings.binding_reference[value_slot]"),
        ("return false if witness_slot >= state.bindings.binding_moved.count", "state.bindings.binding_moved[witness_slot]"),
        ("return false if target_slot >= state.borrows.borrow_present.count", "state.borrows.borrow_present[target_slot]"),
        ("return false if borrow_target_slot >= state.provenance.binding_region.count", "state.provenance.binding_region[borrow_target_slot]"),
        ("return false if slot >= state.scope.pending_join_moves.count", "state.scope.pending_join_moves[slot]"),
    )
    for bounds_check, indexed_read in staged_resource_reads:
        if bounds_check not in call_transitions or indexed_read not in call_transitions or call_transitions.rfind(bounds_check) > call_transitions.rfind(indexed_read):
            failures.append(f"resource-event indexed read is not staged after its bounds check: {indexed_read}")
    if "resource_call_events_seen.count" not in resource_copy or "source.scope.resource_call_events_seen |seen_call_event" not in resource_copy:
        failures.append("resource state copies do not meter and preserve the duplicate-call history")
    congruence = read(PROOF / "kernel_replay" / "goal_metered_congruence.elisa")
    congruence_collect = function_body(congruence, "proof_kernel_replay_congruence_collect_with_goal_work")
    congruence_seed = function_body(congruence, "proof_kernel_replay_congruence_seed_with_goal_work")
    congruence_driver = read(PROOF / "kernel_replay" / "resource_model_integrated_helpers.elisa")
    congruence_goal = function_body(congruence_driver, "proof_kernel_replay_congruence_goal_with_goal_work")
    for body, label in ((congruence_collect, "term collection"), (congruence_seed, "equality seeding")):
        if "proof_kernel_replay_primitive_comparison_with_markers_with_work" not in body:
            failures.append(f"congruence {label} does not reject source-marked untrusted comparison operators")
    if congruence_collect.find("primitive_relation:") < 0 or congruence_collect.find("primitive_relation:") > congruence_collect.find("proof_kernel_replay_congruence_lookup_with_goal_work"):
        failures.append("congruence term collection reaches lookup before checking comparison operators")
    if congruence_seed.find("primitive_relation:") < 0 or congruence_seed.find("primitive_relation:") > congruence_seed.find("proof_kernel_replay_congruence_union_with_goal_work"):
        failures.append("congruence equality seeding reaches class union before checking comparison operators")
    if "proof_kernel_replay_witness_marker_cache_fill_with_work" not in congruence_goal or "proof_kernel_replay_congruence_seed_with_goal_work(nodes, children, markers," not in congruence_goal:
        failures.append("congruence does not share validated operator markers across collection and seeding")
    congruence_fixture = read(ROOT / "examples" / "kernel_congruence_runtime.elisa")
    for regression in ("UNTRUSTED_EQUALITY_SEEDED", "UNTRUSTED_EQUALITY_GOAL_ADMITTED"):
        if regression not in congruence_fixture:
            failures.append(f"direct-kernel congruence fixture is missing {regression}")
    resource_fixtures = ROOT / "examples" / "kernel_arena_runtime"
    stale_resource_roots = []
    for path in resource_fixtures.glob("*.elisa"):
        for line_number, line in enumerate(read(path).splitlines(), 1):
            if '"resource-safety"' in line and 'ElisaProofKernelCore::add_node' in line and not re.search(r'add_node\([^,]+,\s*"resource-safety",\s*"resource-v2",', line):
                stale_resource_roots.append(f"{path.relative_to(ROOT)}:{line_number}")
    if stale_resource_roots:
        failures.append(f"resource runtime fixtures use a stale resource-safety schema: {stale_resource_roots[:8]}")
    leaked = kernel_external_calls()
    if leaked:
        failures.append(f"kernel calls functions defined outside the kernel: {sorted(leaked)}")

    if failures:
        for failure in failures:
            print(f"kernel inventory: {failure}", file=sys.stderr)
        return 1
    total = sum(len(values) for values in checks.values())
    print(f"kernel inventory: {len(checks)} tables, {total} entries match source")
    return 0


if __name__ == "__main__":
    sys.exit(main())
