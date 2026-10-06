# Q0.11 qualified-constant runtime-crash triage — 2026-10-06

## Result

The exact minimized qualified-constant input does **not** crash on a newly built, pair-verified
Stage1 O2 proof/replay generation. It exits 0 and reports one obligation proved, one certificate
replayed, and zero replay gaps. This distinguishes current behavior from the retained historical
binary that crashed, but does not identify the historical cause or prove that it is fixed on every
supported target. No source or compiler change is justified by this run.

The broader `scripts/test_qualified_constants.py` command does not pass in this checkout: it stops
on `qualified_constants_body.elisa`, whose current report is `proved_with_replay_gaps` (4
obligations, 3 certificates replayed, 1 gap). The exact crash regression was below that failure and
therefore never ran in the suite. This milestone moves it before the broader body control. The
rerun now reaches and passes the exact crash regression, then stops at the unrelated body replay-gap
assertion (line 40 after the move). That replay gap remains open.

## Fresh product identity

Build command, from this isolated proof worktree:

```sh
ELISA_COMPILER_SRC='/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/Elisa-compiler' \
  ELISA_PROOF_PRODUCTS=all scripts/build.sh
```

The build completed and published pair generation
`16b967120e5e46498ce5dbfa7ff4709f`. Both `verify_product_pair.py resolve` and
`verify_product_pair.py check-current` succeeded. The proof and replay binaries are the immutable
generation paths returned by `resolve`:

| Identity | Value |
|---|---|
| Proof binary SHA-256 | `eaca33ccba581e56e9120efaa8a570090e8e22aa24cfecd157124269f87e8106` |
| Replay binary SHA-256 | `dcba595db16625f282a35555d7000b5092f78eeb54e8058854b87eb9dce3dec9` |
| Frontend revision / tree | `6b475d894331f0a81c3112167ef7fcf5c642a424` / `401bd5368e7909168e9500c872ab122ae421750c` |
| Stage1 product SHA-256 | `33bb73e7dbcd0a0cc718541fee6ecc7d4b7988f8cf37fe150d7d64409c4702a9` |
| Stage1 source revision | `6b475d894331f0a81c3112167ef7fcf5c642a424` |
| Stage1 source-tree SHA-256 | `e80ef8d3eab73643b80c995320b013ad936ef7e4a27f547ffc6a29643a1dc599` |
| Runtime SHA-256 | `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897` |
| Profile-hook SHA-256 | `ff7eb87b67bbc470ee95c320bb95ff125300f1edc8c2e67585d282e27e0e9711` |
| Target / mode | `arm64-apple-darwin27.0.0`, strict O2 |

The compiler checkout is marked `source_dirty: true` in both pair manifests because it contains
unrelated local changes. Its Stage1 provenance guard nevertheless passed immediately before and
during the build (`stage1 provenance: current`, source revision above); that guard verifies the
actual Stage1 product hash against its recorded source-tree and build-recipe hashes. The pair is
therefore fresh and internally identified, but this is local experimental evidence, not a clean-tree
release build.

## Reproducer and controls

The minimized source is
[`examples/qualified_constant_return_crash_repro.elisa`](../../examples/qualified_constant_return_crash_repro.elisa),
SHA-256 `3cf171b77ae3bd4d847a3f6c6fd1bb10f40978b189e121e1a1951f086fd94ea2` (51 bytes in this
checkout). It was invoked directly with the generation's proof binary and `--json`; result:

- process exit: `0` (no signal, timeout, or stderr)
- status: `proved`
- obligations / proven: `1 / 1`
- certificates / replayed / gaps: `1 / 1 / 0`

The enclosing qualified-constant suite's initial positive and negative controls passed; after the
test reorder, the suite also executed this exact regression and passed it before stopping at the
body replay gap. A separate direct invocation confirmed the same result. The updated
`scripts/test_qualified_constants.py` has SHA-256
`1c198bafb34214e9582166d3797e3982b19f577e5fd0b4e19dd7362c6f315b1c`.

The retained historical crash report identifies a different product hash,
`74f49810b8988d2e53f38d6298a0e29536299c579363209d464ad2a7b789658a`, built from a dirty proof
tree and dirty Stage1 checkout; the originally measured product `d734fd75…` remains unavailable.
The retained LLDB trace's invalid rewritten-array index is symptom evidence only. Neither historical
executable nor its exact dirty source state was available for a current-session differential run.

## Debugger and conclusion

No current runtime failure reproduced, so there was no live crash to inspect. The sibling
`elisa-debugger` project is available, but its support matrix explicitly says native postmortem/core
inspection is not implemented; it would not provide a better crash trace than LLDB for a reproduced
native fault. No debugger was invoked and no cause is claimed. If the historical executable or a
reproducible current crash becomes available, preserve it and obtain a faulting stack before editing.

Commands used for provenance and behavior included `ELISA_PROOF_PRODUCTS=all scripts/build.sh`,
`python3 scripts/verify_product_pair.py resolve --generation-root build/elisa-proof-generations`,
`python3 scripts/verify_product_pair.py check-current ...`, a direct `--json` invocation of the
minimized input, and `ELISA_PROOF_BIN=<immutable-generation-proof-binary> python3
scripts/test_qualified_constants.py`. The test script's replay-gap failure is recorded above; it
must not be represented as a clean pass. The crash regression now runs before that unrelated gate.
