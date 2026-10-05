# R-015 manifest-pair coherence

## Controlled reproduction and fix

`scripts/test_build_dependency_closure.py` runs `scripts/build.sh` against a temporary proof tree
with deterministic compiler and linker stubs. The two product roots have disjoint include
closures. Editing `src/unrelated.elisa` leaves both closure identities unchanged, so the old
behavior reused both executables and left their `proof.source_tree_sha256` values at the prior
tree. The test now checks that the reuse path refreshes both proof provenance records and their
checksum sidecars while leaving both executable bytes and timestamps unchanged. It also checks
that compiler and linker invocation counts do not increase and that the next no-op preserves all
product, manifest, and sidecar bytes and timestamps.

Manifest and sidecar are written to fsynced temporary files and replaced atomically. A reader
that catches the short interval between the two replacements sees a checksum mismatch and
rejects reuse. Each product record is refreshed independently; this change does not claim a
pair-wide transactional publication guarantee.

## Same-output concurrency and failed publication

The deterministic fixture holds the first build inside both compile workers using a filesystem
gate, then starts a second `ELISA_PROOF_PRODUCTS=all` build for the same proof tree. The second
build exits 2 with `another proof build owns ...`; while the first is held, all installed binary,
manifest and sidecar bytes and timestamps remain unchanged. Releasing the gate lets the first
build finish, and both manifests and sidecars validate with a shared proof provenance record.

Failure injection then makes the replay link command exit 42 after the proof product has linked.
Before the staging change, the proof product could have been published before a later replay
failure. Commits `3df1134c` and `37c9d862` now prepare all requested binaries, manifests and
checksums before the final publication loop. The injected replay failure leaves the complete old
product state unchanged. The test does not kill the process during final renames: those renames
remain sequential and can leave a partial pair if interrupted at that exact point. No pair-wide
atomicity claim is made.

## Validation

The controlled closure fixture and manifest-sidecar integrity test passed. Python bytecode
compilation and `git diff --check` passed. A strict Stage1 O2 `ELISA_PROOF_PRODUCTS=all` build
used the pinned compiler product and runtime below. A subsequent build after the code commit
reported both products unchanged while updating manifest `proof.head` to that commit, confirming
metadata refresh did not compile or link either product.

| Identity | Value |
| --- | --- |
| Proof branch commit | `37c9d8629c8048fd5e2f5dcb9c9d2912f98fb547` |
| Proof source tree SHA-256, both manifests | `72d57a84b7c759943ea348ec1af50ccf8e678e5530c44751fa75d0778749a17f` |
| Frontend revision | `7b27fa312c5af923f044f6ee0e5e1de4f811f595` |
| Frontend tree | `ab8926f6080a13d21b06606af251e6f0027c2db5` |
| Stage1 compiler product SHA-256 | `f77278c716dea7f3dba8f4fcbcf76ecc473426ab3f163c95fea4e358f6337653` |
| Runtime object SHA-256 | `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897` |
| Target / optimization | `arm64-apple-darwin27.0.0` / `O2` |
| `build/elisa-proof` SHA-256 | `663a881b798d870743341a19dd9be78acd2a62610a31858df7f6c5ef72312571` |
| `build/elisa-proof-replay` SHA-256 | `43e84544bf6a593e567b598dac35721d9e1d300d0f0876373a6de5030e33b5b0` |

Both manifests name the same proof `HEAD`, source-tree digest, frontend tree, compiler product,
runtime object, target and optimization, and each sidecar matches its manifest bytes.

## Remaining gates

R-015 remains open for interruption-safe pair-wide publication, immutable concurrent
source/product snapshots, and detection or restart when source changes during snapshot
preparation. P-03 still needs broader corruption and concurrent-build evidence. The output-tree
lock covers concurrent writers targeting the same build directory; this does not cover separate
build roots or publication interruption.
