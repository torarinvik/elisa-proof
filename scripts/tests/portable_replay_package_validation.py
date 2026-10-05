"""Package reader, schema, decoder, resource-budget, and report-boundary probes.

Loaded by ``scripts/test_portable_replay.py`` after its single producer/export setup. The
provided namespace contains the positive packages and shared forgery/replay helpers.
"""
import copy
import json
import subprocess

from portable_replay_support import *

# Header, trust and schema: nothing is inferred, over-claimed or accepted twice.
text = json.dumps(with_theorem(base, assumption))
refused(text.replace('{"format": ', '{"format": "elisa-proof-package-v1", "format": ', 1),
        "duplicate-key", "malformed", "package-schema")
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
claim["format"] = "elisa-proof-package-v2"
refused(claim, "format", "malformed", "format")
for bad in ("01", "-0", "+1", "", " 1", "9223372036854775808", "-9223372036854775809", "1e3"):
    claim = with_theorem(base, assumption)
    claim["kernel"]["nodes"][0]["value"] = bad
    refused(claim, "value-" + bad, "malformed", "node-schema")
claim = with_theorem(base, assumption)
claim["kernel"]["nodes"][0]["value"] = 0
refused(claim, "value-number", "malformed", "node-schema")
for bad in (1.5, -1, 2**53, "3", True):
    claim = with_theorem(base, assumption)
    claim["theorems"][0]["conclusion"] = bad
    refused(claim, "index-%r" % (bad,), "malformed", "theorem-schema")
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
huge["kernel"]["nodes"] = [{}] * 1000001
refused(huge, "node-budget", "over-budget", "node-budget")
huge = with_theorem(base, assumption)
huge["kernel"]["children"] = [0] * 4000001
refused(huge, "child-budget", "over-budget", "child-budget")
many = copy.deepcopy(assumption)
many["hypotheses"] = [0] * 4097
many["hypothesis_origins"] = [{}] * 4097
refused(with_theorem(base, many), "hypothesis-budget", "over-budget", "hypothesis-budget")
flood = with_theorem(base, assumption)
flood["theorems"] = [{}] * 65537
refused(flood, "theorem-budget", "over-budget", "theorem-budget")

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
