# R-015 source mutation during snapshot preparation control

## Scope

`scripts/test_build_source_snapshot_race.py` exercises the build orchestrator
with a temporary proof root, a pinned temporary compiler-source fixture, and
mock compiler/linker programs. A fixture-only barrier pauses the copied
`compiler_snapshot.sh` after it has copied the proof `src/` tree but before it
finishes copying `examples/` and returns to `build.sh`.

At the barrier, the test records the digest and sentinel bytes in the copied
`src/` snapshot. It then edits an already-copied live source and adds a new live
source file before allowing preparation and compilation to continue. The mock
compiler records the exact `src/` digest and sentinel it reads from its input
snapshot. Both generated binaries retain those records, and both generation
manifests name the same captured digest while marking the live proof source as
dirty. The resolver accepts the complete pair.

This demonstrates that a mutation after the source subtree copy, while overall
snapshot preparation is still paused, does not make the published manifests
claim the subsequently edited live bytes. It is a mocked build boundary. It
does not interrupt a file while `rsync` is actively reading it, use a real Elisa
compiler, establish compiler semantics, or test source changes concurrent with
the source-tree copy itself. The synthetic compiler's embedded digest is a
test witness for the bytes it reads from the snapshot.

## Exact identities

- Proof repository base: `1ae3717566a40a5c34d371cdad903c1e956787c0`.
- Test: `scripts/test_build_source_snapshot_race.py`.
- Build scripts exercised from temporary fixture copies: `build.sh`,
  `compiler_snapshot.sh`, `build_manifest.py`, and `verify_product_pair.py`.

## Commands and results

```sh
python3 scripts/test_build_source_snapshot_race.py
python3 -m py_compile scripts/test_build_source_snapshot_race.py
git diff --check
```

The test passed. The two generated products' embedded snapshot digests matched
their generation manifests and the digest captured at the barrier; the post-edit
live source digest differed. No compiler checkout or compiler source file was
used or changed.
