"""Deterministic structure-aware mutation campaign for portable proof packages.

This complements the fixed package-cap tests and curated regression forgeries: it exports real
packages, mutates one semantic field (or one serialized byte) per case, and sends every input
through a fresh replay process. No timing threshold is used; subprocess deadlines only ensure a
decoder regression cannot hang the suite.
"""

import copy
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from portable_replay_support import BINARY as PRODUCER, REPLAY

TIMEOUT_SECONDS = 12
SEED = 0xE115A


def run(command, *, timeout=TIMEOUT_SECONDS):
    return subprocess.run(command, capture_output=True, text=True, check=False, timeout=timeout)


def export_package(example):
    result = run([str(PRODUCER), "--package", str(ROOT / "examples" / (example + ".elisa"))])
    assert result.returncode == 0, (example, result.returncode, result.stderr)
    package = json.loads(result.stdout)
    assert package["format"] == "elisa-proof-package-v1", example
    assert package["source"]["admissible"] is True, example
    assert package["theorems"], f"{example} must export at least one certificate"
    return package


def put_at_path(value, path, replacement):
    parent = value
    for part in path[:-1]:
        parent = parent[part]
    parent[path[-1]] = replacement


def get_at_path(value, path):
    for part in path:
        value = value[part]
    return value


def check_result_shape(result):
    assert result.get("format") == "elisa-proof-replay-result-v1", result
    assert result.get("trust") == {
        "kernel": "checked",
        "package_reader": "trusted",
        "hypotheses": "adapter",
        "source_correspondence": "adapter",
        "fingerprints": "identity-hint",
        "source_authenticated": False,
    }, result
    assert isinstance(result.get("summary"), dict), result
    assert set(result["summary"]) == {"theorems", "replayed", "not_replayed"}, result


def write_and_replay(directory, label, payload):
    path = directory / (label + ".json")
    if isinstance(payload, bytes):
        path.write_bytes(payload)
    else:
        path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    # subprocess.run starts a brand-new process; the decoder has no producer-side state.
    result = run([str(REPLAY), str(path)])
    assert result.returncode in (0, 1), (label, result.returncode, result.stdout, result.stderr)
    assert len(result.stdout.encode("utf-8")) <= 4 * 1024 * 1024, (label, "unbounded stdout")
    assert len(result.stderr.encode("utf-8")) <= 4 * 1024 * 1024, (label, "unbounded stderr")
    decoded = json.loads(result.stdout)
    check_result_shape(decoded)
    return result.returncode, decoded


def assert_refused(directory, label, payload):
    code, result = write_and_replay(directory, label, payload)
    assert code == 1, (label, code, result)
    assert result["status"] in {"malformed", "rejected", "over-budget"}, (label, result)
    # This campaign uses a single-theorem fixture. Refusal must never leak a successful theorem
    # or a positive replay count, even if decoder work reached theorem validation.
    assert result["summary"]["replayed"] == 0, (label, result)
    assert result["summary"]["not_replayed"] == result["summary"]["theorems"], (label, result)
    assert len(result.get("theorems", [])) == result["summary"]["theorems"], (label, result)
    assert all(theorem.get("status") != "replayed" for theorem in result.get("theorems", [])), (label, result)


def assert_no_publication(directory, label, payload, expected_reason):
    code, result = write_and_replay(directory, label, payload)
    assert code == 1 and result["status"] == "malformed" \
        and result.get("reason") == expected_reason, (label, code, result)
    assert result["theorems"] == [], (label, result)
    assert result["summary"] == {"theorems": 0, "replayed": 0, "not_replayed": 0}, (label, result)


def mutate_field(package, path, replacement):
    changed = copy.deepcopy(package)
    previous = get_at_path(changed, path)
    assert previous != replacement or type(previous) is not type(replacement), (path, previous, replacement)
    put_at_path(changed, path, replacement)
    return changed


def delete_field(package, path):
    changed = copy.deepcopy(package)
    parent = changed
    for part in path[:-1]:
        parent = parent[part]
    del parent[path[-1]]
    return changed


def single_theorem_fixture(package):
    # Project an exported valid package to one of its independently replayable certificates.
    # This gives refusal checks an unambiguous "no theorem partially accepted" assertion.
    fixture = copy.deepcopy(package)
    fixture["theorems"] = [fixture["theorems"][0]]
    return fixture


