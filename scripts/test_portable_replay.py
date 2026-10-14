"""Single entry point for portable package production, replay, and adversarial checks."""
import copy
import json
from pathlib import Path
import runpy
import subprocess

from portable_replay_support import *
from portable_resource_controls import check_unresolved_shadow

if not __debug__:
    raise SystemExit("portable replay checks must run without Python -O")

ROOT = Path(__file__).resolve().parents[1]


def export_repro(name):
    run = subprocess.run([str(BINARY), "--package", str(ROOT / "test" / "repro" / name)],
                         capture_output=True, text=True, timeout=120)
    assert run.returncode in (0, 1), (name, run.returncode, run.stderr)
    return json.loads(run.stdout)

# One example per kernel rule family; export and replay each positive package exactly once.
POSITIVE = {
    "global_constant_module": {"goal", "resource-safety"},
    "module_negative_i64_constant_contract": {"goal", "resource-safety"},
    "verified": {"goal"},
    "collection_quantifier": {"quantifier-forall", "quantifier-exists"},
    "checked_index_fallback": {"checked-index"},
    "getelse_recovery": {"checked-get"},
    "effect_containment": {"effect-containment"},
    "early_return_index_guard": {"index-lower", "index-upper"},
    "fixed_array_slice_bounds": {"slice-lower", "slice-upper", "slice-order"},
    "pure_unfolding": {"goal"},
    "goal_disjunct_split_probe": {"goal", "resource-safety"},
    "disjunctive_goals": {"goal", "index-upper"},
    "leaving_branch_join": {"goal", "index-upper"},
    "linear_disequality_refuted": {"goal", "resource-safety"},
    "closed_goal_width_uniform": {"goal", "resource-safety"},
    "conditional_result_branchwise_probe": {"goal", "resource-safety"},
    "replay_qualified_constant_argument": {"resource-safety"},
}
packages = {}
for example, rules in POSITIVE.items():
    package = export(example)
    packages[example] = package
    assert package["format"] == "elisa-proof-package-v3" and package["source"]["admissible"], example
    assert package["trust"]["logic_mode"] == "classical_propositional", example
    assert package["source"]["authenticated"] is False, example
    seen = {theorem["rule"] for theorem in package["theorems"]}
    assert rules <= seen, (example, rules, seen)
    for theorem in package["theorems"]:
        assert theorem["statement"] == statement(package, theorem["hypotheses"], theorem["conclusion"]), (example, theorem["name"])
        assert theorem["goal_fingerprint"] == fnv1a32(theorem["statement"]), (example, theorem["name"])
    code, result = replay(package, example)
    assert code == 0 and result["status"] == "replayed", (example, result)
    assert result["trust"]["logic_mode"] == "classical_propositional", result
    assert all(theorem["logic_mode"] == "classical_propositional" for theorem in result["theorems"]), result
    assert result["summary"] == {"theorems": len(package["theorems"]),
                                 "replayed": len(package["theorems"]), "not_replayed": 0}, result
    # Existing v2 packages have no logic-mode field. Preserve their exact schema while making
    # the current replay semantics explicit in the checker result.
    legacy_v2 = copy.deepcopy(package)
    legacy_v2["format"] = "elisa-proof-package-v2"
    legacy_v2["trust"].pop("logic_mode")
    legacy_code, legacy_result = replay(legacy_v2, example + "-v2-compat")
    assert legacy_code == 0 and legacy_result["status"] == "replayed", (example, legacy_result)
    assert legacy_result["trust"]["logic_mode"] == "classical_propositional", legacy_result
    report = json.loads(subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / (example + ".elisa"))],
                                       capture_output=True, text=True, timeout=120).stdout)
    replayed_goals = [goal for goal in report["goals"] if goal["proven"] and goal.get("replay_status") == "replayed"]
    assert len(package["theorems"]) == len(replayed_goals), (example, len(package["theorems"]), len(replayed_goals))

check_unresolved_shadow(packages, refused)

