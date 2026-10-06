"""Two-hop reference frames replay exact places and fail closed on aliases and stale borrows."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PRODUCER = os.environ.get("ELISA_PROOF_BIN", str(ROOT / "build/elisa-proof"))
REPLAY = os.environ.get("ELISA_PROOF_REPLAY_BIN", str(ROOT / "build/elisa-proof-replay"))

SOURCE = """\
struct Box:
    values: mutable darray[i64]
    other: mutable i64

def write_value_at(box: mutable Box&, index: usize) -> void:
    requires index >= 0 and index < box.values.count
    changes box.values
    box.values[index] <- 1

def forward_value_at(box: mutable Box&, index: usize) -> void:
    requires index >= 0 and index < box.values.count
    changes box.values
    write_value_at(box, index)

def forwarded(box: mutable Box&, index: usize) -> i64:
    requires index >= 0 and index < box.values.count
    changes box.values
    preserves box.other
    forward_value_at(box, index)
    return 13

def wrong_place(box: mutable Box&, other: mutable Box&, index: usize) -> void:
    requires index >= 0 and index < other.values.count
    changes box.values
    forward_value_at(other, index)

def forwarded_alias(box: mutable Box&, index: usize) -> void:
    requires index >= 0 and index < box.values.count
    changes box.values
    preserves box.other
    alias: mutable Box& = box
    write_other_at(alias)

def write_other_at(box: mutable Box&) -> void:
    changes box.other
    box.other <- 2

def overwrite_cell(cell: mutable i64&) -> void:
    changes cell
    cell <- 3

def stale_place_after_push(box: mutable Box&, value: i64) -> void can[Memory.Allocate]:
    requires box.values.count > 0
    changes box.values
    preserves box.other
    cell: mutable i64& = &box.values[0]
    box.values.push(value)
    overwrite_cell(cell)
"""

PORTABLE_SOURCE = """\
struct Box:
    values: mutable darray[i64]
    other: mutable i64

def write_value_at(box: mutable Box&, index: usize) -> void:
    requires index >= 0 and index < box.values.count
    box.values[index] <- 1

def forward_value_at(box: mutable Box&, index: usize) -> void:
    requires index >= 0 and index < box.values.count
    write_value_at(box, index)

def forwarded(box: mutable Box&, index: usize) -> i64:
    requires index >= 0 and index < box.values.count
    forward_value_at(box, index)
    return 13
