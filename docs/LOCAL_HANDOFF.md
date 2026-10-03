# Handoff: integrate the cloud performance work into the main branches

Written 2026-10-03 by the cloud integration session for a local Claude Code agent on the user's Mac.
The local worktrees are about four hours behind. Everything below is pushed to GitHub. Treat this
file as the plan: follow the order, verify every step, and stop to ask the user wherever it says to.

## Ground rules

- Soundness first. Never accept a change that makes the checker accept something it used to refuse.
  A proof that is lost but still refused is a regression, not a soundness bug, and it still blocks
  the merge.
- Never force-push and never rewrite history; merge with merge commits. Never skip or disable a test.
- Follow each repository's CLAUDE.md. For elisa-proof: every source file at most 600 lines
  (`scripts/check_source_length.py`); new checks go in the themed `scripts/test.d` or
  `scripts/dogfood.d` part.
- `codex/wasmbrowser-proof` (192 commits, different base, compiler pin c16fbf19): ask the user
  before merging it. `prover-speed` belongs to its own agent; leave it.

## State of every branch (tips at the time of writing)

| Repo | Branch | Tip | Status |
|---|---|---|---|
| elisa-proof | `main` | `7bf8c51` | equals `integrate/all` |
| elisa-proof | `integrate/all-3z3zby` | `7e0e3bf` | READY TO VALIDATE: integration fixes + replay-pipeline + producer half of kernel-terms + stage0 pin |
| elisa-proof | `perf/kernel-terms` | `03291b2` | merged into the integration branch (as 03291b2) |
| elisa-proof | `perf/replay-pipeline` | `471c882` | merged up to c73d4cf; `471c882` adds one build.sh fix (rebuild the profiler hook object when clang changes), not yet merged |
| elisa-proof | `perf/prover-search` | `9cd7aa1` | NOT YET REVIEWED; 10 prover speed commits, 24 files |
| Elisa-core | `main` | `ffbf5de` | done: the legacy `rewrite` keyword is dropped from stage0 |
| Elisa-compiler | `main` | `df344e0` | unchanged |
| Elisa-compiler | `perf/stage1-seed-memory` | `faaea6b` | 3 validated commits + 2 WIP (see below) |
| Elisa-compiler | `perf/frontend-typecheck`, `perf/codegen-backend` | not pushed when this was written | check `git ls-remote` |
| elisa-profiler | `main` | `82139c7` | unchanged |

## Step 1 — elisa-proof: validate and merge `integrate/all-3z3zby` into `main`

What it holds on top of `main` (each commit message has its validation):

- Linux toolchain support (`scripts/linux_toolchain.sh`: static LLVM 23 trees, z3 preflight,
  `ELISA_STAGE1_ROOT`); macOS is unaffected.
- `ELISA_STAGE0_REV` → Elisa-core `ffbf5de`.
- `build.sh`: the object-cache key hashes only compiler files that exist, and the manifest records
  the stage1 checkout revision.
- Kernel: `fc2e330` mirrors the producer's complementary-order refutation (fixes the
  `goal_disjunct_split_probe` replay gap). It also renames `rewrite` locals to `substitution`;
  that rename is now optional, since stage0 accepts `rewrite`.
- Stale expectations fixed: `rejected_budget.elisa`'s `too_deep_conditional` deepened to six
  levels, since five now prove and replay; the dogfood congruence set mirrors test.d
  (`indexed_element` proves by design).
- `7e0e3bf`: on GNU ld only, a dogfood link retries with aborting stubs when its only undefined
  symbols are the runtime's unreachable `elisa_native_callback_*` and `va_*` entry points. macOS
  links take the original path.
- `perf/replay-pipeline`: one build.sh call builds both products; dogfood prefetch runs in parallel
  under `ELISA_PROOF_JOBS` (opt-in; keep it opt-in, see below).
- `perf/kernel-terms` (producer side only): AST equality refutes mismatches early. The trusted-kernel
  fast path was reverted, because it cost the kernel's own static verification.

Results on Linux (LLVM 23.1.2, z3 5.1.0) before the last few merges: `scripts/test.sh` failed only
two steps, and both are fixed. A full run on the final tip did NOT complete here, because the cloud
container kept rebooting under memory pressure. So on the Mac:

1. `git fetch && git switch -c integrate-check origin/integrate/all-3z3zby`, then also merge
   `origin/perf/replay-pipeline` (for `471c882`).
2. Build with the usual Mac stage1 wrapper:
   `ELISA_COMPILER_BIN=<compiler>/scripts/elisac_stage1.sh bash scripts/build.sh`.
