# Proof queue evidence — 2026-10-05

This note consolidates the current bounded evidence for P-00–P-07. Raw captures live under
task-local `/private/tmp` paths and are not release artifacts. All measurements below are from
arm64 macOS unless stated otherwise. The evidence does not establish Linux qualification or a
general speed advantage.

## Product identity

The P-01/P-03 product was built from proof source digest
`1cf9eb5e5354558f5e6cf10a66c096a63a8535967f84d7c2322faaf8a7f9aa36`, frontend pin
`4c479ad1981403c9f77f04a9ee5918f74713533e` (tree
`545f10f3d5c1118cc9a4765e46543fe9f874cb02`), Stage1 compiler source revision
`60c906665c7c48c10daca5d889f6e351796d4e51` (product SHA-256
`79ef1bc37a4595e815ec9351cf911f0c73c35b9700ca96923b1df181bc1e92d8`), and runtime object SHA-256
`b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`. Configuration was strict
O2 for `arm64-apple-darwin27.0.0`.

| Product | SHA-256 |
| --- | --- |
| Proof CLI | `cfec8d7225fa6a6161e761c6cd6c2f70867ee2a1c005097f9373e9e1e45b5d04` |
| Replay CLI | `896ca03a4dbd399238eb852308522669d6a72bd1dcda5766bd4a9802bf902ffb` |
| Main manifest | `b485ff436185c8d1792d541615af883a31a1d6b19412fa075a2a52691c28ad04` |
| Replay manifest | `65f548ae8f272de139159cd1f5c95649bda591de3178096bc100871ead45a0e8` |

These identities name the product measured below; later source edits require a fresh build and
matching source digest before the measurements can describe the candidate.

## P-00 crash and replay follow-up

Fresh O2 runs no longer reproduce the historical SIGSEGV for `kernel_comparison_runtime.elisa`
or mocap `track.elisa`. This does not identify or fix the earlier invalid write. The separate
bounded P-07 run for `kernel_comparison_runtime.elisa` completed with 3,800 obligations, 2,544
proven, and 2,544/2,544 certificates replayed with zero gaps. It took 11.649 seconds and peaked at
1,758,848 KiB under a 3,000,000 KiB cap. The raw report is
`/private/tmp/elisa-p07-kernel-comparison-current-20261005.json`.

The prior six-input census used proof source `1cf9…` and frontend pin `4c479…`. It was incomplete
in three places: `field_equality_runtime.elisa` timed out at 60 seconds (about 1.13 GiB sampled
RSS); `track.elisa` reported 943 obligations and 926 proven, with 926/928 certificates replayed
and two gaps; and the initial 1.5 GiB run of `kernel_comparison_runtime.elisa` stopped at its
memory cap before a separate larger bounded run completed. The historical census is
`/private/tmp/elisa-p07-support-final-20261005.json`.

The earlier crash cause, a minimal source/compiler regression, O0 behavior, and Linux behavior
remain open. The two current track replay gaps are in included `Slide.inner` (`slide.elisa:125`)
and arise from the conditional return `1 if at >= 1 and at + 1 < count else 0` under edge
postconditions. No crash disappearance is being counted as a correctness fix. The three-line
conditional-return case separately reproduces one gap: `inner(at:i64)` has
`ensure result == 0 or at >= 1` and returns `1 if at >= 1 else 0`. Both contain no qualified
constant or body rewrite, so these replay defects are independent of the historical crash. The
regressions are `test/repro/minimal_conditional_ensure_replay_gap.elisa` and
`test/repro/minimal_slide_inner_replay_gap.elisa`, checked by
`scripts/test_conditional_ensure_replay_gap.py`. The focused test passed against the coherent O2
binary and accepts only full replay or explicit refusal. The responsible replay rule remains to be
identified.

