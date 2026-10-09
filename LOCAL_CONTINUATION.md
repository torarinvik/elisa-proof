# Local continuation checkpoint

Checkpointed on 2026-10-09 so work can continue on the Mac without the Vast instance.

## Proof assistant checkout

The active branch is `codex/vast-local-checkpoint-20261009`. It contains the refreshed high-ROI implementation plan, exact Elisa compiler/core pins, and the completed expression-scoped `Global.Read` / `Global.Write` migration for global mutable accesses.

The migration covers 1,066 effectful call sites across 89 source files. Seven counter increments that both read and write globals now require `Global{Read,Write}`. The native Stage1 compiler strict check of the final candidate passed with exit code 0 and zero diagnostics. Qualification details and per-file SHA-256 values are in [global-grant-scope-qualification-2026-10-09.json](docs/evidence/global-grant-scope-qualification-2026-10-09.json).

The check used the exact command `$ELISA_COMPILER_BIN -emit check -O0 src/main.elisa` from the proof project root. The proof source is saved in this branch; the candidate snapshot and raw check log remain under `../local-compiler-optimization-20261009/pinned-f992-ef042-llvm21/evidence/proof-consumer/`.

The full proof regression matrix, CLI/API checks, and replay gates still need to be run against this migration before treating it as release-qualified.

## Native local toolchain

The standalone ARM64 Stage0/Stage1 pair, matching runtime, and evidence are in:

`/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/local-compiler-optimization-20261009/pinned-f992-ef042-llvm21`

Source its `toolchain.env.sh` before local checks. The tuple is Elisa-compiler `f99247d7657781209678d1cc3b6c00da489f92bb`, Elisa-core `ef04267d736eae492c05a023182f6b08f74441a9`, LLVM 21.1.8, and Z3 4.16.0. Stage1 freshness passed. Elisa-compiler `main` was checked against GitHub at checkpoint time and remained at `f99247d`; check upstream again before a later build and rebuild the matching pair if it moves.

## Vast recovery

The verified recovery folder is `/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/vast-recovery-2026-10-09/`. `BACKUP-VERIFIED.json` records 78,421 files, 27 symlinks, and zero mismatches. The full recovery archive and handoff supplement have recorded SHA-256 values. The 1.7 GB local continuation checkpoint is also hash-verified. These archives cover the replacement Vast instance at `141.195.21.72:47559`.

The original instance at `38.49.42.120:53652` has separate `/root/work` data whose transfer was never confirmed. The latest local SSH probes reset on the original endpoint and were refused by the replacement. Keep the original instance's disk intact if it may contain work absent from the verified local archives; do not destroy or recycle it until that tree is recovered or confirmed unnecessary.

The local compiler and associated-type working trees, including their in-progress changes, are also present in the verified local continuation archive. They remain available under the sibling `Elisa-compiler`, `associated-indexed-local`, and `local-compiler-optimization-20261009` directories.
