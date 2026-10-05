# R-006 bounded raw-byte portable replay mutation

## Change and scope

Added `scripts/tests/portable_replay_raw_bytes.py` and registered it in
`scripts/test_portable_replay.py`, after the committed structure-aware JSON matrix. This is a
separate deterministic byte-level layer; it does not replace or change the 28 structured
adversarial cases. The byte inputs are compact encodings of the existing valid positive
portable theorem packages. For each of the 16 packages, the harness first runs the unmodified
encoding through the bounded standalone replay path, then exercises a reproducible budget of
32 distinct mutations.

Mutations cover leading/trailing bytes (NUL, invalid UTF-8, BOM, non-JSON token), a malformed
string escape, JSON truncations, byte deletion/insertion, single-byte replacements and high-bit
flips around package/schema keys and JSON delimiters, plus fixed-seed pseudorandom bit flips.
Three changed encodings remained valid packages and replayed fully; every other mutation
returned a structured refusal. This is deterministic boundary mutation, **not**
coverage-guided fuzzing and makes no coverage-guided exploration claim.

Every raw-byte replay child, including positive controls, receives an OS CPU limit of 4 seconds,
a 5-second polled wall limit, a 512 MiB sampled RSS ceiling, and a 4 MiB combined stdout/stderr
file-size ceiling. Results must use the expected format and trust declaration; theorem summary
counts must partition exactly, replayed counts must match the per-theorem records, and the
per-theorem result list must account for every declared theorem (no truncated result list). A
package can intentionally report a mix of individually replayed and refused theorems: the
existing package contract tests this behavior, while the package itself still exits nonzero and
is never reported as wholly replayed. On any unexpected outcome, the exact bytes are retained;
the harness tries up to 24 bounded chunk deletions and retains a minimized binary seed plus
JSON metadata if the same failure class persists.

## Reproducible validation

- Immutable proof source snapshot: `a1f5a86ab7c159a739cdbaf4271ac51fc08e8743`.
- Proof source tree SHA-256: `8892b7c71e803f8815b947614119e74256442ae7cfe0e82671c2034547003b82`.
- Compiler/frontend revision: `bc8def2eadf41dd088adce22b4d3d9e74aadfee9`.
- Stage1 provenance check: current at that exact compiler revision; compiler product SHA-256
  `96eca8200bb268ea5cc1635a66d6b0da0cd85611331319c3227362d9421c2947`.
- Frontend tree identity: `13ca668b6620f927ec06bb6f348e6b4a75c88a6a`.
- Both strict O2 products were built together in the detached proof snapshot with object-cache
  reuse disabled. Their manifests agree on proof source/tree, frontend, compiler product,
  runtime object, optimization, mode and target (`arm64-apple-darwin27.0.0`).
- Proof executable SHA-256: `f913a50fd11dd7ae1a4eb3cdade8c74477a3cf24e1979b53a703b55accb23406`.
- Replay executable SHA-256: `c1196aa0fb5cec9849755aab775ff4ca8e0e3203aac983e45f6a43b9b3b40aae`.
- Command:
  `ELISA_PROOF_BIN=<isolated>/proof/build/elisa-proof ELISA_PROOF_REPLAY_BIN=<isolated>/proof/build/elisa-proof-replay PYTHONPATH=scripts python3 scripts/test_portable_replay.py`
- Result: 16 positive packages replayed; 512 byte mutations checked; 3 changed byte streams
  remained valid and replayed; 528 bounded raw replay invocations total. Peak observed child
  wall time 0.038 seconds, CPU 0.013 seconds, and sampled RSS 3,227,648 bytes. The existing 28
  structure-aware cases also passed (peak 0.055 seconds wall, 0.047 seconds CPU, 26,509,312
  bytes sampled RSS). The complete portable replay entry point passed, including semantic and
  package-reader attacks.

## Limits

This fixed mutation budget is bounded and reproducible, but does not prove exhaustive JSON
grammar coverage, maximize valid package dimensions, provide coverage feedback, or constitute
sustained resource-pressure testing. RSS is sampled rather than enforced by a portable OS limit;
the CPU limit is OS-enforced, while wall, RSS and output limits are enforced by the supervising
test process. Seed minimization is bounded and only attempts byte-chunk deletions while
preserving the observed failure class.
