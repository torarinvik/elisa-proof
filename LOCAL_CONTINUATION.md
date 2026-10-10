# Local continuation checkpoint — updated 2026-10-10, r18

The proof checkout, local products, compiler provenance, direct-API regression harness, and
benchmark checkpoint are saved on the Mac. Work can continue without the Vast instance.

## Proof assistant checkout

The active branch is `codex/vast-local-checkpoint-20261009`, with implementation commit
`f5e629fe` (`replay: source validate generic type-bound facts`). The branch also carries the
high-ROI implementation plan and the completed expression-scoped `Global.Read` / `Global.Write`
migration for global mutable accesses. The compiler grant migration covers 1,066 effectful call
sites across 89 source files; seven increments that read and write globals require
`Global{Read,Write}`. Qualification details and per-file hashes are in
[global-grant-scope-qualification-2026-10-09.json](docs/evidence/global-grant-scope-qualification-2026-10-09.json).

The type-bound replay change closes a P0 trust hole where a forged generic `type-bound` fact such
as `value < value` could pass shape-only validation. It reconstructs parameter widths/ranges,
scalar constants, fixed-array bounds and witnesses, scalar-local witnesses, literal counting-loop
facts, and direct call-result types from the source AST. Cast-identity facts remain rejected until
replay can authenticate an exact widening site. The focused direct-API mutation harness, Global
grant suite, qualified-constant pin suite, and pure-summary replay suite pass. Qualification is
still open: `test_global_constant_relevance.py` has a replay gap in
`module_u32_scoped_constant_branch.elisa`; `test_qualified_constants.py` has loop/rebind witness
coverage gaps; and `test_qualified_constant_call_domain.py` retains one unproven goal with zero
replay gaps. These remaining cases are documented in section 23.27.52 of `IMPLEMENTATION_PLAN.md`.

Both local products were refreshed after the implementation commit using strict O2 and the newest
pinned public Elisa compiler `8f2023ce8a7d52358b733a0e812ff46293d45f10`. Stage1 is
`/Users/torarinvikbjarko/.elisac/stage1/bin/elisac-stage1` (SHA-256
`2faf57f2dca6914d3f500c6b4532fb993349208ff556459de0a6af025688c644`), from
`../local-compiler-optimization-20261009/parser-effect-template-working`; the matching runtime
object SHA-256 is `347899678c59a997302d9b9afa57a755eaace0d60da48a9100c42a097afe9d85`.
Both manifests record `source_dirty: false` and the current implementation commit. Proof executable
SHA-256: `48299b242d079f1d41a00c449ab79323bd59605a403eae1e143eef7c3f69aaef`; manifest SHA-256:
`fa976bedc97e3bf5bfeb2fd0f5abbb8278d3b52d10a0480f83b4e13371e282e2`. Replay executable
SHA-256: `5d2495e5ef171814ccef723e6726787ab077fd92647562654455122031fb9515`; manifest SHA-256:
`a7f52517618da9c37a75bd140bae94f9dfe6d0035f14e972f915921e25c224a8`.

The compiler self-build A/B run is paused locally with no Stage1 child running. Its retained
checkpoint is `/Users/torarinvikbjarko/.codex/benchmark-results/elisa-selfcompile-ab-install-index-r1/`.
`checkpoint-after-pairs-01.json` SHA-256 is
`290337ea4db43193529154356e28020540fac460f472bfa4bb3236ff5ba7382f`; `primary-results.jsonl`
SHA-256 is `b189df7109a8a49cdd3593a452726211a645162251a0fd807fe49421f3f68f51`; `run.json` SHA-256
is `c237166e60081b36d948688a8d11ed040dbfa697eee849fb6702e9ff2364286d`. Do not resume that run
until its qualification is repaired and the compiler coordinator releases Stage1.

The implementation commit is local on the branch and was not pushed. The portable branch bundle
is refreshed from this checkpoint at
`../vast-recovery-2026-10-09/elisa-proof-local-checkpoint-20261009-r24.bundle`; a SHA-256 sidecar
is stored beside it.

## Native local toolchain

The standalone ARM64 Stage0/Stage1 pair, matching runtime, and evidence are in:

`/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/local-compiler-optimization-20261009/pinned-f992-ef042-llvm21`

Source its `toolchain.env.sh` before using that historical pinned pair. For current proof qualification, the newest public Elisa compiler is `8f2023ce8a7d52358b733a0e812ff46293d45f10`; its installed Stage1 binary is `/Users/torarinvikbjarko/.elisac/stage1/bin/elisac-stage1` with SHA-256 `2faf57f2dca6914d3f500c6b4532fb993349208ff556459de0a6af025688c644`, and the matching runtime object SHA-256 is `347899678c59a997302d9b9afa57a755eaace0d60da48a9100c42a097afe9d85`. Its source snapshot is `../local-compiler-optimization-20261009/parser-effect-template-working`. Check upstream and use a fresh Stage1 before later builds.

The direct-API source-goal binding changes in this checkpoint passed `git diff --check`, Python
bytecode compilation, and the source-length checker. Their final native Stage1 qualification is
pending: the compiler coordinator's parser A/B seed owns the shared local compiler slot.
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

The original instance at `38.49.42.120:53652` has separate `/root/work` data whose transfer was never confirmed. The latest local SSH probe was closed by the original endpoint; the replacement at `141.195.21.72:47559` refused the connection. Keep the original instance's disk intact if it may contain work absent from the verified local archives; do not destroy or recycle it until that tree is recovered or confirmed unnecessary.

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
