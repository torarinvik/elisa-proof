"""Package reader, schema, decoder, resource-budget, and report-boundary probes.

Loaded by ``scripts/test_portable_replay.py`` after its single producer/export setup. The
provided namespace contains the positive packages and shared forgery/replay helpers.
"""
import copy
import json
import subprocess

from portable_replay_support import *


def refused_without_theorem_publication(package, name, status, reason):
    path = WORK / (name + ".json")
    path.write_text(json.dumps(package, separators=(",", ":")), encoding="utf-8")
    checked = subprocess.run([str(REPLAY), str(path)], capture_output=True, timeout=120)
    assert len(checked.stdout) <= 4096 and len(checked.stderr) <= 4096, (name, "unbounded refusal")
    result = json.loads(checked.stdout)
    assert checked.returncode == 1 and result.get("status") == status \
        and result.get("reason") == reason, (name, checked.returncode, result)
    assert result.get("theorems") == [], (name, result)
    assert result.get("summary") == {"theorems": 0, "replayed": 0, "not_replayed": 0}, (name, result)
    return result


def duplicate_object_member(serialized, object_marker, key_token):
    """Append a repeated member to a selected emitted object without normalizing its JSON."""
    marker = serialized.index(object_marker)
    opening = serialized.index("{", marker + len(object_marker) - 1)
    depth = 0
    in_string = False
    escaped = False
    for offset in range(opening, len(serialized)):
        char = serialized[offset]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return serialized[:offset] + "," + key_token + ":null" + serialized[offset:]
    raise AssertionError(("unterminated object", object_marker))

# Header, trust and schema: nothing is inferred, over-claimed or accepted twice.
text = json.dumps(with_theorem(base, assumption))
valid_header = with_theorem(base, assumption)
code, result = replay(valid_header, "required-header-positive")
assert code == 0 and result["status"] == "replayed", result
wrong_source_type = copy.deepcopy(valid_header)
wrong_source_type["source"] = 7
result = refused(wrong_source_type, "source-object-replaced-by-integer", "malformed", "source-schema")
assert result["summary"] == {"theorems": 0, "replayed": 0, "not_replayed": 0}, result
assert result["theorems"] == [], result
missing_header = copy.deepcopy(valid_header)
del missing_header["trust"]
result = refused(missing_header, "required-header-missing-trust", "malformed", "package-schema")
assert result["summary"] == {"theorems": 0, "replayed": 0, "not_replayed": 0}, result
assert result["theorems"] == [], result
refused(text.replace('{"format": ', '{"format": "elisa-proof-package-v1", "format": ', 1),
        "duplicate-key", "malformed", "package-schema")

# The package parser preserves repeated JSON members. Every object that can affect admission,
# resource bounds, theorem roots, or replay identity must therefore reject a duplicate before
# field lookup can inherit first-wins/last-wins behavior. Include an escaped spelling of the same
# top-level key: key decoding must not let a duplicate bypass the exact-member-count check.
serialized = json.dumps(valid_header, separators=(",", ":"))
duplicate_key_cases = (
    ("duplicate-format-escaped", "{", "\"\\u0066ormat\"", "package-schema"),
    ("duplicate-source-authenticated", "\"source\":{", "\"authenticated\"", "source-schema"),
    ("duplicate-fingerprint-value", "\"fingerprint\":{", "\"value\"", "source-schema"),
    ("duplicate-trust-hypotheses", "\"trust\":{", "\"hypotheses\"", "trust-schema"),
    ("duplicate-kernel-nodes", "\"kernel\":{", "\"nodes\"", "kernel-schema"),
    ("duplicate-kernel-children", "\"kernel\":{", "\"children\"", "kernel-schema"),
    ("duplicate-node-left", "\"nodes\":[", "\"left\"", "node-schema"),
    ("duplicate-theorem-hypotheses", "\"theorems\":[", "\"hypotheses\"", "theorem-schema"),
    ("duplicate-theorem-conclusion", "\"theorems\":[", "\"conclusion\"", "theorem-schema"),
    ("duplicate-theorem-identity", "\"theorems\":[", "\"statement\"", "theorem-schema"),
    ("duplicate-theorem-fingerprint", "\"theorems\":[", "\"goal_fingerprint\"", "theorem-schema"),
)
for label, object_marker, key_token, reason in duplicate_key_cases:
    duplicated = duplicate_object_member(serialized, object_marker, key_token)
    result = refused(duplicated, label, "malformed", reason)
    assert result["summary"]["replayed"] == 0 and all(
        theorem["status"] != "replayed" for theorem in result["theorems"]
    ), (label, result)

