# R-015 remote build publication pair

`/scripts/remote/build.sh` cross-compiles both entry points and links them on the remote Linux
host. Previously it wrote only a proof manifest and installed the two binaries under independent
legacy names. The replay product had no manifest, pair identity, or generation resolver check.

The remote publication now stages both linked binaries, writes proof and replay manifests with one
fresh `pair_generation`, writes each manifest checksum, and publishes both through
`scripts/verify_product_pair.py publish`. That publisher validates binary hashes and shared proof
provenance before atomically making the generation current. The build then refreshes legacy paths
from that generation and resolves the pair once before its proof smoke check. Linker failures now
stop the remote build instead of being masked by a warning filter pipeline.

## Focused validation

- `python3 scripts/tests/test_remote_build_pair_publication.py` passed. It checks that the remote
  build supplies both binaries and manifests to the publisher and exercises the actual publisher
  and resolver with a valid pair, confirming both resolved paths are in one generation and their
  bytes match recorded hashes.
- `bash -n scripts/remote/build.sh` passed.
- `git diff --check` passed.

The remote build itself was not run: it writes the remote checkout and generation store. The
regression does not claim cross-compilation or remote Linux linking validation. The remote build
still records the proof source snapshot from the synced remote checkout; tying that tree to the
local cross-compile snapshot remains a separate R-015 boundary.
