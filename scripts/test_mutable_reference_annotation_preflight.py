"""Malformed reference metadata must not publish partial proposition signatures."""
import ast
import os
from pathlib import Path
import subprocess
import tempfile
from source_binding_harness_support import (
    assert_canonical_std_matches_snapshot,
    checked_in_stage0_revision,
)
from stage1_provenance_validation import validated_stage1_snapshot_std_root


ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(os.environ.get("ELISA_COMPILER_ROOT", ROOT.parent / "Elisa-compiler")).resolve()
FRONTEND = Path(os.environ.get("ELISA_PROOF_FRONTEND_ROOT", ROOT / "build/snapshot/Elisa-compiler")).resolve()
PINNED_FRONTEND_REV = (os.environ.get("ELISA_COMPILER_REV", "").strip()
                       or (ROOT / "ELISA_COMPILER_REV").read_text(encoding="ascii").strip())
try:
    PINNED_STAGE0_REV = checked_in_stage0_revision(ROOT)
except (OSError, ValueError) as error:
    raise SystemExit(f"exact proof Stage0 pin selection failed: {error}") from error
COMPILER_ENV = {
    key: value for key, value in os.environ.items()
    if key != "ELISA_ALLOW_STALE_STAGE1" and key != "ELISA_STAGE0_REV"
}

try:
    SNAPSHOT_STD = Path(validated_stage1_snapshot_std_root(
        str(FRONTEND),
        str(COMPILER / "bin/elisac-stage1"),
        str(COMPILER),
        str(COMPILER),
        PINNED_FRONTEND_REV,
        pinned_stage0_revision=PINNED_STAGE0_REV,
        require_stage0_binding=True,
    ))
    assert_canonical_std_matches_snapshot(SNAPSHOT_STD, COMPILER / "elisacore_std")
except (OSError, ValueError) as error:
    raise SystemExit(f"pinned Stage1/compiler qualification failed: {error}") from error