A fresh strict O2 build with object caching disabled was produced at
`/private/tmp/elisa-p07-fresh-20261005/elisa-proof`. Its manifest binds proof source digest
`1f273bf1ec466404c40a5d3f86f0654a6c42df0679541f0f1b1fd06366411ee9`, frontend/Stage1 revision
`7b27fa312c5af923f044f6ee0e5e1de4f811f595`, and target `arm64-apple-darwin27.0.0`; the binary SHA-256
is `549ae6fbae4e9a4d09373a537eec6c13f3701747d8a8d95ed8bce11d308e6d36`, and manifest SHA-256 is
`2fc62f277729d7b23b344a8cd4091bf62c03b143edbe734c172861257ca412bd`. The focused regression script
passed on this fresh binary: the three-line conditional case remained one explicit gap, the
`Slide.inner` slice remained two gaps, and the wrong-guard control stayed unproved with zero replay
gaps. This confirms the outcome from a no-cache build of the recorded source tree; it does not
identify the kernel branch-check failure.

The retained audit warm binary at `build/audit-20261005/elisa-proof-warm` has SHA-256
`74f49810b8988d2e53f38d6298a0e29536299c579363209d464ad2a7b789658a`; its adjacent manifest binds
the dirty proof source tree digest `d3e5d883b6b6fd75a9ac4adcf815022f27de0181d2476660eea74efd2e5109b2`,
frontend/Stage1 revision `4c479ad1981403c9f77f04a9ee5918f74713533e`, strict O2, and the current
arm64 macOS target. Bounded child runs on both `examples/kernel_comparison_runtime.elisa` and
`mocap-cleaner/src/tools/track.elisa` exited `-11` with zero stdout/stderr bytes. The proof fixture
is byte-identical to its blob at audit HEAD `13d686b2`; the track file is clean in its repository
and last changed at `133622721` on 2026-10-03, though its capture-time digest was not saved. The
audit assessment instead records binary SHA-256 `d734fd75…`, leaving the identity of that original
captured executable unresolved. The measurement record at `/private/tmp/elisa-proof-p01-baseline.json`
names its path as `build/elisa-proof`; that path now holds SHA-256
`18f2d6dbef5580d31e310e4e00c61d3f2de658eaf3ade61a1b3b64f8f43c2d09` and is 16 bytes larger than
the recorded 5,429,696-byte product. An inventory of retained project and temporary candidates
found no file matching `d734fd75…`. The 74f binary reproduction therefore establishes that this
retained manifest-bound binary crashes, but does not reproduce the exact measured executable or
establish the cause.

The current strict O0 product has SHA-256
`1a1ea6eac860ffc3854f7bd209135f4513ce97780639853a0c1993b323ea2d8e`; its manifest SHA-256 is
`cf25f6bd4155207cbca7dba5734d7eb74c0c91758a25a167f196a522999990f6`. It binds source digest
`1f273bf1ec466404c40a5d3f86f0654a6c42df0679541f0f1b1fd06366411ee9`, frontend/Stage1 `7b27fa…`,
strict mode, and `arm64-apple-darwin27.0.0`. Serial runs produced complete JSON without a crash:
`kernel_comparison_runtime.elisa` finished in 55.561 s with 3,831 obligations, 2,575 proven,
2,575/2,575 certificates replayed and zero gaps; mocap `track.elisa` finished in 21.141 s with
943 obligations, 926 proven, and 926/928 certificates replayed with the same two `Slide.inner`
gaps. Input SHA-256 values were `905a041e…` and `2723d053…`, respectively. This adds a current
O0 crash control after the lifetime-safe follow-up; the historical cause and Linux coverage remain
open.

Commit `95daaea` factors the bounded unsigned literal/add/sub replay path while preserving its
same-width checks, modulo-width arithmetic and refusal of malformed or unsupported nodes. The
kernel comparison runtime passed a direct O0 compile/link/run after the initial refactor; that run
predates the lifetime-safe follow-up `45e7f01`. On the later coherent exact-current O2 product, the
typed-unsigned report had 16 obligations, 11 proven, 11/11 certificates replayed and zero gaps;
three positive u64 checks proved and five expected refusals remained refused. The original crash
cause is still unknown, and this refactor is not evidence that it has been fixed.

