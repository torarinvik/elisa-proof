# R-013 bounded fact-growth scaling slice

## Scope and method

Added `scripts/test_fact_growth_scaling.py`, a deterministic 25-case harness. It creates a
separate source file for every point and changes one dimension within each sweep:

- proof-relevant facts: a chain of non-negativity inequalities over `n + 1` integer inputs;
- irrelevant facts: `x <= k` premises added to a function whose result is the literal zero;
- duplicate facts: repeated copies of the existing constant self-equality premise, with the
  theorem and bounds held fixed;
- branch width: a single integer `match` with `n` literal arms plus a default arm, every arm
  returning zero.

The relevant-fact chain necessarily grows parameter arity with its premise count so every
inequality contributes to the final bound; this is not a same-arity accumulation experiment.
Likewise, the match sweep creates additional arm obligations as width grows.

The fixed `fact_growth_work_budget.elisa` 12-proof/13-refusal regression and
`bounded_model_work_budget.elisa` regression run first and are required to pass. Every generated
case has a 60-second wall timeout and a 2,097,152 KiB process RSS cap. RSS is sampled over the
process group and verified against `/usr/bin/time`'s exact command peak; a sampled over-limit
process group is killed. Raw per-case data, generated-source hashes, semantic status, goal
outcomes, replay counts/gaps, exposed counters, wall duration and RSS are in
[`2026-10-05-r013-fact-growth-scaling.json`](2026-10-05-r013-fact-growth-scaling.json).

## Result summary

| Axis | Sizes | Semantic/replay result | Observed counters (first to last) | Peak RSS |
|---|---:|---|---|---:|
| Relevant facts | 1, 2, 4, 8, 12, 16 | All proved; 0 replay gaps | live-facts peak 6→51; control-flow steps 5→20; kernel nodes 23→143; report bytes 11,864→66,073 | 8,352 KiB |
| Irrelevant facts | 1, 2, 4, 8, 12, 16 | All proved; 0 replay gaps | live-facts peak 4→19; control-flow steps 5→20; kernel nodes 16→61; report bytes 9,255→27,431 | 7,024 KiB |
| Duplicate facts | 0, 1, 2, 4, 8, 12, 13 | 0–12 proved; 13 refused as unknown; 0 replay gaps | live-facts peak 4→19; control-flow steps 5→18; kernel nodes 21→28; report bytes 10,705→19,457 | 7,408 KiB |
| Match-arm width | 1, 2, 4, 8, 12, 16 | All proved; 0 replay gaps | obligations 3→18; control-flow steps 10→55; kernel nodes 17→77; report bytes 11,290→174,459 | 7,984 KiB |

All 25 invocations finished without timeout or RSS refusal. Per-case wall time was approximately
0.039–0.045 seconds on this machine; it is descriptive only. These measurements do **not** imply
an asymptotic complexity, a general scaling bound, or a speedup. In particular, the match sweep
creates additional arm obligations as width grows; its proof and report counts must not be read
as fixed-work comparisons. The duplicate-fact 13-point refusal is expected budget behavior, not
a semantic counterexample or replay failure.

## Instrumentation coverage and gaps

The report exposes: declarations, obligations, goal attempts, certificates, certificate facts,
largest certificate fact count, repeated certificate fact roots, fact traces, control-flow steps,
live-facts peak, goal-cache hits/misses, kernel nodes/shared nodes/children, and report bytes.
`control_flow_steps` and `live_facts_peak` are the checker’s current instrumentation, not a count
of every solver operation or a process-wide memory census. Kernel/report sizes describe produced
artifacts, not CPU work.

Still unavailable at the source revision measured (the first item is absent from both the
checked source tree and report schema; it was not silently treated as zero):

- `goal_cache_key_fact_candidates` and total per-goal fact visits;
- predicate/term comparisons and total symbolic solver work;
- branch/fork and branch-join counts;
- allocation count/bytes and per-phase allocation peaks;
- per-goal CPU time and per-goal peak memory.

The process-level wall/RSS caps and peaks are available here, but do not fill those per-goal
instrumentation gaps. No prover implementation, work-budget threshold, fixture, or benchmark
module was changed.

## Product provenance and validation

The installed Stage1 binary was freshness-checked against its immutable snapshot with
`stage1_provenance.py check`; it reports current at revision
`7b27fa312c5af923f044f6ee0e5e1de4f811f595`, matching the project pin. Both products were built
in the isolated R-013 worktree using that Stage1 binary and its matching runtime, strict mode,
O2. Proof and portable replay manifests record the same compiler revision, frontend tree
`ab8926f6080a13d21b06606af251e6f0027c2db5`, proof source-tree hash
`72d57a84b7c759943ea348ec1af50ccf8e678e5530c44751fa75d0778749a17f`, and runtime SHA-256
`b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`.

- Proof product SHA-256: `90ad8e3a41cabb8cd2c671cd2faba58f4be044d4b1a0d3f6edea1170c9bc5a51`.
- Portable replay product SHA-256: `81a1d52872278b944eae3ba55327e8c33850d3fa32bbb0adf2fc6255d96d3bf8`.
- `test_fact_growth_work_budget.py`: passed (12 duplicate premises prove/replay; 13 refuse).
- `test_bounded_model_work_budget.py`: passed.
- `test_fact_growth_scaling.py`: 25 cases recorded; 24 proved, one expected unknown/refusal;
  semantic-error count zero and replay gaps zero for every case.
- `test_measurements.py`: passed report schema and arena consistency checks.
- `test_portable_replay.py`: 16 packages replayed; semantic/package-reader attacks refused.
- Python compilation and `git diff --check`: passed.