# Origin records are opaque presentation metadata: replay validates only that one slot exists per
# hypothesis, then ignores the record's object members. A duplicate there cannot select a root,
# alter trust, affect a budget, or change the canonical sequent identity.
origin_duplicate = duplicate_object_member(
    serialized, "\"hypothesis_origins\":[{", "\"kind\"",
)
origin_code, origin_result = replay_text(origin_duplicate, "duplicate-ignored-origin-metadata")
assert origin_code == 0 and origin_result["status"] == "replayed", origin_result
# Boolean fields accept only JSON booleans. Similar-looking values must fail as a structured
# source-schema error before any kernel package is admitted.
for malformed_boolean in (0, 1, None, "false", [], {}):
    claim = with_theorem(base, assumption)
    claim["source"]["authenticated"] = malformed_boolean
    refused(claim, "authenticated-type-%s" % (type(malformed_boolean).__name__,),
            "malformed", "source-schema")
# Raw malformed UTF-8 anywhere in the package is rejected before JSON parsing. Exercise overlong,
# truncated, surrogate, out-of-range, stray-continuation, and invalid-lead encodings in a
# presentation string so the refusal cannot be attributed to theorem identity mismatch.
for index, invalid_utf8 in enumerate((b"\xff", b"\xc3", b"\xed\xa0\x80", b"\xf4\x90\x80\x80",
                                      b"\x80", b"\xc0\xaf")):
    claim = copy.deepcopy(assumption)
    claim["name"] = "r006-utf8-probe"
    package_bytes = json.dumps(with_theorem(base, claim), separators=(",", ":"),
                               ensure_ascii=False).encode("utf-8")
    package_bytes = package_bytes.replace(b'"r006-utf8-probe"',
                                          b'"r006-' + invalid_utf8 + b'-probe"', 1)
    refused(package_bytes, "invalid-utf8-%d" % index, "malformed", "utf8")
# The JSON parser accepts escaped UTF-16 pairs and rejects any unpaired or misordered surrogate
# as malformed JSON. Encode as ASCII so the package contains the exact JSON escape sequences.
paired = copy.deepcopy(base)
paired["source"]["path"] = "probe-\ud83d\ude00"
pair_bytes = json.dumps(paired, separators=(",", ":")).encode("ascii")
code, pair_result = replay_text(pair_bytes, "escaped-surrogate-pair")
assert code == 0 and pair_result["status"] == "replayed", pair_result
for index, malformed_surrogates in enumerate(("\ud800", "\udc00", "\ud800A", "\ud800\ud800",
                                               "\udc00\udc00", "\udc00\ud800")):
    claim = copy.deepcopy(base)
    claim["source"]["path"] = "probe-" + malformed_surrogates
    malformed_bytes = json.dumps(claim, separators=(",", ":")).encode("ascii")
    refused(malformed_bytes, "escaped-surrogate-invalid-%d" % index,
            "malformed", "json")
# The pinned Json recursive-descent parser allows 256 open arrays/objects. The package root is
# the first level; put nested arrays in the required source slot so the limit itself is exercised
# before the strict header schema refuses the otherwise parsed value.
for depth, expected_reason in ((254, "source-schema"), (255, "source-schema"), (256, "json")):
    claim = copy.deepcopy(base)
    nested = "not-a-source-record"
    for _ in range(depth):
        nested = [nested]
    claim["source"] = nested
    nested_bytes = json.dumps(claim, separators=(",", ":")).encode("ascii")
    refused(nested_bytes, "json-depth-%d" % (depth + 1,), "malformed", expected_reason)