## P-01 baseline

The seven-round baseline with one warm-up is complete for three pinned fixtures. Every report had
complete JSON and zero replay gaps; every emitted certificate replayed. Full raw results are in
`/private/tmp/elisa-p01-baseline-final-20261005.json`.

| Fixture | Obligations / proven | Scenario median wall (p95) | Median child CPU | Peak RSS |
| --- | ---: | --- | --- | ---: |
| `real_small` | 2 / 2 | cold 32.7 (33.7) ms; warm repeat 34.3 (34.8); no-op 33.4 (34.4); edit 32.9 (34.3) | 2.2–2.4 ms | 6.8 MiB |
| `real_refusal` | 2 / 1 | cold 35.4 (39.1) ms; warm repeat 34.0 (37.1); no-op 33.9 (36.9) | 2.5–3.0 ms | 6.7 MiB |
| `adversarial` | 78 / 49 | cold 190.5 (213.5) ms; warm repeat 192.3 (203.7); no-op 194.7 (199.5) | 164.9–169.9 ms | 58.8 MiB |

All invocations are fresh processes. “Warm repeat” means another run after warm-up may have
primed the OS file cache; it is not a persistent decision-cache hit or local session. Internal
timings for import, parse, semantics, VC generation, search, encoding, replay and reporting remain
unavailable. The measured corpus is narrow, and no incremental speedup is established.
Runner schema v3 preserves the full serialized `proof_report_measurements` object alongside
external CLI wall time, child CPU time, and harness JSON decode. A one-round smoke run against the
fresh no-cache product above completed all three fixtures with full reports and zero replay gaps:
`real_small` 2/2, `real_refusal` 1/2, and `adversarial` 49/78 proven. Raw output is
`/private/tmp/elisa-p01-schema-v3-20261005/baseline.json`; this checks the new capture fields, not
the timing acceptance gate. Internal import/parse/search/replay/report phase hooks remain
unavailable.

The P-01 instrumentation audit found no monotonic-clock API in the proof or compiler Elisa source.
`src/app/cli.elisa` exposes separate tokenization, parsing, proof-check, certificate-replay and
serialization stages, but `ProofReport.measurements` currently contains counters only. Adding
elapsed-time fields safely requires a runtime/compiler clock API first; no wall-clock substitute
was added to the proof process.

## P-02 cache identity and P-03 orchestration

P-02 recipe fingerprints now cover the report-cache and prefetch recipes plus the remote object
cache key and compiler-environment helpers. Focused identity tests cover hits for unchanged
recipes and misses after recipe changes. Report-cache controls cover included-source
`proof_float_mode` changes, runtime target changes, payload corruption, and fake-runner
cached-versus-uncached output equality. Remote object-cache controls cover compiler/runtime,
source trees, arguments, target, effective toolchain environment and cache recipe changes.

The real CLI equivalence control `scripts/test_report_cache_real_equivalence.py` prefetched each
fixture with `prefetch_reports.run_one`, required an actual cache hit without launching the
verifier, then compared the cached JSON bytes with a fresh uncached run. On the strict O2 binary
SHA-256 `549ae6fbae4e9a4d09373a537eec6c13f3701747d8a8d95ed8bce11d308e6d36`, both reports matched
byte-for-byte: `examples/perf_luna_accept.elisa` (input SHA-256
`b98bc4c879e7ca4279515ade0c248d125f9323a1f3e01f9bed389fc9a818354b`) proved 2/2 obligations with
2/2 replayed; `examples/perf_luna_refusal.elisa` (input SHA-256
`5bb1c84d7baf95c9853e448062184a3427b298d80b205ed7cd9ac8032a7cd454`) proved 1/2 with its one
certificate replayed. The focused script and Python compilation passed. This is bounded real
theorem/report equivalence for one accepted and one refused fixture; stale-product and broader
dependency-mutation controls remain open.

