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
            if "report.certificates" in text and "ProofGoalCertificate{" in text:
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
                if "report.certificates" in text and "ProofGoalCertificate{" in text and section_visibility == "public":
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
        if line.strip().startswith("if node.kind ==") and index + 1 < len(lines) and lines[index + 1].strip() == "return true":
            return set(re.findall(r'node\.kind == "([^"]+)"', line))
    raise AssertionError("resource fact-free leaf list not found")


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
    "mutable", "not", "or", "return", "sizeof", "typeof", "when", "while",
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
    if not checks["resource-fact-free-leaves"] <= kinds:
        failures.append("resource-fact-free-leaves: names a kind the arena does not admit")
    if checks["boundary-trace-kinds"] & (checks["derived-trace-kinds"] | checks["summary-trace-kinds"]):
        failures.append("boundary trace kinds overlap derived or summary kinds")
    shapes = read(PROOF / "kernel_replay" / "arena_shapes.elisa")
    if "return false" not in function_body(shapes, "proof_kernel_replay_arena_float_scalar_shape").strip().splitlines()[-1]:
        failures.append("float scalar shape is no longer unconditionally rejected; update the inventory")
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
