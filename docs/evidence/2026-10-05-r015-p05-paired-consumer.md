# R-015: Pin the package restart consumer to one product generation

Commit `9d91fdeb` migrates `scripts/test_p05_package_restart.py`, which both exports a portable
package and replays it, to the `BINARY` and `REPLAY` pair selected by
`scripts/portable_replay_support.py`. The shared selector resolves the published generation once
and rejects a partial `ELISA_PROOF_BIN` / `ELISA_PROOF_REPLAY_BIN` override.

The focused regression, `scripts/tests/test_portable_replay_generation_resolution.py`, verifies one
resolver invocation for generation selection, acceptance of an explicit complete pair, refusal of a
partial override, and that this paired consumer imports both paths from the shared selector rather
than reading overrides itself.

Validation on the isolated `codex/r015-pair-consumer` branch:

```text
python3 scripts/tests/test_portable_replay_generation_resolution.py
portable replay product selection: one generation resolve; paired overrides retained
portable package restart: producer and replay are pinned through the shared resolver
```

The worktree had no published product generation or default build binaries, so the real producer /
replay restart suite was not run. Its portable-package semantics and its proof/replay outcomes are
unchanged; only paired product selection moved to the shared resolver.
