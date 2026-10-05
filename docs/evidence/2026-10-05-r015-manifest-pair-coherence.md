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

## Validation

The controlled closure fixture and manifest-sidecar integrity test passed. Python bytecode
compilation and `git diff --check` passed. A strict Stage1 O2 `ELISA_PROOF_PRODUCTS=all` build
used the pinned compiler product and runtime below. A subsequent build after the code commit
reported both products unchanged while updating manifest `proof.head` to that commit, confirming
metadata refresh did not compile or link either product.

| Identity | Value |
| --- | --- |
| Proof branch commit | `937ae0bb3a1dd18e97dfdf773dcdc524f459a184` |
| Proof source tree SHA-256, both manifests | `72d57a84b7c759943ea348ec1af50ccf8e678e5530c44751fa75d0778749a17f` |
| Frontend revision | `7b27fa312c5af923f044f6ee0e5e1de4f811f595` |
| Frontend tree | `ab8926f6080a13d21b06606af251e6f0027c2db5` |
| Stage1 compiler product SHA-256 | `f77278c716dea7f3dba8f4fcbcf76ecc473426ab3f163c95fea4e358f6337653` |
| Runtime object SHA-256 | `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897` |
| Target / optimization | `arm64-apple-darwin27.0.0` / `O2` |
| `build/elisa-proof` SHA-256 | `ec5f889435af32334e094f60137e919c392784d84de79957858f84a8d720b370` |
| `build/elisa-proof-replay` SHA-256 | `f8d81f4d740c50b6a94ea6e113b58c29695d45b50fae68b2429dc29ef4d5ee2a` |

Both manifests name the same proof `HEAD`, source-tree digest, frontend tree, compiler product,
runtime object, target and optimization, and each sidecar matches its manifest bytes.

## Remaining gates

R-015 remains open for pair-wide atomic publication, immutable concurrent source/product
snapshots, and detection or restart when source changes during snapshot preparation. P-03 still
needs its broader corruption and concurrent-build evidence. This fix addresses stale whole-tree
provenance on valid closure-specific cache hits only.