`scripts/test_report_cache_identity.py` also replaces the fake proof executable at the same path
after caching a report. The binary digest changes, the old report is not returned, and the new
prefetched result matches an uncached run byte-for-byte. This exercises stale-product invalidation
in the identity/cache harness; it is not a real verifier-binary replacement test.

The real equivalence test also creates a temporary root fixture that includes a separate `Limit`
module. Changing its constant from 0 to 1 leaves the root file bytes/path unchanged, changes the
report and cache key, and yields a new complete 2/2 replayed report. After prefetching the changed
dependency, the cache hit matched the uncached verifier bytes exactly. This is one real included-
source mutation control; other dependency classes and a real executable replacement remain open.

P-03 passed a controlled strict O2 initial build followed by an identical no-op. The no-op kept
main/replay binaries, runtime object, hook products and manifests unchanged, with identical hashes,
inodes, sizes and modification times. It performed no compiles, hook compiles, links, signing or
manifest writes. Three stable source-digest reads before sync and three after the no-op matched the
product. Evidence: `/private/tmp/elisa-proof-p03-refresh3-acceptance.json`; build and no-op traces:
`/private/tmp/elisa-proof-p03-refresh3-build.trace` and
`/private/tmp/elisa-proof-p03-refresh3-noop.trace`.

The focused `scripts/test_build_dependency_closure.py` control now also runs `scripts/build.sh`
twice in a temporary proof/compiler fixture with deterministic stub compiler and clang tools.
After the first build created both main and replay products, editing `src/unrelated.elisa`
outside both include closures caused the next build to report both products unchanged. Compiler,
hook-compile, and link logs had no new entries; binary, manifest, checksum, and binary mtime
remained unchanged. This verifies the real orchestration's outside-closure skip decision; stub
tools do not establish compiler or theorem semantics. The control passed on 2026-10-05 via
`python3 scripts/test_build_dependency_closure.py`.

## P-04–P-06 architecture and profiling

P-04 now has a proof-side v1 identity envelope that validates the proof build manifest and binds
frontend/compiler/runtime/checker/target context, normalized declaration identity, exact source
slice, ordered current dependency identities, and payload digest. A bounded content-addressed
store publishes that envelope and its payload in one immutable file via temporary-file fsync and
atomic link; reads revalidate manifest, source, payload, and dependency identities and reject
missing, oversized, truncated or stale entries. Focused tests cover idempotent publication and a
simulated interruption before linking. Since the compiler currently exports syntax IR rather than
resolved typed declaration bytes, the source slice conservatively invalidates formatting changes
within a declaration. A real dependency graph, reverse invalidation scheduler, checked semantic
summaries, and verifier/session reuse remain unimplemented.

P-05 has a package restart/fresh-process replay slice with additional negatives for forged source
authentication, elevated trust, altered statements and altered fingerprints. Packages explicitly
say `source.authenticated: false`; there is no retained local session, generation token,
cancellation or safe stale-publication boundary. See
[`P-05_SESSION_READINESS.md`](../P05_SESSION_READINESS.md).

The coherent current strict O2 product is
`/private/tmp/elisa-p06-proof-coherent-20261005/build/elisa-proof`, SHA-256
`ba640c47a1107c87e3105bf3ad005d3b2bbddc9d09bfb066427e27ee7610fd1e`. Its manifest binds proof
source digest `1f273bf1ec466404c40a5d3f86f0654a6c42df0679541f0f1b1fd06366411ee9`, frontend and
Stage1 revision `7b27fa312c5af923f044f6ee0e5e1de4f811f595`, and runtime object SHA-256
`b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897` for target
`arm64-apple-darwin27.0.0`. The typed-unsigned report control passed on this exact binary with
complete replay.

On this exact product, `balance.elisa` completed three instrumented runs at 10.37, 13.34 and
16.80 seconds. All three reports were complete and proved/replayed 240/240 obligations with zero
gaps; stdout was 9,882,857 bytes. The matching pinned compiler lexer source
(`src/lexer/lexer.elisa`, SHA-256
`790f7e89330800c19c85b4a9e6e23259877cf5bc561a9f7700dedb451a6456e9`) completed one expected
refusal run in 50.63 seconds: 326 obligations, 110 proven, 216 unproven, 110/110 certificates
replayed, zero gaps, and complete 1,915,250-byte output. Its profiler sidecar is marked partial
because the valid refusal exits 1; capture itself completed with zero dropped frames.

