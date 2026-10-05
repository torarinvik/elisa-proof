# R-006 source-admissible type mutation runtime check (2026-10-05)

Ran the existing `scripts/test_portable_replay.py` suite from proof checkout commit
`3ebb360598c3299820c9386f2ceb1844bd6dc1c6`, using the two binaries from immutable published
generation `79948cae3ccc4190aeebd778041c4b0b`. Both strict O2 manifests identify source commit
`414e569369fd8a3cc8b0fc6afba03475291e23a4`, clean source tree
`558d7e9f7e09be3d3ab76bd05b78babd2b666e808223d38e4144294a26e04a9e`, frontend revision
`7b27fa312c5af923f044f6ee0e5e1de4f811f595`, and target `arm64-apple-darwin27.0.0`.

Exact pair:

- Proof binary: `build/elisa-proof-generations/79948cae3ccc4190aeebd778041c4b0b/elisa-proof`,
  SHA-256 `93015d90f2e8b0dadf7fe5fa92a0dde013b525244a50441ec827fc0d564c3365`.
- Replay binary: `build/elisa-proof-generations/79948cae3ccc4190aeebd778041c4b0b/elisa-proof-replay`,
  SHA-256 `71e313a6c87c339ee89e1d588c639edfe90e581f408c78583792ccb27e8fc4ea`.
- Pair generation: `79948cae3ccc4190aeebd778041c4b0b`.

Command (run from the isolated proof worktree at commit `3ebb360598c3299820c9386f2ceb1844bd6dc1c6`):

```sh
ELISA_PROOF_BIN='/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/elisa-proof/build/elisa-proof-generations/79948cae3ccc4190aeebd778041c4b0b/elisa-proof' \
ELISA_PROOF_REPLAY_BIN='/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/elisa-proof/build/elisa-proof-generations/79948cae3ccc4190aeebd778041c4b0b/elisa-proof-replay' \
python3 scripts/test_portable_replay.py
```

The existing package-validation case changes `source.admissible` from `true` to JSON integer
`0`. It returned exit status 1 with `status=malformed`, `reason=source-schema`, an empty
`theorems` array, and summary `{theorems: 0, replayed: 0, not_replayed: 0}`. The complete suite
also passed: 16 positive packages replayed; structure-aware mutations (including the unknown
reachable-node case) passed; and 512 deterministic raw-byte mutations plus 16 encoded positives
were checked, with two mutated byte strings still valid packages. No crash or partial theorem
replay was reported.

Limits: the direct `source.admissible` case uses the helper's 120-second subprocess timeout and
does not impose a separate CPU/RSS/output cap. The structure-aware and raw-byte fresh-process
matrices each enforce 4 seconds CPU, 5 seconds wall time, 512 MiB RSS, and 4 MiB output per
invocation. This run validates the named 414e5693 product pair only; it is not validation of
current proof HEAD `3ebb3605` or its dirty root checkout. It adds focused runtime evidence for one
Boolean-field type mutation, not exhaustive package-decoder, parser-resource, or maximum-boundary
coverage. R-006 remains open.
