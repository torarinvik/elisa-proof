# Local continuation checkpoint — updated 2026-10-09, r14

Checkpointed on 2026-10-09 so work can continue on the Mac without the Vast instance.

## Proof assistant checkout

The active branch is `codex/vast-local-checkpoint-20261009`. It contains the refreshed high-ROI implementation plan, exact Elisa compiler/core pins, and the completed expression-scoped `Global.Read` / `Global.Write` migration for global mutable accesses. The direct-API source-goal binding candidate and its regression updates are now committed as a local checkpoint; they have passed static checks but still need the held Stage1 runtime qualification described below. The matching portable branch bundle is `../vast-recovery-2026-10-09/elisa-proof-local-checkpoint-20261009-r14.bundle`; its verified checksum is recorded in the recovery continuation file.

The migration covers 1,066 effectful call sites across 89 source files. Seven counter increments that both read and write globals now require `Global{Read,Write}`. The native Stage1 compiler strict check of the final candidate passed with exit code 0 and zero diagnostics. Qualification details and per-file SHA-256 values are in [global-grant-scope-qualification-2026-10-09.json](docs/evidence/global-grant-scope-qualification-2026-10-09.json).

The check used the exact command `$ELISA_COMPILER_BIN -emit check -O0 src/main.elisa` from the proof project root. The proof source is saved in this branch; the candidate snapshot and raw check log remain under `../local-compiler-optimization-20261009/pinned-f992-ef042-llvm21/evidence/proof-consumer/`.

The full proof regression matrix, CLI/API checks, and replay gates still need to be run against this migration before treating it as release-qualified.

## Native local toolchain

The standalone ARM64 Stage0/Stage1 pair, matching runtime, and evidence are in:

`/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/local-compiler-optimization-20261009/pinned-f992-ef042-llvm21`

Source its `toolchain.env.sh` before using that historical pinned pair. For current proof qualification, the newest public Elisa compiler is `8f2023ce8a7d52358b733a0e812ff46293d45f10`; its installed Stage1 binary is `/Users/torarinvikbjarko/.elisac/stage1/bin/elisac-stage1` with SHA-256 `2faf57f2dca6914d3f500c6b4532fb993349208ff556459de0a6af025688c644`, and the matching runtime object SHA-256 is `347899678c59a997302d9b9afa57a755eaace0d60da48a9100c42a097afe9d85`. Its source snapshot is `../local-compiler-optimization-20261009/parser-effect-template-working`. Check upstream and use a fresh Stage1 before later builds.

The direct-API source-goal binding changes in this checkpoint passed `git diff --check`, Python
bytecode compilation, and the source-length checker. Their final native Stage1 qualification is
pending: the compiler authority-candidate benchmark still owns the shared local compiler slot.
The next Global grant coverage increment is also prepared but unqualified: fixed-array indexed
reads/writes, a mutable-global index expression, and mutable-reference acquisition have positive
and exact missing-axis controls for CLI JSON and all direct API routes. The dynamic global-index
positive checks semantic acceptance separately from proof completion. Do not count these as
passing until the Stage1 runs complete.
The proof harness to resume is:

```sh
ELISA_COMPILER_ROOT="/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/local-compiler-optimization-20261009/parser-effect-template-working" python3 scripts/test_direct_api_semantic_admission.py
```

Then rerun the report-inventory runtime controls and fresh-product replay gates before calling the
direct-API source-binding P0 complete. Do not launch overlapping compiler jobs while the authority
profile is active; compiler coordination is in Codex thread `01a121db-9e44-7451-9e08-a8bbd6a1e8e4`.

## Vast recovery

The verified recovery folder is `/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/vast-recovery-2026-10-09/`. `BACKUP-VERIFIED.json` records 78,421 files, 27 symlinks, and zero mismatches. The full recovery archive and handoff supplement have recorded SHA-256 values. The 1.7 GB local continuation checkpoint is also hash-verified. These archives cover the replacement Vast instance at `141.195.21.72:47559`.

The original instance at `38.49.42.120:53652` has separate `/root/work` data whose transfer was never confirmed. The latest local SSH probes reset on the original endpoint and were refused by the replacement. Keep the original instance's disk intact if it may contain work absent from the verified local archives; do not destroy or recycle it until that tree is recovered or confirmed unnecessary.

The 20:32 full local continuation archive covers the compiler and associated-type snapshots captured then. A newer uncommitted parser candidate in `../local-compiler-optimization-20261009/parser-effect-template-working` was created afterward and is captured separately in [PARSER-TEMPLATE-LOCAL-CHECKPOINT.json](../vast-recovery-2026-10-09/PARSER-TEMPLATE-LOCAL-CHECKPOINT.json) and `../vast-recovery-2026-10-09/parser-template-local-checkpoint-20261009.tar.gz`. That supplement includes the candidate source, fixtures, evidence, Stage1 product, and matching runtime.

The parser candidate's focused fixture semantic check and native-r4 compile/check/run pass; its product seed build also passes. The earlier native-r3 run crashed and remains recorded. A separate check of parser source modules reports undefined `Expr`/`Decl`/`Stmt` names, so these records do not establish a full compiler-source gate. The A/B performance comparison is incomplete, and this experiment is not integrated into the proof branch.

The separate compiler-wrapper decomposition evidence is saved at
`../local-compiler-optimization-20261009/compiler-compare-20261009/results/wrapper-decomposition-20261009/`.
All 50 samples, output hashes, and provenance checks passed; wrapper overhead was 131–140 ms on
the two small measured inputs. This is wrapper-only evidence and must not be presented as an
Elisa proof/compiler-wide speedup. A separate authority-profile run remains in progress.

## Local recovery boundary

The current work used by this local session is present on the Mac; it no longer depends on a live
Vast instance. The replacement-instance recovery archive remains verified at 78,421 files and 27
symlinks with zero mismatches, and the parser candidate has its own checksum-verified supplement.
The original instance's separate `/root/work` tree was never confirmed as part of that transfer;
files unique to it remain outside the verified recovery boundary.