"""


def run_json(path):
    result = subprocess.run(
        [PRODUCER, "--json", str(path)], capture_output=True, text=True, timeout=180
    )
    return result.returncode, json.loads(result.stdout)


def check_replay_free(report, label):
    replay = report["replay"]
    assert replay["gaps"] == 0, (label, replay)
    assert replay["certificates"] == replay["replayed"], (label, replay)


def independently_replay(source_path, directory):
    produced = subprocess.run(
        [PRODUCER, "--package", str(source_path)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert produced.returncode in (0, 1), produced.stderr or produced.stdout
    package = json.loads(produced.stdout)
    assert package["source"]["admissible"], package["source"]

    def replay_package(value, name):
        package_path = directory / f"{name}.package.json"
        package_path.write_text(json.dumps(value), encoding="utf-8")
        return subprocess.run(
            [REPLAY, str(package_path)], capture_output=True, text=True, timeout=180
        )

    replayed = replay_package(package, "frame-forwarding")
    data = json.loads(replayed.stdout)
    assert data["status"] == "replayed", data
    assert data["summary"]["not_replayed"] == 0, data

    # A valid-looking resource-call argument must still resolve to the caller's live reference
    # binding. Substituting an in-scope scalar ident for the forwarded root preserves JSON shape
    # but must make the resource certificate fail independent replay.
    forged = copy.deepcopy(package)
    nodes = forged["kernel"]["nodes"]
    actual_indices = [index for index, node in enumerate(nodes)
                      if node["kind"] == "resource-call-arg"
                      and node["operator"] == "reference" and node["name"] == "box"]
    assert len(actual_indices) >= 2, "both call boundaries must carry reference witnesses"
    wrong_root = next(index for index, node in enumerate(nodes)
                      if node["kind"] == "ident" and node["name"] == "index")
    for boundary, actual_index in enumerate(actual_indices):
        forged = copy.deepcopy(package)
        forged["kernel"]["nodes"][actual_index]["left"] = wrong_root
        refused = replay_package(forged, f"frame-forwarding-wrong-root-{boundary}")
        refused_data = json.loads(refused.stdout)
        assert refused.returncode == 1 and refused_data["status"] == "rejected", refused_data
        assert refused_data["reason"] == "kernel-rejected", refused_data


# Pin the reported indexed-frame shape itself: the current producer must not emit either opaque
# frame diagnostic for its by-reference `box` argument, and every produced certificate replays.
_, indexed_report = run_json(ROOT / "examples" / "indexed_frame.elisa")
assert indexed_report["summary"]["semantic_errors"] == 0, indexed_report["summary"]
assert indexed_report["summary"]["proven"] == indexed_report["summary"]["obligations"], indexed_report["summary"]
assert not any(finding["kind"] in {"frame-call-opaque", "frame-preserve-opaque"}
               and finding["name"] == "caller_preserves_other"
               for finding in indexed_report["findings"]), indexed_report["findings"]
indexed_caller = next(function for function in indexed_report["functions"]
                      if function["name"] == "caller_preserves_other")
assert indexed_caller["proved"], indexed_caller
check_replay_free(indexed_report, "indexed_frame baseline")

with tempfile.TemporaryDirectory(prefix="elisa-byref-frame-forwarding-") as directory_name:
    directory = Path(directory_name)
    source_path = directory / "forwarding.elisa"
    source_path.write_text(SOURCE, encoding="utf-8")
    code, report = run_json(source_path)
    assert code == 1 and report["status"] == "failed", (code, report["status"])
    assert report["summary"]["semantic_errors"] == 1, report["summary"]
    assert any("storage dependency facts were invalidated by darray push of box"
               in diagnostic["message"]
               for diagnostic in report["semantic_diagnostics"]), report["semantic_diagnostics"]
    check_replay_free(report, "forwarding source report")

    forwarded = [goal for goal in report["goals"] if goal["name"] == "forwarded"]
    assert forwarded and all(goal["proven"] for goal in forwarded), forwarded
    calls = [node for node in report["kernel"]["nodes"] if node["kind"] == "resource-call"]
    assert {"forward_value_at", "write_value_at"} <= {
        node["name"] for node in calls
    }, "both forwarding boundaries must record resource transitions"
    call = next((node for node in calls if node["name"] == "forward_value_at"), None)
    assert call is not None, "outer forwarded call did not record a resource transition"
    actuals = report["kernel"]["children"][call["children_start"] : call["children_start"] + call["children_count"]]
    reference = next(
        (report["kernel"]["nodes"][root] for root in actuals
         if report["kernel"]["nodes"][root]["kind"] == "resource-call-arg"
         and report["kernel"]["nodes"][root]["name"] == "box"),
        None,
    )
    assert reference is not None and reference["operator"] == "reference", reference
    source_place = report["kernel"]["nodes"][reference["left"]]
    assert source_place["kind"] == "ident" and source_place["name"] == "box", source_place

    wrong = [goal for goal in report["goals"] if goal["name"] == "wrong_place"]
    assert wrong, "wrong-place case produced no caller obligations"
    wrong_findings = [finding for finding in report["findings"]
                      if finding["name"] == "wrong_place"]
    assert any(finding["kind"] == "frame-call-outside"
               and finding["status"] == "disproved" for finding in wrong_findings), wrong_findings
    assert not any(finding["kind"] == "frame-call-opaque"
                   for finding in wrong_findings), wrong_findings

    alias = [goal for goal in report["goals"] if goal["name"] == "forwarded_alias"]
    alias_function = next(function for function in report["functions"]
                          if function["name"] == "forwarded_alias")
    assert not alias_function["proved"], alias_function
    alias_findings = [finding for finding in report["findings"]
                      if finding["name"] == "forwarded_alias"]
    assert any(finding["kind"] == "borrow-source-opaque"
               and finding["status"] == "unsupported" for finding in alias_findings), alias_findings
    assert any(finding["kind"] == "frame-preserve-violated"
               and finding["status"] == "disproved" for finding in alias_findings), alias_findings
    stale_findings = [finding for finding in report["findings"]
                      if finding["name"] == "stale_place_after_push"]
    assert any(finding["kind"] == "borrow-write-conflict"
               and finding["status"] == "disproved" for finding in stale_findings), stale_findings
    positive_path = directory / "forwarding-positive.elisa"
    positive_path.write_text(PORTABLE_SOURCE, encoding="utf-8")
    _, positive_report = run_json(positive_path)
    assert positive_report["summary"]["proven"] == positive_report["summary"]["obligations"], positive_report["summary"]
    assert positive_report["findings"] == [], positive_report["findings"]
    assert positive_report["summary"]["semantic_errors"] == 0, positive_report["summary"]
    check_replay_free(positive_report, "forwarding positive report")
    positive_goals = [goal for goal in positive_report["goals"]
                      if goal["name"] == "forwarded"]
    assert positive_goals and all(goal["proven"] for goal in positive_goals), positive_goals
    independently_replay(positive_path, directory)

print("by-reference frame forwarding: two-hop frame replayed; forged roots, wrong-place, alias and post-reallocation borrows refused")
