"""Keep effect-containment report scans charged to their shared source-work budget."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/proof/model/report_effect_containment_admission.elisa"
TEXT = SOURCE.read_text(encoding="utf-8")
MARKER_SOURCE = ROOT / "src/proof/check/effect_row_markers.elisa"
MARKER_TEXT = MARKER_SOURCE.read_text(encoding="utf-8")
PARSER_SOURCE = ROOT.parent / "Elisa-compiler/src/parser/parser_types_function.elisa"
PARSER_TEXT = PARSER_SOURCE.read_text(encoding="utf-8")
PARSER_CORE = ROOT.parent / "Elisa-compiler/src/parser/parser_core_blocks.elisa"
PARSER_CORE_TEXT = PARSER_CORE.read_text(encoding="utf-8")
PARSER_SIGNATURE = ROOT.parent / "Elisa-compiler/src/parser/parser_types_signature.elisa"
PARSER_SIGNATURE_TEXT = PARSER_SIGNATURE.read_text(encoding="utf-8")
KERNEL_SOURCE = ROOT / "src/proof/replay/effect_source_validation.elisa"
KERNEL_TEXT = KERNEL_SOURCE.read_text(encoding="utf-8")
NEEDLE = "proof_report_source_work_charge("


def calls_on_line(line: str):
    start = 0
    while (position := line.find(NEEDLE, start)) >= 0:
        opening = position + len(NEEDLE) - 1
        depth = 1
        commas = 0
        quoted = False
        escaped = False
        argument_start = opening + 1
        arguments = []
        cursor = opening + 1
        while cursor < len(line) and depth:
            character = line[cursor]
            if quoted:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    quoted = False
            elif character == '"':
                quoted = True
            elif character == "(":
                depth += 1
            elif character == ")":
                if depth == 1:
                    arguments.append(line[argument_start:cursor].strip())
                depth -= 1
            elif character == "," and depth == 1:
                commas += 1
                arguments.append(line[argument_start:cursor].strip())
                argument_start = cursor + 1
            cursor += 1
        assert depth == 0, f"unclosed work-charge call: {line}"
        yield position, commas + 1, arguments
        start = cursor


charge_count = 0
for line_number, line in enumerate(TEXT.splitlines(), start=1):
    for position, arity, arguments in calls_on_line(line):
        charge_count += 1
        assert arity == 2, f"line {line_number}: work charge must include the shared meter"
        assert arguments[1].strip() == "source_work", f"line {line_number}: wrong work meter"
        assert line[:position].rstrip().endswith("not"), f"line {line_number}: charge result is unchecked"

assert charge_count > 0
assert "source_work <= PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT" in TEXT

# Both the declared row and each call row must reject malformed kernel children
# before their names can participate in source correspondence.
kernel_row_work = KERNEL_TEXT.split("def proof_replay_effect_kernel_row_with_work(", 1)[1].split(
    "def proof_replay_effect_function_row_matches(", 1
)[0]
kernel_row = KERNEL_TEXT.split("def proof_replay_effect_kernel_row(", 1)[1].split(
    "def proof_replay_effect_kernel_row_with_work(", 1
)[0]
assert 'nodes[root].kind != "effect-row"' in kernel_row_work
assert 'nodes[member].kind != "effect" or nodes[member].name == ""' in kernel_row_work
assert "proof_replay_effect_member_concrete(name)" in kernel_row
assert "any previous in members where previous == name" in kernel_row
source_validator = KERNEL_TEXT.split("def proof_replay_effect_source_valid_with_work(", 1)[1]
assert "proof_replay_effect_kernel_row_with_work(nodes, children, containment.left, &declared, source_work)" in source_validator
assert 'nodes[call].kind != "effect-call"' in source_validator
assert "proof_replay_effect_kernel_row_with_work(nodes, children, nodes[call].left, &members, source_work)" in source_validator
assert "proof_replay_effect_callee_source_matches_with_work(declarations, annotations, parameters, name, &members, source_work)" in source_validator
assert "proof_replay_effect_function_row_matches(&effects, &declared)" in source_validator
assert "proof_replay_source_call_set_matches_with_work(&source_parameters, &body, annotations, &expected_calls, source_work)" in source_validator

# Preserve explicit empty rows in both function-header positions and bind their markers to the
# exact declaration. Duplicate or misplaced markers must fail closed.
assert 'name: "__function_effect_row_declared"' in PARSER_TEXT
assert "parser.captured_effect_clause_present" in PARSER_TEXT
assert "parser.signature_effect_clause_present" in PARSER_TEXT
assert "parser.captured_effect_clause_present <- true" in PARSER_CORE_TEXT
assert "parser.signature_effect_clause_present <- true" in PARSER_SIGNATURE_TEXT
assert "annotation.offset != function_offset" in MARKER_TEXT
assert "annotation.owner != function_name or annotation.detail_line != function_line" in MARKER_TEXT
assert "index.counts[slot] <- index.counts[slot] + 1" in MARKER_TEXT
assert "index.counts[slot] != 1" in MARKER_TEXT
assert "not proof_report_source_work_charge(1, source_work)" in MARKER_TEXT
assert "effects.count == 0 and not explicit_empty" in TEXT
for consumer in (
    ROOT / "src/proof/check/function_index.elisa",
    ROOT / "src/proof/check/declaration_recording.elisa",
):
    assert "proof_function_effect_row_marker_index_lookup" in consumer.read_text(encoding="utf-8")

# Bind same-spelled module functions to their own source lines during replay.
assert 'node.right > 0' in (ROOT / "src/proof/kernel_replay/arena_shapes.elisa").read_text(encoding="utf-8")
assert "proof_replay_effect_function_declaration_at_with_work(declarations, owner, nodes[root].right.u32(), nodes[root].value.u32()" in source_validator
assert 'nodes[root].right != line.usize()' in source_validator
assert "position.line == line and position.offset == offset" in KERNEL_TEXT
assert '"effect-containment", "", declared_row, line.usize()' in (ROOT / "src/proof/check/effect_containment.elisa").read_text(encoding="utf-8")
producer = (ROOT / "src/proof/check/effect_containment.elisa").read_text(encoding="utf-8")
assert "def proof_effect_containment_name_index_find(" in producer
assert "proof_effect_containment_name_index_find(callee_names, callee_name_index, name" in producer
assert "identity.row >= callee_targets.count" in producer
assert "callee_targets[identity.row] != callee" in producer
call_identity_scan = producer.split("for offset in 0..<call_count", 1)[1].split(
    "needed_nodes: usize =", 1
)[0]
assert "for previous in 0..<callee_targets.count" not in call_identity_scan
identity_failure = call_identity_scan.split("if not identity.complete:", 1)[1].split(
    "if identity.found:", 1
)[0]
assert "implicit_effect_work > PROOF_REPLAY_SUMMARY_SOURCE_WORK_LIMIT" in identity_failure
assert 'proof_add_finding(report, "effect-call-opaque"' in identity_failure
assert "same-spelled callees resolve to distinct source declarations" in producer
duplicate_modules = (ROOT / "examples/effect_containment_duplicate_module_names.elisa").read_text(encoding="utf-8")
assert duplicate_modules.count("def action() -> u8 can[Memory.Allocate]:") == 2