# Termination certificates are source-relative: the replay kernel checks witness shape but does
# not derive recursive call sites from a declaration. Build a validly-shaped, fully resealed
# certificate to make sure this public route cannot turn that shape alone into a theorem.
structural_package = copy.deepcopy(packages["verified"])
structural_package["theorems"] = []
structural_children = structural_package["kernel"]["children"]
witness_root = append_node(structural_package, "structural-argument", "strict", value="2",
                           name="subject", auxiliary=1, secondary_name="child")
witness_children_start = len(structural_children)
structural_children.append(witness_root)
edge_root = append_node(structural_package, "structural-edge", auxiliary=1,
                        children_start=witness_children_start, children_count=1,
                        name="f", secondary_name="f")
edge_children_start = len(structural_children)
structural_children.append(edge_root)
structural_root = append_node(structural_package, "structural-safety",
                              children_start=edge_children_start, children_count=1,
                              name="f", secondary_name="structural-v1")
structural_theorem = {
    "goal_id": 0, "name": "forged-structural", "line": 1, "rule": "structural-safety",
    "hypotheses": [], "hypothesis_origins": [], "conclusion": structural_root,
}
structural_package["theorems"] = [reseal(structural_package, structural_theorem)]
assert structural_package["source"]["authenticated"] is False
structural_result = refused(structural_package, "unauthenticated-structural-safety",
                            "rejected", "source-authentication-required")
assert structural_result["theorems"] == [], structural_result
assert structural_result["summary"] == {"theorems": 0, "replayed": 0, "not_replayed": 0}, structural_result
assert structural_result["kernel"] == {"nodes": 0, "children": 0}, structural_result
late_bad_envelope = copy.deepcopy(structural_package)
late_bad_envelope["theorems"].append(copy.deepcopy(structural_theorem))
del late_bad_envelope["theorems"][1]["statement"]
late_bad_result = refused(late_bad_envelope, "structural-rule-does-not-skip-envelope-scan",
                          "malformed", "theorem-schema")
assert late_bad_result["theorems"] == [], late_bad_result

# The positive-conjunction rule is useful on its source shape, but a re-sealed portable theorem
# cannot replace the required conjunct with a merely related comparison.
conditional = export_repro("minimal_conditional_positive_conjunct_replay.elisa")
conditional_goal = next(theorem for theorem in conditional["theorems"] if theorem["rule"] == "goal")
code, result = replay(conditional, "conditional-positive-conjunct")
assert code == 0 and result["status"] == "replayed", result
forged_conditional = with_theorem(conditional, conditional_goal)
forged_goal = forged_conditional["theorems"][0]
nodes = forged_conditional["kernel"]["nodes"]
original = nodes[forged_goal["conclusion"]]
assert original["kind"] == "binary" and original["operator"] == "or", original
at_root = next(index for index, node in enumerate(nodes)
               if node["kind"] == "ident" and node["name"] == "at")
two_root = append_node(forged_conditional, "int", value="2")
missing_conjunct = append_node(forged_conditional, "binary", ">=", at_root, two_root)
forged_goal["conclusion"] = append_node(forged_conditional, "binary", "or",
                                        original["left"], missing_conjunct)
forged_conditional["theorems"] = [reseal(forged_conditional, forged_goal)]
refused(forged_conditional, "conditional-fallback-without-conjunct", "rejected", "kernel-rejected")

# Root 51's bounded signed unit-shift rule must survive package export and replay in a fresh,
# standalone process; producer-side acceptance alone is not sufficient evidence.
signed_unit_shift = export_repro("minimal_conditional_signed_unit_shift_replay.elisa")
assert signed_unit_shift["source"]["admissible"] is True
assert len(signed_unit_shift["theorems"]) == 2, signed_unit_shift["theorems"]
code, result = replay(signed_unit_shift, "conditional-signed-unit-shift-root-51")
assert code == 0 and result["status"] == "replayed", result
assert result["summary"] == {"theorems": 2, "replayed": 2, "not_replayed": 0}, result

# The new branchwise conditional-result rule must decline a resealed goal with a bad result arm,
# and one whose left disjunct uses a nearby but different guard. The serialized node identities
# are changed, the theorem statement and fingerprint are recomputed, and the kernel still refuses.
conditional_package = copy.deepcopy(packages["conditional_result_branchwise_probe"])
conditional_theorem = next(t for t in conditional_package["theorems"]
                           if t["name"] == "conditional_result_both_arms" and t["rule"] == "goal")
