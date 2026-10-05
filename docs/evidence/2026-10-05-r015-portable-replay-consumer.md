# R-015 portable replay consumer migration

## Consumer changed

`scripts/portable_replay_support.py` is the shared product selection point for
`scripts/test_portable_replay.py` and its loaded adversarial cases. It previously selected
`build/elisa-proof` and `build/elisa-proof-replay` independently. It now invokes
`scripts/verify_product_pair.py resolve` once, then sets both `BINARY` and `REPLAY` from the
returned product paths. `ELISA_PROOF_GENERATION_ROOT` can select the generation store. Explicit
test/tool overrides remain supported only as a pair (`ELISA_PROOF_BIN` and
`ELISA_PROOF_REPLAY_BIN`); a one-sided override fails before either binary runs.

## Evidence

- `python3 scripts/tests/test_portable_replay_generation_resolution.py` passed. Its mocked resolver
  returned paths from one generation; the test confirmed exactly one resolver invocation, use of
  both returned paths, paired override compatibility, and rejection of a partial override.
- The full `scripts/test_portable_replay.py` passed against a validated real pair from generation
  `3832e97fbe8c40fd936e53e5c81cfaf0` in the existing proof checkout's generation store. The proof
  and replay binaries had SHA-256 values `07b87539c10da71aa09920712e3dc5e33dcea3c118b3359a893c31777882d651`
  and `d6bde829937bfc46c6b0e38132e3f50d3e056c38421c712a6f5ecb6f341df87a`, respectively. The
  portable suite replayed 16 packages and refused its semantic and package-reader attacks. This
  validates this consumer path with actual paired products; it is not a fresh Stage1 build gate.

## Remaining R-015 work

This is one paired consumer only. Other tests, CLI paths, benchmarks, build helpers, and
documentation commands still need an inventory and migration where they open proof and replay
products independently. Generation-safe reader migration is not complete. Fresh matched Stage1
build validation, process-kill/restart recovery, independent-root writer coordination, immutable
source-snapshot binding, and safe old-generation retention/cleanup also remain open.
