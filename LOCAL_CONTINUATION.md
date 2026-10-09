# Local continuation checkpoint

Checkpointed 2026-10-09 on the Mac so work can continue after the Vast instance is closed.

## Proof assistant checkout

The saved working changes are on branch `codex/vast-local-checkpoint-20261009`. They include the refreshed high-ROI implementation plan, the exact compiler/core pins, and the current expression-scoped `Global.Read`/`Global.Write` edits for direct global mutable accesses. The strict consumer check still reports 1,066 effectful call-site diagnostics; local grants around direct accesses do not discharge effects at callers. Treat this branch as an active checkpoint, not a qualified release.

## Native local toolchain

The standalone ARM64 Stage0/Stage1 pair, matching runtime, provenance, and check evidence are in:

`/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/local-compiler-optimization-20261009/pinned-f992-ef042-llvm21`

Source its `toolchain.env.sh` before local checks. The tuple is Elisa-compiler `f99247d7657781209678d1cc3b6c00da489f92bb`, Elisa-core `ef04267d736eae492c05a023182f6b08f74441a9`, LLVM 21.1.8, and Z3 4.16.0. Stage1 freshness passed. Elisa-compiler `main` was checked against GitHub at checkpoint time and remained at `f99247d`; check the upstream ref again before the next build and rebuild the matching pair if it moves.

The proof-source evidence is under `pinned-f992-ef042-llvm21/evidence/proof-consumer/`. Permissive semantic checking passed with zero diagnostics. Strict checking of the current grant candidate still reports 1,066 call-site grant diagnostics. Direct variable accesses are locally scoped now, but every caller must also handle the propagated effect. Continue with caller grants and rerun strict checking before attempting the CLI/API and replay gates. Do not treat permissive checking as proof of authorization enforcement.

## Vast recovery

The verified recovery is at `/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/vast-recovery-2026-10-09/`. `vast-final-recovery-20261009.tar.gz` and the handoff supplement have recorded SHA-256 values; `BACKUP-VERIFIED.json` records 78,421 files, 27 symlinks, and no mismatches. A later 1.7 GB local continuation checkpoint also has a SHA-256 sidecar. The archive covers the replacement Vast instance at `141.195.21.72:47559`.

The original instance at `38.49.42.120:53652` has separate `/root/work` data whose transfer was never confirmed. A final SSH probe on 2026-10-09 timed out during banner exchange, so that tree could not be rescanned or copied. Preserve that instance's disk if it may contain work absent from the verified archive; stopping it retains the disk, while destroying or recycling it may lose that data.
