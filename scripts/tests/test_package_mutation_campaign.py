"""Deterministic structure-aware mutation campaign for portable proof packages.

This complements the fixed package-cap tests and curated regression forgeries: it exports real
packages, mutates one semantic field (or one serialized byte) per case, and sends every input
through a fresh replay process. No timing threshold is used; subprocess deadlines only ensure a
decoder regression cannot hang the suite.
"""

import copy
import json
import os
from pathlib import Path
import random
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
PRODUCER = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
REPLAY = Path(os.environ.get("ELISA_PROOF_REPLAY_BIN", ROOT / "build/elisa-proof-replay"))
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
    assert all(theorem.get("status") != "replayed" for theorem in result.get("theorems", [])), (label, result)


def mutate_field(package, path, replacement):
    changed = copy.deepcopy(package)
    previous = get_at_path(changed, path)
    assert previous != replacement, (path, previous, replacement)
    put_at_path(changed, path, replacement)
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
        ("wrong-source-bytes-type", ("source", "bytes"), "371"),
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
        ("length-truncate-child-arena", ("kernel", "children"), base["kernel"]["children"][:-1]),
        ("length-truncate-node-arena", ("kernel", "nodes"), nodes[:theorem["conclusion"]]),
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

    print(f"package mutation campaign: {len(cases) + 2} adversarial inputs refused; 2 hint-only edits freshly replayed; seed={SEED}")


if __name__ == "__main__":
    main()
