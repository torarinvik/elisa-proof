"""Same-array reads require independently established machine-index equality."""
import json
import os, qualified_test_binary
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

BIN = qualified_test_binary.proof_test_binary(ROOT)
if not __debug__:
    raise SystemExit("run without Python -O")
for fixture, expected in (("index_read_equality.elisa", "failed"),
                          ("typed_index_read_congruence.elisa", "proved"),
                          ("open_indexed_prefix_reasoning.elisa", "failed"),
                          ("open_index_window_disjunctions.elisa", "failed"),
                          ("rejected_index_read_equality.elisa", "failed"),
                          ("rejected_typed_index_read_overloaded_equality.elisa", "failed"),
                          ("rejected_typed_index_read_overloaded_index.elisa", "failed")):
    result = subprocess.run([BIN, "--json", str(ROOT / "examples" / fixture)],
                            capture_output=True, text=True, timeout=60)
    report = json.loads(result.stdout)
    assert result.returncode == (0 if expected == "proved" else 1)
    assert report["status"] == expected, report["findings"]
    assert report["summary"]["semantic_errors"] == 0, report["semantic_diagnostics"]
    assert report["replay"]["gaps"] == 0, report["replay"]
    assert report["replay"]["certificates"] == report["replay"]["replayed"]
    assert not report["trust"]["trusted_assumptions"]
    if expected == "proved":
        assert report["summary"]["proven"] == report["summary"]["obligations"] > 0
        targets = ("typed_read_equal_at_direct_index", "typed_read_equal_at_transitive_index",
                   "typed_field_read_equal_at_index")
        for target in targets:
            assert any(d.get("name") == target and d.get("verified")
                       for d in report["declaration_details"]), (target, report["declaration_details"])
    elif fixture == "rejected_index_read_equality.elisa":
        for target in ("rejected_different_index", "rejected_different_array", "rejected_wrapping_index",
                       "rejected_disequality_different_index",
                       "rejected_index_read_through_cross_sort_edges",
                       "rejected_stale_read_after_write", "rejected_skipped_prefix_row",
                       "rejected_float_arithmetic_totality"):
            # Float arithmetic may fail closed at proposition typing before
            # reaching the integer-only denial rule; it must never be verified.
            rejected_kinds = {"ensure-unproven", "contract-proposition-type"} if target == "rejected_float_arithmetic_totality" else {"ensure-unproven"}
            assert any(f["name"] == target and f["kind"] in rejected_kinds
                       for f in report["findings"]), (target, report["findings"])
            assert not any(d.get("name") == target and d.get("verified")
                           for d in report["declaration_details"])
    elif fixture == "rejected_typed_index_read_overloaded_equality.elisa":
        for target in ("rejected_index_read_through_overloaded_equality",
                       "rejected_implicit_scalar_reference_overloaded_reflexivity",
                       "rejected_explicit_scalar_reference_overloaded_reflexivity",
                       "rejected_array_element_overloaded_equality",
                       "rejected_pure_call_result_overloaded_reflexivity"):
            assert any(f["name"] == target and f["kind"] == "ensure-unproven"
                       for f in report["findings"]), (target, report["findings"])
            assert not any(d.get("name") == target and d.get("verified")
                           for d in report["declaration_details"])
    elif fixture == "rejected_typed_index_read_overloaded_index.elisa":
        target = "rejected_custom_index_congruence"
        assert any(f["name"] == target and f["kind"] == "ensure-unproven"
                   for f in report["findings"]), (target, report["findings"])
        assert not any(d.get("name") == target and d.get("verified")
                       for d in report["declaration_details"])
    else:
        targets = {
            "index_read_equality.elisa": ("indexed_read_at_equal_index", "indexed_read_at_transitively_equal_index", "indexed_prefix_step",
                                          "indexed_read_from_negated_inequality", "indexed_disequality_at_equal_index",
                                          "indexed_disequality_from_negated_equality"),
            "open_indexed_prefix_reasoning.elisa": ("indexed_read_from_window",),
            "open_index_window_disjunctions.elisa": ("indexed_read_with_row_disjunctions",),
        }[fixture]
        for target in targets:
            assert any(f["name"] == target and f["kind"] == "ensure-unproven"
                       for f in report["findings"]), (target, report["findings"])
            assert not any(d.get("name") == target and d.get("verified")
                           for d in report["declaration_details"])
print("same-array indexed equalities replay; different indices, arrays, wrapping and stale-read controls reject")
