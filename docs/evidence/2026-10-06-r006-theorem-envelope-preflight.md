# R-006 theorem-envelope preflight

## Finding

The portable checker admitted and validated the complete kernel arena before checking theorem
records. It then decoded each theorem's schema immediately before replaying that theorem. A package
with one or more valid, potentially expensive certificates followed by a malformed theorem record
therefore spent kernel-admission and prefix-replay work before rejecting the whole package. The
result path suppressed the prefix, so this was not an observed theorem-result leak; it was avoidable
work on attacker-controlled input and a fragile ordering boundary for future consumers.

## Change

`proof_package_preflight_theorem` now checks each theorem's exact key set, required field types,
hypothesis/origin lengths, per-theorem hypothesis cap, and hypothesis-index encodings. The checker
runs this bounded pass over the complete theorem list before decoding the kernel arena. Malformed
or over-budget theorem envelopes return an empty theorem list and zero theorem summary without
admitting the arena or replaying a valid prefix.

The preflight deliberately does not reject semantic certificate failures: root range, supported
rule, recomputed statement, fingerprint, and kernel replay checks remain in the per-theorem path.
The regression for a well-formed certificate with a forged fingerprint still reports the earlier
successful theorem and the rejected theorem, preserving the existing diagnostic contract.

## Regression and validation

The structure-aware package mutation campaign now appends either a JSON `null` theorem or a theorem
whose `hypotheses` field has the wrong type after a replayable prefix. Both must return
`malformed/theorem-schema`, no theorem rows, and an all-zero replay summary. The campaign also
checks positive replay and a well-formed-but-invalid fingerprint with its per-theorem diagnostics.

Passed:

```text
ELISA_PROOF_BIN="$PWD/build/elisa-proof-generations/36b3b18cd45b4def94e916d9d009a90b/elisa-proof" \
ELISA_PROOF_REPLAY_BIN=/tmp/elisa-proof-replay-package-preflight \
python3 scripts/tests/test_package_mutation_campaign.py
package mutation campaign: 63 adversarial inputs refused; ...
```

The replay-only product was freshly built at strict O2 with the installed matched Stage1 snapshot:

- Stage1 revision: `7b27fa312c5af923f044f6ee0e5e1de4f811f595`
- Stage1 SHA-256: `3e23836002e5b6035dba43185ea84a9ab5358707c1ee4148c4752cacb2f41a70`
- Replay product SHA-256: `ef153e0fb0a3faa021a65a8683bc6113004d857ba2433d72f0a867a91c7b22ce`
- Replay build identity: `cdb59421186b8fbe49b4785628c63b9f3da0c7aacab0dbb8eac4d773a4e3d227`
- Imported frontend revision/tree: `7b27fa312c5af923f044f6ee0e5e1de4f811f595` / `ab8926f6080a13d21b06606af251e6f0027c2db5`
- Exact build manifest: `/tmp/elisa-proof-replay-package-preflight.manifest.json`

The producer used by this focused campaign is the existing O0 proof product from pair generation
`36b3b18cd45b4def94e916d9d009a90b` (SHA-256
`f4f36d4d4ab537b9177004ac7f3bc8c63fe05082ba1d2e4ffa7993760d260f8b`). Thus the package checker
itself is fresh Stage1/O2, but this test did not use a newly rebuilt matched producer/replay pair.
The full two-product build was attempted and could not complete because unrelated current dirty
proof sources fail parsing at `src/proof/replay/source_binding_validation/immutable_bindings.elisa:320`
and then `src/proof/replay/boundary_trace_shapes.elisa:1`. The broader
`scripts/test_portable_replay.py` consequently stopped at its stale-producer `pure_unfolding`
expectation; that run is not counted as passed. No performance improvement is claimed: this adds a
bounded schema pass, with a small additional traversal on well-formed theorem lists.
