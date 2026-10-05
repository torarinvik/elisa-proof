"""Adversarial UTF-8 and aggregate copied-string boundaries for portable packages."""

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
PROOF = Path(os.environ.get("ELISA_PROOF_BIN", ROOT / "build/elisa-proof"))
REPLAY = Path(os.environ.get("ELISA_PROOF_REPLAY_BIN", ROOT / "build/elisa-proof-replay"))
STRING_BUDGET_BYTES = 65536


def manifest(binary):
    path = Path(str(binary) + ".manifest.json")
    sidecar = Path(str(path) + ".sha256")
    raw = path.read_bytes()
    recorded = sidecar.read_text(encoding="ascii").strip()
    assert hashlib.sha256(raw).hexdigest() == recorded, f"bad manifest sidecar: {path}"
    value = json.loads(raw)
    assert value["binary"]["sha256"] == hashlib.sha256(Path(binary).read_bytes()).hexdigest()
    return value


def replay_bytes(data, path):
    path.write_bytes(data)
    process = subprocess.run([str(REPLAY), str(path)], capture_output=True, timeout=120)
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError((process.returncode, process.stdout, process.stderr)) from error
    return process.returncode, result


def package_bytes(package, marker):
    package["theorems"][0]["name"] = marker.decode("ascii")
    return json.dumps(package, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def utf8_probe(valid_package, payload, label, work, reason="utf8"):
    marker = b"R006-UTF8-BYTE-BOUNDARY-PROBE"
    raw = package_bytes(copy.deepcopy(valid_package), marker)
    assert raw.count(marker) == 1
    hostile = raw.replace(marker, payload, 1)
    code, report = replay_bytes(hostile, work / (label + ".json"))
    assert code == 1 and report.get("status") == "malformed" and report.get("reason") == reason, (
        label, code, report)


def append_string(package, text):
    package["kernel"]["nodes"].append({
        "kind": "string", "operator": "", "left": 0, "right": 0,
        "auxiliary": 0, "children_start": 0, "children_count": 0,
        "value": "0", "name": text, "secondary_name": "",
    })


def copied_node_string_bytes(package):
    fields = ("kind", "operator", "name", "secondary_name")
    return sum(len(node[field].encode("utf-8"))
               for node in package["kernel"]["nodes"] for field in fields)


def main():
    proof_manifest = manifest(PROOF)
    replay_manifest = manifest(REPLAY)
    assert proof_manifest["schema"] == replay_manifest["schema"] == "elisa-proof-build-manifest-v1"
    for field in ("frontend", "target", "optimization", "compile_mode", "proof"):
        if field == "proof":
            assert proof_manifest[field]["source_tree_sha256"] == replay_manifest[field]["source_tree_sha256"], field
        else:
            assert proof_manifest[field] == replay_manifest[field], field
    for field in ("stage", "source_revision", "product"):
        assert proof_manifest["compiler"][field] == replay_manifest["compiler"][field], field
    assert proof_manifest["compiler"]["stage"] == "stage1", proof_manifest["compiler"]
    assert proof_manifest["compiler"]["source_dirty"] is False
    assert replay_manifest["compiler"]["source_dirty"] is False

    exported = subprocess.run([str(PROOF), "--package", str(ROOT / "examples/verified.elisa")],
                              capture_output=True, timeout=120)
    assert exported.returncode == 0, (exported.returncode, exported.stderr.decode(errors="replace"))
    package = json.loads(exported.stdout)
    assert package["theorems"]

    truncated = [b"\xc2", b"\xe1", b"\xe1\x80", b"\xf1", b"\xf1\x80", b"\xf1\x80\x80"]
    bad_continuations = [
        b"\xc2A",
        b"\xe1A\x80", b"\xe1\x80A",
        b"\xf1A\x80\x80", b"\xf1\x80A\x80", b"\xf1\x80\x80A",
    ]
    invalid_sequences = {
        "overlong-two-byte": b"\xc0\xaf",
        "overlong-three-byte": b"\xe0\x80\x80",
        "overlong-four-byte": b"\xf0\x80\x80\x80",
        "surrogate": b"\xed\xa0\x80",
        "above-unicode-maximum": b"\xf4\x90\x80\x80",
        "stray-continuation": b"\x80",
        "invalid-lead": b"\xff",
    }

    with tempfile.TemporaryDirectory(prefix="elisa-proof-byte-boundaries-") as directory:
        work = Path(directory)
        for index, prefix in enumerate(truncated):
            utf8_probe(package, prefix, f"truncated-prefix-{index}-{prefix.hex()}", work)
        for index, sequence in enumerate(bad_continuations):
            utf8_probe(package, sequence, f"bad-continuation-position-{index}", work)
        for label, sequence in invalid_sequences.items():
            utf8_probe(package, sequence, label, work)

        # U+0000 is valid UTF-8 but forbidden as an unescaped byte in a JSON string. It must
        # fail package parsing rather than truncate the input or replay a prefix.
        utf8_probe(package, b"\x00", "embedded-nul", work, reason="json")

        exact = copy.deepcopy(package)
        existing_bytes = copied_node_string_bytes(exact)
        remaining_name_bytes = STRING_BUDGET_BYTES - existing_bytes - 2 * len("string")
        assert remaining_name_bytes > 1, remaining_name_bytes
        append_string(exact, "a" * (remaining_name_bytes // 2))
        append_string(exact, "b" * (remaining_name_bytes - remaining_name_bytes // 2))
        assert copied_node_string_bytes(exact) == STRING_BUDGET_BYTES
        exact_path = work / "aggregate-exact-limit.json"
        code, report = replay_bytes(json.dumps(exact).encode("utf-8"), exact_path)
        assert code == 0 and report.get("status") == "replayed", ("aggregate-exact-limit", code, report)

        over = copy.deepcopy(exact)
        over["kernel"]["nodes"][-1]["name"] += "c"
        code, report = replay_bytes(json.dumps(over).encode("utf-8"), work / "aggregate-one-over.json")
        assert code == 1 and report.get("status") == "over-budget" \
            and report.get("reason") == "string-budget", ("aggregate-one-over", code, report)

    print("portable package byte boundaries: truncated prefixes=6; invalid continuations=6; "
          "other malformed UTF-8=7; embedded NUL rejected; aggregate copied bytes 65536 accepted, "
          "65537 refused")


if __name__ == "__main__":
    main()
