# R-015 build publication SIGKILL and restart evidence

Date: 2026-10-05

The mocked build closure regression now kills the complete build process group at a
deterministic authoritative-generation boundary. The test edits only its copied
`verify_product_pair.py`: at `before-pointer-replace`, after the new immutable directory
has been renamed into place and synced, the fixture publisher writes its PID to a marker
and waits. The production publisher has no added pause or crash hook.

The test sends `SIGKILL` to the isolated build process group while it is at this barrier.
The resolver then accepts the complete old generation selected by `CURRENT`; it validates
both binaries, both manifest checksums, the binary digests, and shared generation and
provenance. The build shell's EXIT trap cannot run after SIGKILL, and the test confirms
that its lock remains with the killed shell's PID. After the shell has exited, the fixture
explicitly removes that stale lock and runs an ordinary build. The restarted build
publishes a different generation whose two products resolve and share provenance.

Command:

```sh
python3 scripts/test_build_dependency_closure.py
```

Result: passed. Output reported that SIGKILL before `CURRENT` kept the old pair resolvable
and restart published a complete pair. Existing failure-injection checks for all four
authoritative publication boundaries, six compatibility-file boundaries, link failure,
and independent compatibility roots passed in the same focused run.

Test change commit: `695f85ccefcba97feb63f8a79480e86cf2bb38a7`.

Limitations: this is deterministic process-kill coverage with mock compiler/link tools and
a fixture-only barrier. It exercises the pre-pointer-replacement boundary, which must
retain the old generation; it does not kill at every instruction or every publication
boundary, test power loss/filesystem hardware behavior, or exercise real compiler products.
No production defect was exposed, so no production fix was made. The stale lock is
explicitly cleaned up by the fixture; automatic stale-lock reclamation remains outside
this test.
