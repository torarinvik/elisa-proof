# Performance fan-out status

## Current six-Luna batch (2026-10-04)

The current baseline is `778e53d`; reviewed optimization commit `ff1768c` is on `main`.
Six GPT-6 Luna agents worked on disjoint source/checker/kernel, benchmark, and profiler lanes.
Agent reasoning runs in Codex; the Linux build and validation work runs over SSH on the
user-supplied Vast instance. No remote API credentials or local binary products were copied.

The Linux toolchain was bootstrapped with the repository pins, LLVM 20.1.2, and z3.
Both baseline and candidate main/replay products compiled successfully. Candidate checks passed:

- Linear certificate search, replay, forged-certificate, and budget controls.
- Symbolic quantifiers, including sorting/partition, adversarial, malformed, and budget cases.
- Chained pure calls and the bounded GCD producer fixture.
- Native kernel congruence, interval/arena-preservation, and quantifier-instance probes.

The patch reduces unused annotation scans, repeated index AST walks, congruence scratch arrays,
and GCD provenance scanning. The GCD shortcut still scans all signed coefficients and the
constant, preserving the existing minimum-integer edge behavior.

`scripts/perf_luna_benchmark.py` compares proof, package, and standalone replay outputs, including
exit status and stderr, before reporting bounded repeated wall-time/RSS measurements. Its
process-group timeout cleanup self-test passes with normal Python and Python optimization enabled.
The three-round Linux comparison passed on all six fixtures with byte-identical outputs, exit
codes, and stderr across baseline/candidate/rounds. Raw evidence was copied off-box to ignored
`build/luna-remote-20261004/benchmark.json`.

Observed proof-check medians (seconds):

| Workload | Baseline | Candidate |
|---|---:|---:|
| Symbolic quantifier | 1.5886 | 1.5829 |
| Rejected symbolic quantifier | 0.6139 | 0.6117 |
| Congruence | 0.0175 | 0.0170 |
| Rejected congruence | 0.0194 | 0.0175 |

These are small changes, several at millisecond scale, with only three repetitions and no
statistical confidence claim. RSS was essentially unchanged; no broad speedup is established.
The most useful result is a verified comparison baseline and removal of avoidable work. Targeted
profiling has now supplied the next batch's targets. This is not a full matrix pass.

The proof baseline limitation and resolved platform follow-up are distinct from these optimizations:

1. `test_pure_unfolding.py` fails identically in baseline and candidate: `is_space` line 29 has an
   open connective-shaped ensure, and `first_space` line 38 cannot use its unverified summary.
   Both reports have 22 obligations, 20 proved, and zero replay gaps.
   The historical congruence matrix also expects `call_congruence` to be refused, but current
   verified `pure_identity` summaries reduce its goal to the existing `a == b` premise in both
   baseline and candidate. Its certificate replays; this is summary unfolding, not admission of
   arbitrary calls as congruent formers. The new benchmark retains it as a positive control.
2. The native profiler's x86_64 Linux capture/build support is now committed as
   `elisa-profiler` commit `d2de05f`. Linux and macOS sampling, validated cache reuse/invalidation,
   target timeout, and descendant cleanup tests pass. Linux also passes progress, prebuilt reuse,
   collector identity, ABI, and timing failure/mismatch tests. File flags and monotonic clock IDs
   are target-specific; ELF entry-symbol rewriting and GNU linking replace Darwin assumptions.
   `scripts/perf_luna_profile.sh` now admits x86_64 Linux and retains the macOS path.
   Windows is explicitly deferred until a native Windows backend/test host is available.

The first full-checker instrumented O2 build exceeded the profiler's default five-minute compiler
bound before target execution. The follow-up capture explicitly raises the still-capped tool bound
to 1200 seconds, independently of the 120-second target bound, with a per-command 1800-second outer
bound. Its per-run target cache avoids compiling the same checker separately for all three workloads.
The diagnostic retention bound is explicitly 16 MiB; an optional `ELISA_PROFILE_BUILD_CACHE`
reuses a validated target cache across runs. Profiler follow-ups `07f0be0` and `0fe5acc` add bounded
tool execution, allocation/sample schema checks, bounded streaming diagnostic reads, and flushing
buffered target output before capture finalization. This retention bound does not cap target disk
writes during execution.

All three final captures are retained under ignored `build/luna-linux-20261004/`: symbolic
quantifier, congruence, and congruence refusal. Each completed three repetitions with untruncated
stdout, zero missed/dropped samples, and zero replay gaps. Independent comparisons found every
instrumented proof report byte-identical to its uninstrumented baseline (including the expected
refusal exit status). The symbolic capture has 35,064 CPU samples; certificate replay appears in
66.1% of stacks. The two smaller captures have 181 and 232 samples.

Captures are instrumented CPU stack occupancy, not instruction-pointer samples or uninstrumented
speedup evidence. Tiny helper callbacks can be disproportionately expensive under instrumentation.
Sample-mode captures omit source-definition records; name-level rankings are not unique source
attribution. `scripts/perf_luna_profile_summary.py` explicitly separates sample completeness from
proof verification and withholds ambiguous definition attribution; its ten synthetic tests pass.

The second six-Luna pass targets replay witnesses, marker decoding, quantified replay, and trace
hook linkage. Three experiments were reverted because uninstrumented comparisons did not show
repeatable gains. The bare-identifier witness scan optimization is committed as `29ffd6d`:
it avoids a redundant structural primitive-marker scan before the existing name-matching scan.
Untrusted operator checks remain first, and marker validation and recursion budgets are unchanged.
Two three-round uninstrumented comparisons preserved exact proof/package/portable-replay outputs
across six fixtures. In the second run, symbolic proof time was 1.5877 s versus 1.4865 s, export
1.6017 s versus 1.4858 s, and replay 0.5315 s versus 0.4878 s. This is workload-specific evidence,
not a system-wide speedup claim. Congruence malformed/budget, symbolic quantifier, safe constant,
dispatcher-budget, and portable replay forgery/schema/trust controls all passed.

The broader profiler regression matrix remains non-green: Linux full-mode collection growth hits
a compiler-generated suffixed trace-hook symbol. Compiler commit `43956296` reuses only the exact
canonical reserved fault-handler signature. A fresh private Linux compiler passes separate
uninstrumented, `-ftrace`, and `-ftrace-functions` link/run controls and the original collection
growth workload. Normal seed publication and the broader profiler suite are being checked next.
The macOS arena reuse workload also has a baseline exit-status mismatch under investigation.
These are not concealed by the successful sampling gates. Compiler pins remain unchanged.

The instance workspace is not a persistent volume. Keep source gains committed locally and copy
important evidence off-box before recycling/destroying it. Builds/caches are not repository gains.

## Historical snapshot (2026-10-03; not the current branch inventory)

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
