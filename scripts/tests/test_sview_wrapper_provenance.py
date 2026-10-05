"""Exercise exact sview provenance through a real two-wrapper argument permutation."""

import copy
import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PRODUCER = ROOT / "build/elisa-proof"
REPLAY = ROOT / "build/elisa-proof-replay"


def invoke(command):
    return subprocess.run(command, capture_output=True, text=True, timeout=120)


def proof_report(fixture):
    source = ROOT / "examples" / f"{fixture}.elisa"
    result = invoke([str(PRODUCER), "--json", str(source)])
    assert result.returncode in (0, 1), (fixture, result.returncode, result.stderr)
    return json.loads(result.stdout), result.returncode


positive, positive_exit = proof_report("sview_call_return_provenance")
assert positive_exit == 0, positive
assert positive["status"] == "proved", positive["status"]
assert positive["summary"]["semantic_errors"] == 0
assert positive["findings"] == []
assert positive["replay"]["gaps"] == 0
assert positive["replay"]["certificates"] == positive["replay"]["replayed"] > 0

# The first wrapper returns formal `first`; its caller permutes the arguments, so the outer
# summary must name formal `second` and preserve the same region parameter `r`.
return_witnesses = [
    node
    for node in positive["kernel"]["nodes"]
    if node["kind"] == "resource-region-return" and node["operator"] == "sview-call"
]
assert len(return_witnesses) == 1, return_witnesses
assert return_witnesses[0]["name"] == "r", return_witnesses[0]
assert return_witnesses[0]["secondary_name"] == "second", return_witnesses[0]

# Replay the actual persisted certificate in a separate, source-independent process. Then alter
# the exact owner and lifetime claims while keeping the theorem/proof package otherwise intact.
package_result = invoke(
    [str(PRODUCER), "--package", str(ROOT / "examples/sview_call_return_provenance.elisa")]
)
assert package_result.returncode == 0, package_result.stderr
valid_package = json.loads(package_result.stdout)
with tempfile.TemporaryDirectory(prefix="elisa-proof-r047-sview-") as directory:
    package_path = Path(directory) / "package.json"
    package_path.write_text(json.dumps(valid_package), encoding="utf-8")
    valid_replay = invoke([str(REPLAY), str(package_path)])
    valid_result = json.loads(valid_replay.stdout)
    assert valid_replay.returncode == 0, valid_result
    assert valid_result["status"] == "replayed", valid_result
    assert valid_result["summary"]["replayed"] == valid_result["summary"]["theorems"] == 6

    for mutation, expected_claim in (("wrong-owner", "first"), ("wrong-region", "dead_region")):
        forged = copy.deepcopy(valid_package)
        witness = next(
            node
            for node in forged["kernel"]["nodes"]
            if node["kind"] == "resource-region-return" and node["operator"] == "sview-call"
        )
        if mutation == "wrong-owner":
            witness["secondary_name"] = expected_claim
        else:
            witness["name"] = expected_claim
        forged_path = Path(directory) / f"{mutation}.json"
        forged_path.write_text(json.dumps(forged), encoding="utf-8")
        rejected = invoke([str(REPLAY), str(forged_path)])
        rejected_result = json.loads(rejected.stdout)
        assert rejected.returncode == 1, (mutation, rejected_result)
        assert rejected_result["status"] == "rejected", (mutation, rejected_result)
        assert rejected_result["reason"] == "kernel-rejected", (mutation, rejected_result)
        assert rejected_result["summary"]["not_replayed"] >= 1, (mutation, rejected_result)

# Mutating/reallocating the selected backing store is refused, as are views whose region has
# ended or whose alias/aggregate would carry a lifetime beyond its owner.
negative_cases = {
    "rejected_sview_call_return_wrong_provenance": "borrow-write-conflict",
    "rejected_sview_return_after_region_destroy": "region-destroy-live-borrow",
    "rejected_sview_after_region_destroy": "region-destroy-live-borrow",
    "rejected_sview_alias_region_escape": "region-alias-unsupported",
    "rejected_sview_aggregate_region_escape": "region-alias-unsupported",
}
for fixture, expected_finding in negative_cases.items():
    report, exit_code = proof_report(fixture)
    assert exit_code == 1, (fixture, exit_code, report.get("status"))
    assert report["status"] == "failed", (fixture, report.get("status"))
    assert report["verification_state"] != "proved", (fixture, report["verification_state"])
    assert report["replay"]["gaps"] == 0, (fixture, report["replay"])
    assert report["replay"]["certificates"] == report["replay"]["replayed"], (fixture, report["replay"])
    assert expected_finding in {finding["kind"] for finding in report["findings"]}, (
        fixture,
        report["findings"],
    )

print(
    "sview wrapper provenance: exact returned formal and region replay; wrong-owner/region "
    "certificates, backing reallocation, region escape and ended-lifetime controls refused"
)
