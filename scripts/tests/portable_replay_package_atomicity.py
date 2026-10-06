"""Keep package-level rejection distinct from per-theorem replay diagnostics."""
import copy


base = packages["verified"]
theorem = copy.deepcopy(base["theorems"][0])
multiple = copy.deepcopy(base)
multiple["theorems"] = [copy.deepcopy(theorem), copy.deepcopy(theorem)]

# A complete valid package publishes both independent theorem rows.
code, result = replay(multiple, "atomicity-valid-multi-theorem")
assert code == 0 and result["status"] == "replayed", result
assert result["summary"] == {"theorems": 2, "replayed": 2, "not_replayed": 0}, result
assert [row["status"] for row in result["theorems"]] == ["replayed", "replayed"], result

# A malformed trailing theorem invalidates package admission before any kernel arena or theorem
# result is published, even when the prefix is independently valid.
malformed_tail = copy.deepcopy(multiple)
del malformed_tail["theorems"][1]["statement"]
result = refused(malformed_tail, "atomicity-malformed-tail", "malformed", "theorem-schema")
assert result["kernel"] == {"nodes": 0, "children": 0}, result
assert result["theorems"] == [], result
assert result["summary"] == {"theorems": 0, "replayed": 0, "not_replayed": 0}, result

# A well-formed but invalid certificate stays on the per-theorem diagnostic path. Its bad
# fingerprint rejects the package, while the independent valid theorem row remains explicit.
bad_certificate = copy.deepcopy(multiple)
bad_certificate["theorems"][1]["goal_fingerprint"] = (
    bad_certificate["theorems"][1]["goal_fingerprint"] + 1
) % (2**32)
result = refused(bad_certificate, "atomicity-semantic-rejection", "rejected", "fingerprint-mismatch")
assert [row["status"] for row in result["theorems"]] == ["replayed", "rejected"], result
assert result["summary"] == {"theorems": 2, "replayed": 1, "not_replayed": 1}, result