kernel_nodes = conditional_package["kernel"]["nodes"]
conditional_goal = kernel_nodes[conditional_theorem["conclusion"]]
assert conditional_goal["kind"] == "binary" and conditional_goal["operator"] == "or", conditional_goal
left_comparison = kernel_nodes[conditional_goal["left"]]
right_comparison = kernel_nodes[conditional_goal["right"]]
assert left_comparison["kind"] == "binary" and right_comparison["kind"] == "binary", (left_comparison, right_comparison)
left_conditional = kernel_nodes[left_comparison["left"]]
right_conditional = kernel_nodes[right_comparison["left"]]
assert left_conditional["kind"] == "if" and right_conditional["kind"] == "if", (left_conditional, right_conditional)

bad_arm = copy.deepcopy(conditional_package)
bad_nodes = bad_arm["kernel"]["nodes"]
bad_theorem = copy.deepcopy(conditional_theorem)
bad_conditional = bad_nodes[left_comparison["left"]]
bad_value = append_node(bad_arm, "int", value="256")
bad_if = append_node(bad_arm, "if", left=bad_conditional["left"], right=bad_conditional["right"],
                     auxiliary=bad_value)
bad_left = append_node(bad_arm, "binary", "<", bad_if, left_comparison["right"])
bad_right = append_node(bad_arm, "binary", "==", bad_if, right_comparison["right"])
bad_goal = append_node(bad_arm, "binary", "or", bad_left, bad_right)
bad_theorem["conclusion"] = bad_goal
refused(with_theorem(bad_arm, reseal(bad_arm, bad_theorem)), "conditional-result-bad-arm", "rejected", "kernel-rejected")

altered_guard = copy.deepcopy(conditional_package)
altered_nodes = altered_guard["kernel"]["nodes"]
altered_theorem = copy.deepcopy(conditional_theorem)
altered_goal = altered_nodes[conditional_theorem["conclusion"]]
altered_left = altered_nodes[altered_goal["left"]]
altered_right = altered_nodes[altered_goal["right"]]
source_if = altered_nodes[altered_left["left"]]
source_guard = altered_nodes[source_if["left"]]
two = append_node(altered_guard, "int", value="2")
other_guard = append_node(altered_guard, "binary", "==", source_guard["left"], two)
other_if = append_node(altered_guard, "if", left=other_guard, right=source_if["right"], auxiliary=source_if["auxiliary"])
other_left = append_node(altered_guard, "binary", "<", other_if, altered_left["right"])
altered_root = append_node(altered_guard, "binary", "or", other_left, altered_goal["right"])
altered_theorem["conclusion"] = altered_root
refused(with_theorem(altered_guard, reseal(altered_guard, altered_theorem)),
        "conditional-result-altered-guard", "rejected", "kernel-rejected")

# Replay scratch quantifier binders are never part of the exported package.
quantified = packages["collection_quantifier"]
last_root = max(max([t["conclusion"]] + t["hypotheses"]) for t in quantified["theorems"])
assert len(quantified["kernel"]["nodes"]) == last_root + 1, (len(quantified["kernel"]["nodes"]), last_root)
assert not any(node["name"].startswith("__elisa_kernel_quantifier") for node in quantified["kernel"]["nodes"])

base = packages["verified"]
assumption = next(t for t in base["theorems"] if t["rule"] == "goal" and t["conclusion"] in t["hypotheses"])
runpy.run_path(str(ROOT / "scripts/tests/portable_replay_kernel_forgeries.py"), init_globals=globals())
runpy.run_path(str(ROOT / "scripts/tests/portable_replay_package_validation.py"), init_globals=globals())
runpy.run_path(str(ROOT / "scripts/tests/portable_replay_structure_fuzz.py"), init_globals=globals())
runpy.run_path(str(ROOT / "scripts/tests/portable_replay_raw_bytes.py"), init_globals=globals())
runpy.run_path(str(ROOT / "scripts/tests/portable_replay_package_atomicity.py"), init_globals=globals())
print("portable replay: %d packages replay; semantic and package-reader attacks are refused" % len(packages))