extra = with_theorem(base, assumption)
extra["kernel"]["nodes"][0]["proof"] = True
refused(extra, "extra-node-key", "malformed", "node-schema")
extra = with_theorem(base, assumption)
extra["theorems"][0]["trusted"] = True
refused(extra, "extra-theorem-key", "malformed", "theorem-schema")
for key, value in (("hypotheses", "kernel"), ("source_correspondence", "checked"), ("fingerprints", "digest")):
    claim = with_theorem(base, assumption)
    claim["trust"][key] = value
    refused(claim, "trust-" + key, "malformed", "trust-schema")
claim = with_theorem(base, assumption)
claim["source"]["authenticated"] = True
refused(claim, "authenticated", "malformed", "source-schema")
claim = with_theorem(base, assumption)
claim["source"]["admissible"] = False
refused(claim, "inadmissible", "rejected", "source-inadmissible")
claim = with_theorem(base, assumption)
claim["source"]["admissible"] = 0
result = refused(claim, "admissible-type-integer", "malformed", "source-schema")
assert result["summary"] == {"theorems": 0, "replayed": 0, "not_replayed": 0}, result
assert result["theorems"] == [], result
claim = with_theorem(base, assumption)
claim["format"] = "elisa-proof-package-v2"
refused(claim, "format", "malformed", "format")
for bad in ("01", "-0", "+1", "", " 1", "9223372036854775808", "-9223372036854775809", "1e3"):
    claim = with_theorem(base, assumption)
    claim["kernel"]["nodes"][0]["value"] = bad
    refused(claim, "value-" + bad, "malformed", "node-schema")
claim = with_theorem(base, assumption)
claim["kernel"]["nodes"][0]["value"] = 0
refused(claim, "value-number", "malformed", "node-schema")
# A bool node's payload has two decoder boundaries: its JSON field must be the package's
# canonical decimal string, and the admitted kernel value must be exactly 0 or 1. Keep the
# malformed node reachable from a well-formed theorem so this exercises complete package replay.
for bad in (True, 1, None, [], {}):
    claim = copy.deepcopy(base)
    boolean_root = append_node(claim, "bool", value=bad)
    theorem = copy.deepcopy(assumption)
    theorem["hypotheses"] = [boolean_root]
    theorem["conclusion"] = boolean_root
    claim["theorems"] = [reseal(claim, theorem)]
    refused(claim, "bool-payload-type-%s" % (type(bad).__name__,),
            "malformed", "node-schema")
for bad in ("-1", "2", "9223372036854775807"):
    claim = copy.deepcopy(base)
    boolean_root = append_node(claim, "bool", value=bad)
    theorem = copy.deepcopy(assumption)
    theorem["hypotheses"] = [boolean_root]
    theorem["conclusion"] = boolean_root
    claim["theorems"] = [reseal(claim, theorem)]
    refused(claim, "bool-payload-range-" + bad, "malformed", "arena-inadmissible")
for bad, reason in ((1.5, "number-format"), (-1, "number-format"),
                    (2**53, "theorem-schema"), ("3", "theorem-schema"),
                    (True, "theorem-schema")):
    claim = with_theorem(base, assumption)
    claim["theorems"][0]["conclusion"] = bad
    refused(claim, "index-%r" % (bad,), "malformed", reason)
claim = with_theorem(base, assumption)
claim["theorems"][0]["hypothesis_origins"] = []
refused(claim, "origins", "malformed", "theorem-schema")
refused(with_theorem(base, assumption) | {"theorems": []}, "empty", "rejected", "no-theorems")
refused(text[:-2], "truncated", "malformed", "json")
refused("", "empty-file", "malformed", "json")

