"""Single entry point for portable package production, replay, and adversarial checks."""
import json
from pathlib import Path
import runpy
import subprocess

from portable_replay_support import *

ROOT = Path(__file__).resolve().parents[1]

# One example per kernel rule family; export and replay each positive package exactly once.
POSITIVE = {
    "global_constant_module": {"goal", "resource-safety"},
    "module_negative_i64_constant_contract": {"goal", "resource-safety"},
    "verified": {"goal"},
    "collection_quantifier": {"quantifier-forall", "quantifier-exists"},
    "checked_index_fallback": {"checked-index"},
    "getelse_recovery": {"checked-get"},
    "effect_containment": {"effect-containment"},
    "implicit_structural_decreases": {"structural-safety"},
    "early_return_index_guard": {"index-lower", "index-upper"},
    "fixed_array_slice_bounds": {"slice-lower", "slice-upper", "slice-order"},
    "pure_unfolding": {"goal"},
    "goal_disjunct_split_probe": {"goal", "resource-safety"},
    "disjunctive_goals": {"goal", "index-upper"},
    "leaving_branch_join": {"goal", "index-upper"},
    "linear_disequality_refuted": {"goal", "resource-safety"},
    "closed_goal_width_uniform": {"goal", "resource-safety"},
}
packages = {}
for example, rules in POSITIVE.items():
    package = export(example)
    packages[example] = package
    assert package["format"] == "elisa-proof-package-v1" and package["source"]["admissible"], example
    assert package["source"]["authenticated"] is False, example
    seen = {theorem["rule"] for theorem in package["theorems"]}
    assert rules <= seen, (example, rules, seen)
    for theorem in package["theorems"]:
        assert theorem["statement"] == statement(package, theorem["hypotheses"], theorem["conclusion"]), (example, theorem["name"])
        assert theorem["goal_fingerprint"] == fnv1a32(theorem["statement"]), (example, theorem["name"])
    code, result = replay(package, example)
    assert code == 0 and result["status"] == "replayed", (example, result)
    assert result["summary"] == {"theorems": len(package["theorems"]),
                                 "replayed": len(package["theorems"]), "not_replayed": 0}, result
    report = json.loads(subprocess.run([str(BINARY), "--json", str(ROOT / "examples" / (example + ".elisa"))],
                                       capture_output=True, text=True, timeout=120).stdout)
    replayed_goals = [goal for goal in report["goals"] if goal["proven"] and goal.get("replay_status") == "replayed"]
    assert len(package["theorems"]) == len(replayed_goals), (example, len(package["theorems"]), len(replayed_goals))

# Replay scratch quantifier binders are never part of the exported package.
quantified = packages["collection_quantifier"]
last_root = max(max([t["conclusion"]] + t["hypotheses"]) for t in quantified["theorems"])
assert len(quantified["kernel"]["nodes"]) == last_root + 1, (len(quantified["kernel"]["nodes"]), last_root)
assert not any(node["name"].startswith("__elisa_kernel_quantifier") for node in quantified["kernel"]["nodes"])

base = packages["verified"]
assumption = next(t for t in base["theorems"] if t["rule"] == "goal" and t["conclusion"] in t["hypotheses"])
runpy.run_path(str(ROOT / "scripts/tests/portable_replay_kernel_forgeries.py"), init_globals=globals())
runpy.run_path(str(ROOT / "scripts/tests/portable_replay_package_validation.py"), init_globals=globals())
print("portable replay: %d packages replay; semantic and package-reader attacks are refused" % len(packages))