template_tree = ast.parse((ROOT / "scripts/test_loop_invariants_compile.py").read_text())
template = next(
    ast.literal_eval(node.value)
    for node in template_tree.body
    if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == "REPLAY_HARNESS" for target in node.targets)
)
prefix = template.split("extend ElisaProof:", 1)[0]
prefix = prefix.replace("../../Elisa-compiler/", str(FRONTEND) + "/").replace(
    "../src/", str(ROOT / "src") + "/"
)
harness = prefix + r'''
extend ElisaProof:
    public:
        def source_projection_summary(text: sview, add_reference_marker: bool) -> (known: bool, complete: usize, incomplete: usize, parameters: usize, second_by_reference: bool) can Memory.Allocate, Abort.Panic:
            source: mutable darray[u8] = []
            for index in 0..<sview_len(text) |index, text, source|:
                source.push(text[index])
            source.push(0)
            file: mutable Ast::File = frontend_parse(&source[0])
            target_line: mutable u32 = 0
            for declaration in file.top_decls |target_line|:
                match declaration:
                    Ast::Decl.Func(name, _, _, _, _, _, position):
                        target_line <- position.line if name == "target"
                    _:
                        pass
            return (false, 0, 0, 0, false) if target_line == 0
            if add_reference_marker:
                file.enum_annotations.push(Ast::EnumAnnotation{owner: "second", name: "__typestate_ref_param", line: target_line})

            entries: mutable darray[ProofSourceKernelTypeEntry] = []
            root_path: darray[sview] = []
            source_work: mutable usize = 0
            owner_path_segments: mutable usize = 0
            return (false, 0, 0, 0, false) if not proof_source_kernel_collect_type_index(file.top_decls, &entries, root_path, &source_work, &owner_path_segments, 0)
            type_index: mutable ProofSourceKernelTypeIndex = proof_source_kernel_build_type_index(entries, &source_work)
            return (false, 0, 0, 0, false) if not type_index.complete
            tuple_index: ProofSourceKernelTupleLabelIndex = proof_source_kernel_build_tuple_label_index(file.enum_annotations, &source_work)
            return (false, 0, 0, 0, false) if not tuple_index.complete
            bindings: mutable darray[ElisaProofKernelCore::ProofKernelTypingBinding] = []
            complete: mutable usize = 0
            incomplete: mutable usize = 0
            parameters: mutable usize = 0
            second_by_reference: mutable bool = false
            known: bool = proof_source_kernel_global_bindings(file.top_decls, file.enum_annotations, tuple_index, type_index, &bindings, &source_work)
            return (false, 0, 0, 0, false) if not known
            for binding in bindings |complete, incomplete, parameters, second_by_reference|:
                if binding.kind == "function" or binding.kind == "function-incomplete":
                    continue if binding.name != "target"
                    complete <- complete + 1 if binding.kind == "function"
                    incomplete <- incomplete + 1 if binding.kind == "function-incomplete"
                elif binding.kind == "function-parameter" and binding.owner == "target":
                    parameters <- parameters + 1
                    second_by_reference <- binding.parameter_by_reference if binding.name == "second"
            return (true, complete, incomplete, parameters, second_by_reference)

        def malformed_reference_lookup_publishes_nothing() -> bool can Memory.Allocate, Abort.Panic:
            text: sview = "def target(first: bool&, second: bool) -> bool:\n    return true\n"
            source: mutable darray[u8] = []
            for index in 0..<sview_len(text) |index, text, source|:
                source.push(text[index])
            source.push(0)
            file: Ast::File = frontend_parse(&source[0])
            entries: mutable darray[ProofSourceKernelTypeEntry] = []
            root_path: darray[sview] = []
            source_work: mutable usize = 0
            owner_path_segments: mutable usize = 0
            return false if not proof_source_kernel_collect_type_index(file.top_decls, &entries, root_path, &source_work, &owner_path_segments, 0)
            type_index: mutable ProofSourceKernelTypeIndex = proof_source_kernel_build_type_index(entries, &source_work)
            return false if not type_index.complete
            rows: mutable darray[ElisaProofKernelCore::ProofKernelTypingBinding] = []
            for declaration in file.top_decls |source_work, type_index, rows|:
                match declaration:
                    Ast::Decl.Func(name, parameters, return_type, _, _, _, position):
                        if name == "target":
                            first_hash: u32 = proof_expr_shape_mix(proof_name_hash("first"), position.line.i64())
                            malformed_index: ProofSourceKernelReferenceParameterIndex = ProofSourceKernelReferenceParameterIndex{hashes: [first_hash], lines: [position.line], names: ["first"], occupied: [true]}
                            first_lookup: (complete: bool, present: bool) = proof_source_kernel_parameter_by_reference(malformed_index, position.line, "first", &source_work)
                            return false if not first_lookup.complete or not first_lookup.present
                            second_lookup: (complete: bool, present: bool) = proof_source_kernel_parameter_by_reference(malformed_index, position.line, "second", &source_work)
                            return false if second_lookup.complete
                            added: bool = proof_source_kernel_add_function_signature(rows, name, 0, parameters, return_type, position, malformed_index, file.top_decls, type_index, &source_work)
                            return not added and rows.count == 0
                    _:
                        pass
            return false

        def empty_reference_marker_rejected() -> bool can Memory.Allocate, Abort.Panic:
            text: sview = "def target(first: bool, second: bool) -> bool:\n    return true\n"
            source: mutable darray[u8] = []
            for index in 0..<sview_len(text) |index, text, source|:
                source.push(text[index])
            source.push(0)
            file: mutable Ast::File = frontend_parse(&source[0])
            target_line: mutable u32 = 0
            for declaration in file.top_decls |target_line|:
                match declaration:
                    Ast::Decl.Func(name, _, _, _, _, _, position):
                        target_line <- position.line if name == "target"
                    _:
                        pass
            return false if target_line == 0
            file.enum_annotations.push(Ast::EnumAnnotation{owner: "", name: "__typestate_ref_param", line: target_line})
            entries: mutable darray[ProofSourceKernelTypeEntry] = []
            root_path: darray[sview] = []
            source_work: mutable usize = 0
            owner_path_segments: mutable usize = 0
            return false if not proof_source_kernel_collect_type_index(file.top_decls, &entries, root_path, &source_work, &owner_path_segments, 0)
            type_index: mutable ProofSourceKernelTypeIndex = proof_source_kernel_build_type_index(entries, &source_work)
            return false if not type_index.complete
            tuple_index: ProofSourceKernelTupleLabelIndex = proof_source_kernel_build_tuple_label_index(file.enum_annotations, &source_work)
            return false if not tuple_index.complete
            rows: mutable darray[ElisaProofKernelCore::ProofKernelTypingBinding] = []
            return not proof_source_kernel_global_bindings(file.top_decls, file.enum_annotations, tuple_index, type_index, &rows, &source_work) and rows.count == 0

        def successive_alias_scopes_restore() -> bool can Memory.Allocate, Abort.Panic:
            text: sview = "module Left:\n    struct Node:\n        value: i64\n    type Ref = Node&\nmodule Right:\n    struct Node:\n        value: bool\n    type Ref = Node&\nmodule Caller:\n    struct Node:\n        value: u8\n    def target(first: Left::Ref, second: Right::Ref, third: Node) -> bool:\n        return true\n"
            source: mutable darray[u8] = []
            for index in 0..<sview_len(text) |index, text, source|:
                source.push(text[index])
            source.push(0)
            file: Ast::File = frontend_parse(&source[0])
            entries: mutable darray[ProofSourceKernelTypeEntry] = []
            root_path: darray[sview] = []
            source_work: mutable usize = 0
            owner_path_segments: mutable usize = 0
            return false if not proof_source_kernel_collect_type_index(file.top_decls, &entries, root_path, &source_work, &owner_path_segments, 0)
            type_index: mutable ProofSourceKernelTypeIndex = proof_source_kernel_build_type_index(entries, &source_work)
            return false if not type_index.complete
            tuple_index: ProofSourceKernelTupleLabelIndex = proof_source_kernel_build_tuple_label_index(file.enum_annotations, &source_work)
            return false if not tuple_index.complete
            bindings: mutable darray[ElisaProofKernelCore::ProofKernelTypingBinding] = []
            return false if not proof_source_kernel_global_bindings(file.top_decls, file.enum_annotations, tuple_index, type_index, &bindings, &source_work)
            first_identity: mutable usize = 0
            second_identity: mutable usize = 0
            third_identity: mutable usize = 0
            first_by_reference: mutable bool = false
            second_by_reference: mutable bool = false
            third_by_reference: mutable bool = true
            parameter_count: mutable usize = 0
            for binding in bindings |first_identity, second_identity, third_identity, first_by_reference, second_by_reference, third_by_reference, parameter_count|:
                continue if binding.kind != "function-parameter" or binding.owner != "target"
                parameter_count <- parameter_count + 1
                if binding.name == "first":
                    first_identity <- binding.type_identity
                    first_by_reference <- binding.parameter_by_reference
                elif binding.name == "second":
                    second_identity <- binding.type_identity
                    second_by_reference <- binding.parameter_by_reference
                elif binding.name == "third":
                    third_identity <- binding.type_identity
                    third_by_reference <- binding.parameter_by_reference
            return parameter_count == 3 and first_identity != 0 and second_identity != 0 and third_identity != 0 and first_identity != second_identity and first_identity != third_identity and second_identity != third_identity and first_by_reference and second_by_reference and not third_by_reference

const INCOMPATIBLE_MARKER_SOURCE: sview = "def target(first: bool, second: bool) -> bool:\n    return true\n"
const NULLABLE_REFERENCE_SOURCE: sview = "struct Node:\n    value: i64\n\ndef target(first: bool, second: Node&?) -> bool:\n    return true\n"

def main() -> i64 can Memory.Allocate, Abort.Panic:
    baseline: (known: bool, complete: usize, incomplete: usize, parameters: usize, second_by_reference: bool) = source_projection_summary(INCOMPATIBLE_MARKER_SOURCE, false)
    return 1 if not baseline.known or baseline.complete != 1 or baseline.incomplete != 0 or baseline.parameters != 2
    malformed: (known: bool, complete: usize, incomplete: usize, parameters: usize, second_by_reference: bool) = source_projection_summary(INCOMPATIBLE_MARKER_SOURCE, true)
    return 2 if not malformed.known or malformed.complete != 0 or malformed.incomplete != 1 or malformed.parameters != 0
    nullable: (known: bool, complete: usize, incomplete: usize, parameters: usize, second_by_reference: bool) = source_projection_summary(NULLABLE_REFERENCE_SOURCE, true)
    return 3 if not nullable.known or nullable.complete != 1 or nullable.incomplete != 0 or nullable.parameters != 2 or nullable.second_by_reference
    return 4 if not malformed_reference_lookup_publishes_nothing()
    return 5 if not empty_reference_marker_rejected()
    return 6 if not successive_alias_scopes_restore()
    0
'''

with tempfile.TemporaryDirectory(prefix="mutable-reference-annotation-preflight-") as temporary:
    path = Path(temporary) / "main.elisa"
    binary = Path(temporary) / "gate"
    path.write_text(harness)
    subprocess.run(
        [str(COMPILER / "scripts/elisac_stage1.sh"), str(path), "-emit", "exe", "-O0", "-o", str(binary)],
        cwd=COMPILER,
        env=COMPILER_ENV,
        check=True,
    )
    subprocess.run([str(binary)], env=COMPILER_ENV, check=True, timeout=60)
print("mutable-reference annotation preflight: malformed lookups and empty owners reject; no partial rows; nullable and sibling-alias scope controls preserved")
