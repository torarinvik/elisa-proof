# R-006 required-object type confusion

The portable package reader was checked with a positive `verified` theorem package, then with
the required `source` record replaced by the integer `7`. The positive control replayed. The
mutated package returned structured `malformed/source-schema`, an empty theorem result list, and
the exact zero summary `{theorems: 0, replayed: 0, not_replayed: 0}`.

The regression lives in `scripts/tests/portable_replay_package_validation.py` and runs as part of
`scripts/test_portable_replay.py`.

## Matched product and source scope

Validation selected proof generation `3832e97fbe8c40fd936e53e5c81cfaf0`; both proof and replay
manifests name that generation. The proof executable SHA-256 is
`07b87539c10da71aa09920712e3dc5e33dcea3c118b3359a893c31777882d651`; replay executable SHA-256
is `d6bde829937bfc46c6b0e38132e3f50d3e056c38421c712a6f5ecb6f341df87a`. Both were built with the
strict O2 Stage1 compiler at source revision `bc8def2eadf41dd088adce22b4d3d9e74aadfee9`.
The proof source manifest identifies HEAD `ed9e0390292004c29e020d19d6453a2bb2a73bd7`, with
`source_dirty: true` and tree hash
`3daacb5e3c77eb97fa850d2917466a17ece2f94eb8936720e7e8c11009dca975`. Thus this evidence names
the exact matched artifact pair and its recorded proof source tree; it does not claim a clean-tree
build from this regression branch.

Command:

```sh
ELISA_PROOF_GENERATION_ROOT='/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/elisa-proof/build/elisa-proof-generations' python3 scripts/test_portable_replay.py
```

Result: passed; 16 positive packages replayed, the package validation matrix completed, and the
structure-aware and raw-byte R-006 mutation suites passed.

This adds one required-object boundary. Other schema fields and every documented resource maximum
are not exhaustively type-mutated by this case.
