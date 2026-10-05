# P-01 bounded baseline

The baseline runner in `scripts/p01_baseline.py` does not build or modify the proof product. It
checks the adjacent manifest and checksum against the selected executable, requires proof-source,
frontend, compiler, runtime, target, optimization, and compile-mode identities, and spools each
bounded report to disk so large JSON cannot deadlock a pipe. Runner schema v3 records seven rounds
after one warm-up, invocation wall and child CPU time, peak RSS, declaration/obligation counters,
and certificate replay completeness. Each run row also preserves the complete serialized proof
report `measurements` object, including report bytes, kernel/certificate counters, and the
heaviest-function summary. It separately times decoding the captured JSON in the Python harness.
The runner schema is v3; earlier captured output remains in its original schema.

## Current result (2026-10-05)

The measured product is strict O2 for `arm64-apple-darwin27.0.0`. Proof source tree
`1cf9eb5e5354558f5e6cf10a66c096a63a8535967f84d7c2322faaf8a7f9aa36` was built with pinned
frontend revision `4c479ad1981403c9f77f04a9ee5918f74713533e` (tree
`545f10f3d5c1118cc9a4765e46543fe9f874cb02`), Stage1 compiler source revision
`60c906665c7c48c10daca5d889f6e351796d4e51` (product SHA-256
`79ef1bc37a4595e815ec9351cf911f0c73c35b9700ca96923b1df181bc1e92d8`), and runtime object
SHA-256 `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`.

Proof CLI SHA-256 is `cfec8d7225fa6a6161e761c6cd6c2f70867ee2a1c005097f9373e9e1e45b5d04`;
its build manifest SHA-256 is `b485ff436185c8d1792d541615af883a31a1d6b19412fa075a2a52691c28ad04`.
The report is complete, its build manifest matches the selected binary, all seven rounds have
complete JSON and zero replay gaps, and every certificate replays. The exact raw result is
`/private/tmp/elisa-p01-baseline-final-20261005.json`.

| Fixture | Obligations | Proven | Replay gaps | Scenario median wall (p95) | Median CPU (p95) | Peak RSS |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| `real_small` | 2 | 2 | 0 | cold 32.7 (33.7) ms; warm repeat 34.3 (34.8) ms; no-op 33.4 (34.4) ms; edit 32.9 (34.3) ms | 2.2–2.4 (2.7–4.3) ms | 6.8 MiB |
| `real_refusal` | 2 | 1 | 0 | cold 35.4 (39.1) ms; warm repeat 34.0 (37.1) ms; no-op 33.9 (36.9) ms | 2.5–3.0 (3.4–3.7) ms | 6.7 MiB |
| `adversarial` | 78 | 49 | 0 | cold 190.5 (213.5) ms; warm repeat 192.3 (203.7) ms; no-op 194.7 (199.5) ms | 164.9–169.9 (181.2–184.2) ms | 58.8 MiB |

Each invocation is a fresh process. “Warm repeat” means a second check after one warm-up may have
primed the OS file cache; it is not a persistent proof-cache or local-session hit. The no-op
scenario adds a comment, and the small accepted fixture also has a body-edit scenario. These
measurements do not demonstrate incremental declaration reuse or a speedup.

## Counter coverage and remaining P-01 work

Serialized proof-report counters include goal-cache hits/misses, control-flow steps, peak live
facts, declaration/obligation totals, replay totals, and report bytes. The baseline preserves the
entire CLI `measurements` object for every invocation, including kernel node/child totals,
certificate-fact reuse counts, fact traces, and heaviest functions. Each runner row's
`phase_timings_seconds` distinguishes proof CLI invocation
wall time and child CPU time from Python JSON decoding. The invocation wall includes process
launch, wait polling, and captured-output handling; it is not an internal proof-stage timer.
`phase_timing_availability` names internal timings that remain unavailable: source import,
lexing, parsing, summary scheduling, replay, and JSON rendering have no clock hook in the proof
executable; resolution and semantics share one opaque `Semantic::check_full_into` call; VC
generation/search/goal recording are interleaved. No duration is estimated for these phases.
Separate resolution and semantic timings need compiler phase hooks, and internal timings need a
portable monotonic clock in the linked product. The current captured baseline remains historical
schema v1; rerunning the runner emits schema v2. The machine is one arm64 macOS host, so this is
not Linux qualification or a cross-platform speed claim.

P-01's seven-round current-product baseline gate is met for this fixed corpus and machine. A
versioned broader real-code/adversarial corpus, internal phase timing, and edit/no-op measurements
from a retained session remain open under P-04/P-05.
