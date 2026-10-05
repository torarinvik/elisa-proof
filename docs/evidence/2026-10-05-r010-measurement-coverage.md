# R-010 measurement coverage audit (2026-10-05)

This is a source-level inventory of the current CLI report and benchmark harness, not a timing run. R-010 remains open: the report has workload and proof-artifact counters, but the requested end-to-end internal phase timings and phase-work totals are not established.

## Existing report counters

`src/app/measurement_output.elisa` emits `elisa-proof-measurements-v1`. Its counters are derived from `ProofReport` or report arrays and do not control a verdict:

- Workload inventory: `declarations`, `obligations`, `goal_attempts`, `certificates`, `fact_traces`.
- Certificate shape: `certificate_facts`, `largest_certificate_facts`, `repeated_certificate_fact_roots`.
- Search/cache: `goal_cache_hits`, `goal_cache_misses`.
- Selected control-flow accounting: `control_flow_steps`, `live_facts_peak`.
- Kernel arena: `kernel_nodes`, `kernel_nodes_shared`, `kernel_children`.
- Output and concentration: `report_bytes` (bytes emitted before the measurements object) and `heaviest_functions` (attempt/fact aggregates by function).

The origins are narrower than the field names can suggest. `measured_control_flow_steps` and `measured_live_facts_peak` are updated in `src/proof/check/return_analysis_budgets.elisa` for budgeted return/control-flow analysis; they are not totals for all semantic or control-flow work. `goal_cache_*` count lookup hits/misses in the built-in goal-result cache, not all search attempts or solver work. `kernel_nodes_shared` counts producer interning reuse; it is not replay memoization work.

## Phase coverage

| Phase | Source boundary / available data | Coverage |
| --- | --- | --- |
| Import | `proof_import_source_mapped` in `src/app/cli.elisa`; import failure, source bytes/fingerprint, source map arrays | No import duration or imported-file/byte work total in the measurement object. |
| Lex/parse | `frontend_tokenize_with_length` and `frontend_parser_parse_file` in `src/app/cli.elisa`; parse findings and later declaration inventory | No tokenize or parse duration; no token/node count in report measurements. |
| Semantic checks | Proof check call in CLI; visible semantic diagnostics and errors are computed afterward | No semantic-pass duration or visits/check count. Some proof checks contribute obligations/goal attempts, but those are not a semantic-work total. |
| Scheduling | `proof_check_with_semantic_diagnostics` / focused variant | No scheduler phase, queue/SCC counts, or schedule duration identified in the CLI path. Work is not separately attributed. |
| VC generation | Obligation and goal recording in `ProofReport` | `obligations` and `goal_attempts` give inventory, not generation time, generated VC node count, or per-declaration totals by phase. |
| Search | Goal cache and budgeted control-flow counters above | Partial counters only; no visited-node, fact-scan, comparison, rewrite, substitution, branch-candidate, or search-duration totals. These belong to R-012 as well. |
| Certificate construction | Certificate/fact arrays and kernel arena arrays | Counts and shape are present; no construction duration or producer work total. |
| Replay | Report `replayed`/`replay_gaps` and CLI call to `proof_replay_certificates` | Outcome counts exist outside `measurements`; no replay duration or replay-work counter. |
| Serialization | `report_bytes` in `src/app/measurement_output.elisa` | Output size only; no serializer duration. It excludes the measurement object itself by construction. |

## Timing boundary and next work

The proof CLI source inspected here contains no monotonic clock API. `scripts/p01_baseline.py` uses external process measurements for CLI wall/CPU/RSS, then separately records `baseline_harness_json_decode` with Python `time.monotonic()`. Those are valid harness measurements, not internal phase timers. The runner preserves the complete proof report measurement object, but preservation does not create phase coverage.

Do not estimate an internal phase by subtracting external total durations: process startup, I/O, report writing, and nested phases would make the result ambiguous. The plan explicitly requires coordinating a genuine monotonic clock API with compiler/runtime support. Until that API exists, counters can be added at source-owned phase boundaries; each counter needs a defined ownership/denominator and a consistency check against report inventory. No single additional work counter was added in this audit because the current source does not expose one unambiguous end-to-end work unit spanning the requested phases.

**Gate status:** disabled instrumentation overhead has not been measured; exclusive nested phase timing does not exist; only declaration/obligation and artifact count identities can be checked from the existing report. R-010 remains open.
