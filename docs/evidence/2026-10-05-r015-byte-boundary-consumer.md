# R-015 portable byte-boundary consumer migration

## Consumer changed

`scripts/tests/test_portable_package_byte_boundaries.py` now imports the proof and replay paths
from `portable_replay_support`. This pins both executables to one resolved product generation
while keeping the test's manifest sidecar, binary hash, schema, source-tree, compiler, and
stage assertions intact.

## Evidence

- Ran `scripts/tests/test_portable_package_byte_boundaries.py` with
  `ELISA_PROOF_GENERATION_ROOT` set to the shared proof checkout's generation store.
- Resolver selected generation `3832e97fbe8c40fd936e53e5c81cfaf0`:
  - `elisa-proof`: SHA-256 `07b87539c10da71aa09920712e3dc5e33dcea3c118b3359a893c31777882d651`
  - `elisa-proof-replay`: SHA-256 `d6bde829937bfc46c6b0e38132e3f50d3e056c38421c712a6f5ecb6f341df87a`
- Result: passed; 6 truncated UTF-8 prefixes, 6 invalid continuation positions, 7 other malformed
  UTF-8 encodings, embedded NUL rejection, 65,536 copied string bytes accepted, and 65,537
  refused.

## Remaining scope

This migrates only the byte-boundary consumer. It does not validate a fresh Stage1 build or
migrate other consumers that independently select proof and replay products.
