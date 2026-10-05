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

The refreshed six-input census remains incomplete in three places: `field_equality_runtime.elisa`
timed out at 60 seconds (about 1.13 GiB sampled RSS); `track.elisa` reported 943 obligations and
926 proven, with 926/928 certificates replayed and two gaps; and the initial 1.5 GiB run of
`kernel_comparison_runtime.elisa` stopped at its memory cap before the separate larger bounded
run completed. Other current results include `kernel_core.elisa` at 37/37, mocap `balance.elisa`
at 240/240, and compiler `lexer.elisa` at 110/326 with 110/110 replayed and 173 unsupported
sites. The census is `/private/tmp/elisa-p07-support-final-20261005.json`.

The earlier crash cause, a minimal source/compiler regression, O0 behavior, and Linux behavior
remain open. The two track replay gaps are still bounds goals in included `Slide.inner`
(`slide.elisa:115`) formed from ternary-return index conditions. No crash disappearance is being
counted as a correctness fix. A separate three-line conditional-return case now reproduces a
single replay gap: `inner(at:i64)` has `ensure result == 0 or at >= 1` and returns `1 if at >= 1
else 0`. It contains no qualified constant or body rewrite, so this replay defect is independent
of the historical crash. The regression is in
`test/repro/minimal_conditional_ensure_replay_gap.elisa` and
`scripts/test_conditional_ensure_replay_gap.py`; it accepts a future complete replay or today's
explicit refusal, and rejects a `proved` label with gaps. The focused test passed against the
refreshed O2 binary. It does not yet identify which replay rule should be fixed.

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
Runner schema v2 labels external CLI wall time, child CPU time, and harness JSON decode separately;
only the first two are proof-process measurements, and none substitutes for missing internal
phase hooks.

## P-02 cache identity and P-03 orchestration

P-02 recipe fingerprints now cover the report-cache and prefetch recipes plus the remote object
cache key and compiler-environment helpers. Focused identity tests cover hits for unchanged
recipes and misses after recipe changes. Report-cache controls cover included-source
`proof_float_mode` changes, runtime target changes, payload corruption, and fake-runner
cached-versus-uncached output equality. Remote object-cache controls cover compiler/runtime,
source trees, arguments, target, effective toolchain environment and cache recipe changes.
Focused tests, Python compilation, remote shell syntax, and diff checks passed. The fake runner
does not establish real theorem-set equivalence; that remains an acceptance item alongside stale
product and broader dependency-mutation controls.

P-03 passed a controlled strict O2 initial build followed by an identical no-op. The no-op kept
main/replay binaries, runtime object, hook products and manifests unchanged, with identical hashes,
inodes, sizes and modification times. It performed no compiles, hook compiles, links, signing or
manifest writes. Three stable source-digest reads before sync and three after the no-op matched the
product. Evidence: `/private/tmp/elisa-proof-p03-refresh3-acceptance.json`; build and no-op traces:
`/private/tmp/elisa-proof-p03-refresh3-build.trace` and
`/private/tmp/elisa-proof-p03-refresh3-noop.trace`.

## P-04–P-06 architecture and profiling

P-04 now has a proof-side v1 identity envelope that validates the proof build manifest and binds
frontend/compiler/runtime/checker/target context, normalized declaration identity, exact source
slice, ordered current dependency identities, and payload digest. Mutation and malformed-record
tests fail closed. Since the compiler currently exports syntax IR rather than resolved typed
declaration bytes, the source slice conservatively invalidates formatting changes within a
declaration. A real dependency graph, reverse invalidation scheduler, checked semantic summaries,
and incremental admission equivalence remain unimplemented.

P-05 has a package restart/fresh-process replay slice with additional negatives for forged source
authentication, elevated trust, altered statements and altered fingerprints. Packages explicitly
say `source.authenticated: false`; there is no retained local session, generation token,
cancellation or safe stale-publication boundary. See
[`P-05_SESSION_READINESS.md`](../P05_SESSION_READINESS.md).

The latest P-06 profile attempt stopped before compilation because the profiler rejected the
pinned Stage1 compiler product for a `source_revision` provenance mismatch and then could not
resolve source dependencies. It did not bypass freshness or edit proof sources. Records are in
`/private/tmp/elisa-p06-profile-20261005-latest`. Current internal phase timings are therefore
still unmeasured.

## Acceptance status

These slices provide bounded, identity-bound build, baseline, cache and census evidence. They do
not complete P-00, P-01's full corpus/phase counters, P-02 equivalence controls, P-04, P-05, P-06
or P-07. Required remaining work includes a minimized crash/replay regression, session-backed
incremental reuse, canonical identities and invalidation, current profiling, source-justified
support repairs, Linux qualification and immutable-snapshot full gates.