3. Regenerate the census baseline: `python3 scripts/refusal_census.py --retry-unreadable docs/census`.
   The checked-in baseline was recorded with compiler `d8b5d305`, not the pin `2678ff10`.
   Compare per file against the old baseline before committing. Drops seen on Linux, all explained:
   - three float fixtures are now checked and refused by `no-rule`, where the front end used to
     reject them outright;
   - `rejected_symbolic_quantifier` now forms 78 obligations (49 proven, all kernel-replayed);
   - `rejected_dispatcher_budget` drops from 55 to 53 obligations before its budget trips, and its
     test passes.

   Any other drop in a file readable in both runs is a regression to investigate. Files that time
   out at 120 s are machine-dependent, so use `--retry-unreadable`.
4. `KEEP_GOING=1 bash scripts/test.sh` and `bash scripts/dogfood.sh` must both pass. Then commit
   the census, merge into `main`, and push.

## Step 2 — elisa-proof: review and merge `perf/prover-search`

Not reviewed yet. Merge it into the step-1 result on a check branch, then rerun the full suite,
dogfood and the census diff. It touches prover tiers (`src/proof/linear/*`, `src/proof/model.elisa`
and others), including `proof_expr_equal`, which kernel-terms also changed, so expect overlap there.
Require: reports byte-identical on the examples (or each difference explained as a pure speedup
with the same verdicts), no new replay gaps, census gains only. Then merge into `main`.

## Step 3 — Elisa-compiler: integrate the perf branches

The cloud seed-memory agent refused to touch `main`, correctly, so this is yours.

- `perf/stage1-seed-memory` (`faaea6b`). Validated, safe to take:
  - `fc0330b`: RSS guards without forking, about 10% less wall time through the wrapper;
  - `c08f4c1`: the seed refuses up front without z3;
  - `faaea6b`: `tools/memprof`, an allocation-hook profiler for optimized builds.

  WIP, needs its gates first:
  - `ec39b19`: parks 256 MiB arena reserve regions. Self-compile 401.8 s → 372.8 s, peak RSS
    1825 → 1704 MB, objects byte-identical. Still to run: differential_corpus,
    adversarial_differential_smoke and self_host_gen3_smoke.
  - `66a0d52`: linux_shim support for static LLVM, Linux only.
- `perf/frontend-typecheck`, `perf/codegen-backend`: take only commits their agents mark validated.
- Gate: identical pass/fail sets versus `main` on the compiler's suites, byte-identical self-compile
  objects (or a justified codegen change), and the gen2/gen3 fixpoint. On Linux these suites were
  already red at `main` and are not regressions: arena_runtime_lifecycle, arena_cache_concurrency,
  arena_alloc_size_overflow, runtime_string_allocation (stage1 -emit exe exits 8), emit_ast_parity
  (-emit ast ignores -o), diagnostics_diff (101 mismatches), semantic_acceptance_diff (1/584).
  Check whether they're red on macOS too.
- After the compiler `main` moves: bump elisa-proof's `ELISA_COMPILER_REV`, rebuild, rerun step 1's
  checks, and regenerate the census if the counts move.

## Step 4 — update the local worktrees

elisa-engine-proof, elisa-proof-mocap, elisa-proof-speed, elisa-proof-sync, proof-testdrift and
wasmbrowser-proof are about four hours stale. In each, commit or stash local edits first
(wasmbrowser-proof has uncommitted edits, so ask the user before touching them), then merge the new
`main`. Several will conflict; resolve them by keeping both behaviours, and when one side changed
the same logic, ask.

## Open findings worth doing next

- Biggest lever: the compiler's bundled runtime object is built at `-O0`. `ctx_aos_store_record`
  and `ctx_string_views_eq` are about 35% of checker samples, and building that unit at `-O2`
  dead-strips every entry point. The fix is in the compiler: keep the runtime entry points alive,
  then optimize.
- LLVM IndVarSimplify takes 45 s on `wasm_push_mjs_seg4` at O2 in the compiler build.
- Keep `ELISA_PROOF_JOBS` opt-in. Under it, test.sh's kernel_core determinism repeat
  (test.d/03:472-473) reads one cached report twice, so it stops checking determinism. Fix that
  before making it the default.
- Stage0 without z3 on PATH reports the compiler's own contracts as unprovable instead of saying
  the solver is missing. Worth a clear diagnostic in Elisa-core.
- The frontend agent saw a stage1 segfault ("c3"); ask it or reproduce.

See also `docs/perf-fanout-status.md` for the measured gains and the full Linux toolchain recipe.
