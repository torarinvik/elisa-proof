# R-015 independent-root concurrent build control

## Scope

`scripts/test_build_independent_roots.py` launches the production build
orchestrator from two temporary proof roots at the same time. Each root has a
separate committed compiler-source fixture. Mock compiler and linker programs
produce deterministic files; a fixture-only gate in each copied manifest tool
pauses both builds after their first staged manifest is written.

While both builds are paused, the test checks that each owns its own build lock,
that lock PIDs match the two build processes, and that object, linked-binary,
and manifest staging paths are disjoint. The staged manifests identify
different proof source trees, frontend revisions, and pair generations. After
release, each root's generation resolver accepts a complete proof/replay pair
whose manifests share that root's source identity and generation.

This is a mocked orchestration boundary only. It verifies the current scripts'
root-local coordination and publication paths for the exercised concurrent
builds. It does not compile Elisa code with a real compiler, measure build
performance, test source mutation during snapshot preparation, inject process
failure or cancellation, or establish coordination across machines/filesystems.
No production race was exposed, so no build behavior was changed.

## Exact identities

- Proof repository base: `4f2b0d9813c312cff44ac0513a3b00b89610b7f4`.
- Test: `scripts/test_build_independent_roots.py`.
- Build scripts exercised from isolated temporary fixture copies:
  `build.sh`, `compiler_snapshot.sh`, `build_manifest.py`, and
  `verify_product_pair.py`.

## Command and result

```sh
python3 scripts/test_build_independent_roots.py
python3 -m py_compile scripts/test_build_independent_roots.py
git diff --check
```

The concurrent mocked builds both reached the manifest barrier, used disjoint
locks and staged paths, published different pair generations, and resolved
successfully from their own generation roots. The test did not invoke any
compiler checkout or modify compiler sources.
