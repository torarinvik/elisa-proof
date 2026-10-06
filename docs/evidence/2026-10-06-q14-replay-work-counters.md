# Q1.4 scoped replay work counters

This milestone adds two deterministic measurements to the final report:

- `replay_arena_records_scanned`: node records visited by the canonical whole-arena admission pass.
- `replay_child_table_edges_scanned`: child-table slots inspected by that pass's postorder-edge check.

The counters are reset at the start of each certificate-replay batch and increment only where the
existing replay admission loops visit those records/slots. They are observational: no proof rule,
budget, admission condition, or result consumes them. A tiny successful source fixture checks that
the scan counts equal its serialized kernel-node and child-table array lengths. The repeated-fact
work-budget fixture checks that the below-cap goal still proves and replays, while the above-cap
goal remains an explicit budget refusal with no certificate; the measurements are present on that
report as well.

There is currently no counters-disabled CLI mode, so enabled/disabled report equivalence was not
applicable. The tests instead preserve the expected proof status, goal outcomes, and replay-gap
invariants while checking the new measurement values. No speedup or runtime overhead claim is made.

This is intentionally a narrow start to Q1.4. It does not count scalar `left`/`right`/`auxiliary`
references as edge visits, per-certificate reachable-node visits, source AST nodes/declarations,
import lookups, generated obligations, live/duplicated facts, branch copies, congruence/arithmetic
work, allocations, normalization/substitution/cache activity, solver queries, JSON/package bytes,
or retained-arena peaks. Those families remain planned follow-up work; counters from this milestone
are not a complete work census.

Validation used a strict Stage1/O2 proof build pinned to compiler/frontend revision
`3778d8fd7ec8679371199458dacb9ff414d73a0c`. The tiny fixture reported 13 arena records and 6
child-table edges, matching its serialized arrays, with 2/2 certificates replayed and zero gaps.
`scripts/test_measurements.py`, `scripts/test_fact_growth_work_budget.py`, and
`scripts/tests/test_disjunction_work_accounting.py` passed; Stage1 provenance and `git diff --check`
passed. The repository-wide source-length check still reports the pre-existing 691-line
`scripts/test_build_dependency_closure.py`; this milestone did not modify that file.
