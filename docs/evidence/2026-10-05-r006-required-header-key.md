# R-006 required top-level package field

Added a paired portable replay regression in `scripts/tests/portable_replay_package_validation.py`:

- A valid one-theorem package with the complete header replays successfully.
- Removing the required top-level `trust` object returns structured `malformed/package-schema`.
- The refusal summary is exactly zero theorems, zero replayed, zero not replayed, and its theorem result array is empty.

Validation command:

```sh
ELISA_PROOF_BIN='/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/elisa-proof/build/elisa-proof-generations/5db1910c9a554e029f04d749db43cedd/elisa-proof' \
ELISA_PROOF_REPLAY_BIN='/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/elisa-proof/build/elisa-proof-generations/5db1910c9a554e029f04d749db43cedd/elisa-proof-replay' \
PYTHONPATH=scripts python3 scripts/test_portable_replay.py
```

Result: passed. The full run replayed 16 positive packages; the structure-aware corpus exercised 5 nesting depths, 8 exact-index boundaries, 5 child indexes, one unknown reachable node tag, four child ranges, two node references, two cycles, one forward reference, and an 8 MiB parser workload. The raw-byte matrix checked 512 deterministic mutations across 16 packages, with no crashes or partial theorem replay. `git diff --check` passed.

The run used matched generation `5db1910c9a554e029f04d749db43cedd`, strict Stage1 O2, target `arm64-apple-darwin27.0.0`. Replay binary SHA-256: `79259061e741e6314b0c84b86833153b82e5f758c444902c37ef2887a655d644`. Its manifest records proof HEAD `b7f5dd7483dce0b0e0774b35d390a49a19d5ba93` with `source_dirty: true`; this is a focused behavioral check against the available generation, not a clean build of this branch's exact source.

Remaining R-006 gaps include raw mutation coverage for every required field and enum/type boundary, exact and one-over checks for each independent resource maximum, and measured CPU/RSS behavior near all limits. This change covers only a missing required top-level header field.