def main():
    packages = [single_theorem_fixture(export_package("verified")),
                single_theorem_fixture(export_package("checked_index_fallback"))]
    base = packages[0]
    theorem = base["theorems"][0]
    nodes = base["kernel"]["nodes"]
    compound_index = next(i for i, node in enumerate(nodes) if node["kind"] == "binary")
    compound = nodes[compound_index]
    child_index = next(i for i, node in enumerate(nodes) if node["children_count"] > 0)
    child_node = nodes[child_index]

    # These single-field mutations stay below resource caps so they exercise schema and
    # reference validation rather than the separate aggregate-budget boundary tests.
    cases = [
        ("unknown-package-tag", ("format",), "elisa-proof-package-v2"),
        ("unknown-node-tag", ("kernel", "nodes", theorem["conclusion"], "kind"), "proof-oracle"),
        ("node-tag-case", ("kernel", "nodes", theorem["conclusion"], "kind"),
         nodes[theorem["conclusion"]]["kind"].upper()),
        ("bad-node-integer-spelling", ("kernel", "nodes", theorem["conclusion"], "value"), "01"),
        ("node-index-negative", ("kernel", "nodes", child_index, "children_start"), -1),
        ("node-index-noninteger", ("kernel", "nodes", child_index, "children_start"), "0"),
        ("theorem-reference-bool", ("theorems", 0, "conclusion"), True),
        ("theorem-reference-out-of-range", ("theorems", 0, "conclusion"), len(nodes) + 5),
        ("theorem-line-float", ("theorems", 0, "line"), 1.25),
        ("theorem-id-bool", ("theorems", 0, "goal_id"), True),
        ("theorem-name-type", ("theorems", 0, "name"), []),
        ("theorem-statement-type", ("theorems", 0, "statement"), {}),
        ("theorem-hypotheses-type", ("theorems", 0, "hypotheses"), "0"),
        ("theorem-hypothesis-id-bool", ("theorems", 0, "hypotheses"), [True]),
        ("wrong-source-bytes-type", ("source", "bytes"), "371"),
        ("source-path-null", ("source", "path"), None),
        ("source-bytes-bool", ("source", "bytes"), True),
        ("source-fingerprint-tag", ("source", "fingerprint", "algorithm"), "sha256"),
        ("source-fingerprint-out-of-range", ("source", "fingerprint", "value"), 2**32),
        ("unauthenticated-source-upgrade", ("source", "authenticated"), True),
        ("source-admission-revocation", ("source", "admissible"), False),
        ("trust-hypothesis-upgrade", ("trust", "hypotheses"), "kernel"),
        ("trust-correspondence-upgrade", ("trust", "source_correspondence"), "checked"),
        ("trust-fingerprint-upgrade", ("trust", "fingerprints"), "cryptographic"),
        ("theorem-checksum-bitflip", ("theorems", 0, "goal_fingerprint"),
         theorem["goal_fingerprint"] ^ 1),
        ("theorem-rule-tag", ("theorems", 0, "rule"), "untrusted-oracle"),
        ("length-child-span-overrun", ("kernel", "nodes", child_index, "children_count"),
         child_node["children_count"] + len(base["kernel"]["children"]) + 1),
        ("nested-span-start-at-end-with-positive-count",
         ("kernel", "nodes", child_index, "children_start"), len(base["kernel"]["children"])),
        ("nested-span-overflowing-start-and-count",
         ("kernel", "nodes", child_index, "children_start"), 2**63 - 1),
        ("nested-span-negative-count", ("kernel", "nodes", child_index, "children_count"), -1),
        ("length-truncate-child-arena", ("kernel", "children"), base["kernel"]["children"][:-1]),
        ("length-truncate-node-arena", ("kernel", "nodes"), nodes[:theorem["conclusion"]]),
        ("node-operator-type", ("kernel", "nodes", compound_index, "operator"), 0),
        ("node-left-id-bool", ("kernel", "nodes", compound_index, "left"), True),
        ("node-auxiliary-type", ("kernel", "nodes", compound_index, "auxiliary"), "0"),
        ("node-child-start-float", ("kernel", "nodes", child_index, "children_start"), 0.5),
        ("node-child-count-bool", ("kernel", "nodes", child_index, "children_count"), False),
        ("node-child-count-inexact-bound", ("kernel", "nodes", child_index, "children_count"), 2**53),
        ("node-child-count-signed-limit", ("kernel", "nodes", child_index, "children_count"), 2**63 - 1),
        ("node-name-type", ("kernel", "nodes", compound_index, "name"), []),
        ("node-secondary-name-type", ("kernel", "nodes", compound_index, "secondary_name"), {}),
        ("child-id-float", ("kernel", "children", 0), 0.5),
        ("child-id-out-of-range", ("kernel", "children", 0), len(nodes) + 1),
        # A backward edge is legal in neither the package DAG nor the identity traversal.
        ("dag-self-cycle", ("kernel", "nodes", compound_index, "left"), compound_index),
        ("dag-invalid-reference", ("kernel", "nodes", compound_index, "right"), len(nodes) + 1),
    ]

    rng = random.Random(SEED)
    # Add reproducible mutations sampled from actual records; values stay small and within
    # global caps so each fresh decoder process exercises semantic validation.
    candidate_indices = [i for i, node in enumerate(nodes) if node["kind"] in {"int", "ident", "binary"}]
    rng.shuffle(candidate_indices)
    for index in candidate_indices[:6]:
        node = nodes[index]
        if node["kind"] == "int":
            cases.append((f"seed-{SEED:x}-integer-{index}", ("kernel", "nodes", index, "value"), "-00"))
        elif node["kind"] == "ident":
            cases.append((f"seed-{SEED:x}-identifier-{index}", ("kernel", "nodes", index, "secondary_name"), "\u0000"))
        else:
            edge = "left" if rng.randrange(2) == 0 else "right"
            cases.append((f"seed-{SEED:x}-edge-{index}", ("kernel", "nodes", index, edge), len(nodes) + 2))

    with tempfile.TemporaryDirectory(prefix="elisa-package-mutation-") as temporary:
        directory = Path(temporary)
        # Establish both projected fixtures as independently replayable before mutation.
        for index, fixture in enumerate(packages):
            code, result = write_and_replay(directory, f"valid-fixture-{index}", fixture)
            assert code == 0 and result["status"] == "replayed", (index, result)
            assert result["summary"]["replayed"] == 1, (index, result)

        for label, path, value in cases:
            assert_refused(directory, label, mutate_field(base, path, value))

        one_over_empty_span = copy.deepcopy(base)
        one_over_empty_span["kernel"]["nodes"][child_index]["children_start"] = \
            len(one_over_empty_span["kernel"]["children"]) + 1
        one_over_empty_span["kernel"]["nodes"][child_index]["children_count"] = 0
        assert_refused(directory, "nested-span-zero-count-start-one-over", one_over_empty_span)

        # A zero-length nested span exactly at the child-arena end is the inclusive boundary.
        # Its one-over neighbor is covered above and must fail closed, even though it refers to
        # no child. This catches unchecked start+count arithmetic and off-by-one range tests.
        exact_empty_span = copy.deepcopy(base)
        exact_empty_span["kernel"]["nodes"].append({
            "kind": "array", "operator": "", "left": 0, "right": 0, "auxiliary": 0,
            "children_start": len(exact_empty_span["kernel"]["children"]), "children_count": 0,
            "value": "0", "name": "", "secondary_name": "",
        })
        code, result = write_and_replay(directory, "nested-span-exact-empty-boundary", exact_empty_span)
        assert code == 0 and result["status"] == "replayed" \
            and result["summary"]["replayed"] == 1, result

        # Repeated goal IDs are accepted by the current package contract; they must not alias a
        # replay cache entry. The second record is independently rejected when its fingerprint
        # is forged, instead of inheriting the first record's successful result.
        duplicate_ids = copy.deepcopy(base)
        second = copy.deepcopy(duplicate_ids["theorems"][0])
        second["name"] = "same-id-independent-record"
        duplicate_ids["theorems"].append(second)
        code, result = write_and_replay(directory, "duplicate-goal-id-independent-replay", duplicate_ids)
        assert code == 0 and result["status"] == "replayed" \
            and result["summary"] == {"theorems": 2, "replayed": 2, "not_replayed": 0}, result
        assert [item["goal_id"] for item in result["theorems"]] == [
            duplicate_ids["theorems"][0]["goal_id"], duplicate_ids["theorems"][0]["goal_id"]], result

        duplicate_ids["theorems"][1]["goal_fingerprint"] ^= 1
        code, result = write_and_replay(directory, "duplicate-goal-id-cache-isolation", duplicate_ids)
        assert code == 1 and result["status"] == "rejected" \
            and result["summary"] == {"theorems": 2, "replayed": 1, "not_replayed": 1}, result
        assert [item["status"] for item in result["theorems"]] == ["replayed", "rejected"], result

        # Package-wide structure validation precedes per-theorem replay/publication. Even with
        # two valid theorem records before the malformed arena entry, no prefix may escape.
        late_global_error = copy.deepcopy(duplicate_ids)
        late_global_error["theorems"][1]["goal_fingerprint"] ^= 1
        late_global_error["kernel"]["nodes"][0]["unexpected"] = True
        assert_no_publication(directory, "late-global-schema-error-no-partial-theorems",
                              late_global_error, "node-schema")

        # A malformed theorem record late in the list must not publish results for the valid
        # prefix. Package schema admission is all-or-nothing even though theorem replay itself
        # is performed sequentially; a rejected package has no theorem/cache publication.
        late_theorem_schema_error = copy.deepcopy(duplicate_ids)
        del late_theorem_schema_error["theorems"][1]["statement"]
        assert_no_publication(directory, "late-theorem-schema-error-no-partial-theorems",
                              late_theorem_schema_error, "theorem-schema")

        schema_cases = [
            ("missing-source-authenticated", ("source", "authenticated")),
            ("missing-fingerprint-value", ("source", "fingerprint", "value")),
            ("missing-node-kind", ("kernel", "nodes", theorem["conclusion"], "kind")),
            ("missing-theorem-statement", ("theorems", 0, "statement")),
        ]
        for label, path in schema_cases:
            assert_refused(directory, label, delete_field(base, path))

        extra_node_field = copy.deepcopy(base)
        extra_node_field["kernel"]["nodes"][theorem["conclusion"]]["unexpected"] = 0
        assert_refused(directory, "extra-reachable-node-field", extra_node_field)
        invalid_child_id = copy.deepcopy(base)
        invalid_child_id["kernel"]["children"].append(True)
        assert_refused(directory, "child-id-bool", invalid_child_id)

        # A one-byte discriminator corruption remains parseable; truncation separately exercises
        # incomplete-token handling.
        encoded = json.dumps(base, separators=(",", ":"))
        marker = '"format":"elisa-proof-package-v1"'
        marker_start = encoded.index(marker) + len('"format":"')
        byte_changed = encoded[:marker_start] + "X" + encoded[marker_start + 1:]
        assert_refused(directory, "single-byte-format-tag", byte_changed.encode("utf-8"))
        assert_refused(directory, "truncated-json-tail", encoded[:-1].encode("utf-8"))

        # These source identity hints are deliberately non-authoritative. Their mutation may
        # replay only because the theorem certificate itself is freshly checked by this process.
        harmless = mutate_field(base, ("source", "path"), "renamed-untrusted-source.elisa")
        code, result = write_and_replay(directory, "source-path-hint-only", harmless)
        assert code == 0 and result["status"] == "replayed", result
        assert result["summary"]["replayed"] == len(harmless["theorems"]), result

        changed_fingerprint = copy.deepcopy(base)
        old_fingerprint = changed_fingerprint["source"]["fingerprint"]["value"]
        changed_fingerprint["source"]["fingerprint"]["value"] = old_fingerprint ^ 1
        code, result = write_and_replay(directory, "source-fingerprint-hint-only", changed_fingerprint)
        assert code == 0 and result["status"] == "replayed", result
        assert result["summary"]["replayed"] == len(changed_fingerprint["theorems"]), result

    refused_count = len(cases) + len(schema_cases) + 6
    print(f"package mutation campaign: {refused_count} adversarial inputs refused; exact empty-span boundary and duplicate-ID cache isolation checked; 2 hint-only edits freshly replayed; seed={SEED}")


if __name__ == "__main__":
    main()
