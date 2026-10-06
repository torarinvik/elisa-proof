"""Portable source identity fields must never elevate the package's trust claims."""
import copy

from portable_replay_support import TRUST, export, fnv1a32, replay


package = export("branch_negation")
assert package["source"]["authenticated"] is False, package["source"]
fake_source = "def unrelated() -> i64: return 7\n"
replacement_identity = {
    "bytes": len(fake_source.encode("utf-8")),
    "fingerprint": {"algorithm": "fnv1a32", "value": fnv1a32(fake_source)},
}

# Replay authenticates theorem roots, not the path, byte count, or identity-hint fingerprint.
# In particular, a self-consistent replacement byte count/fingerprint must not upgrade trust.
mutations = (
    ("path", lambda source: source.update(path="/untrusted/claimed-source.elisa")),
    ("bytes-and-fingerprint", lambda source: source.update(copy.deepcopy(replacement_identity))),
    ("fingerprint", lambda source: source.update(fingerprint=copy.deepcopy(replacement_identity["fingerprint"]))),
    ("all-source-metadata", lambda source: source.update(
        path="/untrusted/claimed-source.elisa", **copy.deepcopy(replacement_identity))),
)
for name, mutate in mutations:
    claim = copy.deepcopy(package)
    mutate(claim["source"])
    code, result = replay(claim, "source-metadata-" + name)
    assert code == 0 and result["status"] == "replayed", (name, result)
    assert result["trust"] == TRUST, (name, result)
    assert result["trust"]["source_authenticated"] is False, (name, result)

print("portable source metadata: resealed identity hints do not authenticate source or elevate trust")