Function/event/call-edge/location/timing data is complete for both. Stack detail is partial under
the 16 MiB cap: 288,437,385 balance stack records and 181,588,070 lexer stack records were dropped.
The function profiles repeatedly show `proof_kernel_replay_valid`, `root_valid`, witness-marker
candidate extraction, replay goal/depth/report work, and arena helpers as hotspots. These are
instrumented discovery signals, not speed claims. The raw JSON, sidecars, exact identity records,
and commands are in `/private/tmp/elisa-p06-profile-20261005-recovered/` (`balance-final-functions.json`,
`lexer-final-functions.json`, and `identity-final-after-profile.json`). The earlier `ad1888…`
profiles remain historical and are not attributed to the current source. No optimization or paired
uninstrumented speedup is established yet; the known `track` 300-second timeout remains a separate
bounded failure and was not repeated.

## P-07 current census

The six-input refresh ran serially against proof source digest
`1f273bf1ec466404c40a5d3f86f0654a6c42df0679541f0f1b1fd06366411ee9`, frontend/Stage1 revision
`7b27fa312c5af923f044f6ee0e5e1de4f811f595`, and proof binary SHA-256
`ba640c47a1107c87e3105bf3ad005d3b2bbddc9d09bfb066427e27ee7610fd1e`. All input hashes matched
before and after. Per-input time/RSS ceilings and raw captures are recorded in
`/private/tmp/elisa-p07-current-20261005/aggregate.json`.

| Input | Result | Obligations / proven | Certificates / replayed / gaps | Time | Peak RSS |
| --- | --- | ---: | ---: | ---: | ---: |
| `balance.elisa` | Proved | 240 / 240 | 240 / 240 / 0 | 0.231 s | 19,920 KiB |
| `track.elisa` | Incomplete replay | 943 / 926 | 928 / 926 / 2 | 10.539 s | 131,024 KiB |
| `field_equality_runtime.elisa` | Timeout, no complete report | — | — | 120.171 s | 601,536 KiB |
| `kernel_comparison_runtime.elisa` | Unsupported findings | 3,800 / 2,544 | 2,544 / 2,544 / 0 | 23.279 s | 612,672 KiB |
| `kernel_core.elisa` | Proved | 37 / 37 | 37 / 37 / 0 | 0.076 s | 15,824 KiB |
| `lexer.elisa` | Unsupported findings | 326 / 110 | 110 / 110 / 0 | 0.422 s | 60,720 KiB |

`kernel_comparison_runtime` had 1,109 unsupported sites and 691 unverified declarations;
`lexer` had 173 unsupported sites and 154 unverified declarations. All emitted certificates for
those two inputs replayed. The full `track.elisa` report is preserved at
`/private/tmp/elisa-p07-current-20261005/track-report-full.json`: certificates 512 and 513 are the
two gaps in `Slide.inner` at `slide.elisa:125`. The 120-second `field_equality_runtime` timeout and
the two replay gaps remain explicit bounded failures; no bound was extended after either result.
Individual census captures are `balance.json`, `track.json`, `field_equality_runtime.json`,
`kernel_comparison_runtime.json`, `kernel_core.json`, and `lexer.json` in the same directory. No
support repair has yet been accepted from this ranking.

## Acceptance status

These slices provide bounded, identity-bound build, baseline, cache, profiling and census evidence.
They do not complete P-00, P-01's full corpus/phase counters, P-02 equivalence controls, P-04, P-05,
P-06 or P-07. Required remaining work includes the historical crash's root cause and platform
matrix, session-backed incremental reuse, canonical identities and invalidation, a measured
hot-path change with paired uninstrumented results, current source-justified support repairs, Linux
qualification and immutable-snapshot full gates.
