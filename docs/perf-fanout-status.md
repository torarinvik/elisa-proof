# Performance fan-out status (2026-10-03)

Six cloud agents worked on compiler and proof-assistant performance, each on its own branch, plus
one session that drops stage0's legacy `rewrite` keyword. None of this work is merged into any
`main`. This file records where each piece lives, what has been measured and what is still open,
so a later session can pick it up.

## Branches

| Repo | Branch | Lane | State at last check |
|---|---|---|---|
| elisa-proof | `integrate/all-3z3zby` | integration of `integrate/all` plus fixes | see "Integration branch" below |
| elisa-proof | `perf/kernel-terms` | trusted kernel term equality | `57a3b98`, pushed |
| elisa-proof | `perf/replay-pipeline` | replay checker, build, test and dogfood drivers | `c73d4cf`, pushed, finished |
| elisa-proof | `perf/prover-search` | prover search, goal tiers | nothing pushed at last check |
| Elisa-compiler | `perf/stage1-seed-memory` | seed time, peak RSS | `faaea6b`, pushed |
| Elisa-compiler | `perf/frontend-typecheck` | parse, resolve, typecheck | nothing pushed at last check |
| Elisa-compiler | `perf/codegen-backend` | lowering, LLVM passes, runtime | nothing pushed at last check (its checkout was on `main`) |
| Elisa-core | `stage0/drop-legacy-rewrite` | drop the `rewrite` keyword from stage0 | `ffbf5de`, pushed, final report pending |

`main` was unchanged in all four repositories at the last check. elisa-proof `main` equals
`integrate/all` (`7bf8c51`).

## Integration branch (`integrate/all-3z3zby`)

On top of `integrate/all` (`7bf8c51`), each commit validated as described in its message:

- `08847ab` linux_toolchain.sh links a static LLVM tree (LLVM 23.1.2 release) and retries stage0
  with `-permissive`; exports PATH so build.sh's `clang` matches.
- `2cb5f00` `ELISA_STAGE0_REV` → Elisa-core `a58c4f96`, because the old pin cannot parse compiler
  `2678ff10` (`@append_only`).
- `55255e6` build.sh object-cache key no longer fails silently for a bare stage1 binary.
- `081c8b7` `rejected_budget.elisa` `too_deep_conditional` deepened from five levels to six. Five
  now prove and replay; six still time out.
- `058050c` linux_toolchain.sh requires z3. Without it, stage0 reports the compiler's own contracts
  as unprovable instead of saying the solver is missing.
- `6c69249` dogfood congruence refused-set matches test.d (`indexed_element` proves by design).
- `750b60a` build.sh takes `ELISA_STAGE1_ROOT`, so the manifest records the compiler revision and
  the refusal census runs.
- `fc2e330` kernel mirror of the producer's complementary-order refutation (fixes the
  `goal_disjunct_split_probe` replay gap), and `rewrite` locals renamed `substitution` so dogfood's
  stage0 bootstrap compiles.

Results on Linux with LLVM 23.1.2 and z3 5.1.0, before `fc2e330`: `scripts/test.sh` failed exactly
two steps, the disjunct-split replay gap and the census provenance, and both are now fixed. With
`fc2e330` applied, the full `KEEP_GOING=1` run was clean through the optimized replay checks when
work stopped; it did not finish.

Open before merging into `main`:

1. Finish a full `KEEP_GOING=1 bash scripts/test.sh` and `bash scripts/dogfood.sh` on this branch.
2. Regenerate the refusal census baseline (`docs/census/`). It was recorded with compiler
   `d8b5d305`, not the pin `2678ff10`. `census_diff` flags five `rejected_*` fixtures; all still fail
   with zero replay gaps:
   - three float fixtures are now checked and refused by `no-rule`, where the front end used to
     reject them outright;
   - `rejected_symbolic_quantifier` now forms 78 obligations (49 proven, all kernel-replayed);
   - `rejected_dispatcher_budget` drops from 55 to 53 obligations before its budget trips, and its
     own test passes.
3. Merge into `main` (no force-push).

## Measured gains (not merged yet)

- perf/replay-pipeline (LLVM 20, z3 5.1.0, 4 vCPU, identical outputs): dogfood up to the stage0
  bootstrap 194 s → 95 s with `ELISA_PROOF_JOBS=4`; cold build of both products 255 s → ~238 s;
  test.sh unchanged (394 s → 400 s). Replay checker: ~90% of time is kernel replay, so no
  checker-side change is worth the trusted-base risk.
- perf/kernel-terms (LLVM 20): `kernel_replay_standalone` 35.4 s → 25.8 s user (-27%), with
  reports, including replay status, byte-identical on 161 examples.
- perf/stage1-seed-memory (LLVM 20, z3 5.1.0, byte-identical objects): compiler self-compile
  401.8 s → 372.8 s, peak RSS 1825 → 1704 MB, sys time 9.9 s → 1.4 s; through the wrapper about 10%
  less wall time and about 90% fewer page faults.

## Findings to follow up

- The bundled runtime object is built at `-O0`; `ctx_aos_store_record` and `ctx_string_views_eq` are
  about 35% of checker samples. Building it at `-O2` dead-strips every entry point, so it needs a
  compiler fix (keep the entry points alive). Probably the largest single win; owned by the codegen
  lane.
- LLVM IndVarSimplify takes 45 s on one function (`wasm_push_mjs_seg4`) at O2 in the compiler build.
- Several Elisa-compiler suites are already red on Linux at `main`: `stage1 -emit exe` exits 8,
  `-emit ast` ignores `-o`.
- The frontend agent was investigating a stage1 segfault (`c3`); details pending.
- Elisa-compiler's own seed, build_drivers.sh and self_host_gen2.sh links are macOS-only.
  `tools/linux_shim/clang` covers a shared LLVM; static LLVM support was WIP on
  perf/stage1-seed-memory.
- After `stage0/drop-legacy-rewrite` lands, re-pin `ELISA_STAGE0_REV` once it bootstraps `2678ff10`
  strictly.

## Linux toolchain recipe

```sh
pip install z3-solver                          # z3 5.1.0 on PATH; required
curl -sSL -o /opt/llvm23.tar.xz https://github.com/llvm/llvm-project/releases/download/llvmorg-23.1.2/LLVM-23.1.2-Linux-X64.tar.xz
mkdir -p /opt/llvm-23 && tar -xJf /opt/llvm23.tar.xz -C /opt/llvm-23 --strip-components=1
apt-get install -y libzstd-dev zlib1g-dev libxml2-dev
ELISA_LLVM_DIR=/opt/llvm-23 ELISA_CORE_REPO=<Elisa-core> ELISA_COMPILER_REPO=<Elisa-compiler> \
    bash scripts/linux_toolchain.sh > ~/tc.env && eval "$(cat ~/tc.env)"
bash scripts/build.sh && KEEP_GOING=1 bash scripts/test.sh
```