# Extreme i64 values round-trip exactly as decimal strings.
extreme = copy.deepcopy(base)
low = append_node(extreme, "int", value="-9223372036854775808")
high = append_node(extreme, "int", value="9223372036854775807")
claim = copy.deepcopy(assumption)
claim["conclusion"] = append_node(extreme, "binary", "<", low, high)
extreme["theorems"] = [reseal(extreme, claim)]
assert "(int::-9223372036854775808:" in extreme["theorems"][0]["statement"]
# The kernel may decline to compare width-ambiguous constants; the reader must still read them
# exactly, so the recomputed statement matches, and a value one off does not.
code, result = replay(extreme, "extreme-values")
assert result["reason"] in (None, "kernel-rejected"), result
extreme["kernel"]["nodes"][high]["value"] = "9223372036854775806"
refused(extreme, "extreme-value-off-by-one", "rejected", "statement-mismatch")

# Budgets are checked before the work they bound.
huge = with_theorem(base, assumption)
huge["kernel"]["nodes"] = [{}] * 1000000
exact_node_result = refused_without_theorem_publication(
    huge, "node-budget-exact-shape-shadow", "malformed", "node-schema")
# A fully valid million-node package cannot reach kernel admission because the package-wide
# copied-string limit is smaller; these deliberately malformed entries prove the count check
# admits the exact count (then refuses the node schema) rather than treating it as one-over.
huge = with_theorem(base, assumption)
huge["kernel"]["nodes"] = [{}] * 1000001
refused_without_theorem_publication(huge, "node-budget", "over-budget", "node-budget")
exact_children = with_theorem(base, assumption)
exact_child_limit = 4000000
exact_child_start = len(exact_children["kernel"]["children"])
exact_children["kernel"]["children"].extend([0] * (exact_child_limit - exact_child_start))
# The admitted arena requires the flat child vector to be covered by valid aggregate spans.
# Add a disconnected, well-formed array node over the entire exact-limit suffix instead of
# making the valid fixture fail later for unowned child entries.
exact_children["kernel"]["nodes"].append({
    "kind": "array", "operator": "", "left": 0, "right": 0, "auxiliary": 0,
    "children_start": exact_child_start, "children_count": exact_child_limit - exact_child_start,
    "value": "0", "name": "", "secondary_name": "",
})
code, exact_result = replay(exact_children, "child-budget-exact")
assert code == 0 and exact_result["status"] == "replayed", exact_result
assert exact_result["summary"]["replayed"] == len(exact_children["theorems"]), exact_result
del exact_children
huge = with_theorem(base, assumption)
huge["kernel"]["children"] = [0] * 4000001
refused_without_theorem_publication(huge, "child-budget", "over-budget", "child-budget")
many = copy.deepcopy(assumption)
many["hypotheses"] = [0] * 4097
many["hypothesis_origins"] = [{}] * 4097
refused(with_theorem(base, many), "hypothesis-budget", "over-budget", "hypothesis-budget")
flood = with_theorem(base, assumption)
flood["theorems"] = [{}] * 65537
refused_without_theorem_publication(flood, "theorem-budget", "over-budget", "theorem-budget")

# One bad theorem among good ones fails the package and is named; the rest still replay.
mixed = copy.deepcopy(packages["global_constant_module"])
bad = copy.deepcopy(mixed["theorems"][0])
bad["goal_fingerprint"] = (bad["goal_fingerprint"] + 1) % 2**32
mixed["theorems"].insert(1, bad)
result = refused(mixed, "mixed", "rejected", "fingerprint-mismatch")
assert result["summary"] == {"theorems": len(mixed["theorems"]), "replayed": len(mixed["theorems"]) - 1,
                             "not_replayed": 1}, result
assert [t["status"] for t in result["theorems"]].count("rejected") == 1, result

# Usage and unreadable input exit 2.
usage = subprocess.run([str(REPLAY)], capture_output=True, text=True, timeout=30)
assert usage.returncode == 2 and "usage" in usage.stdout, usage
missing = subprocess.run([str(REPLAY), str(WORK / "missing.json")], capture_output=True, text=True, timeout=30)
assert missing.returncode == 2 and json.loads(missing.stdout)["status"] == "unreadable", missing
