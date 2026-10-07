# Prover matrix with compiler 96761822

The all-products build of prover 2a0d0804 completed against compiler
96761822e6469efb929c5d50a804bb765f6bc3f7. The proof and portable replay products
were built before the matrix. The serial KEEP_GOING matrix completed with
status 1 and 98 failed steps. This counts failed shell steps, including
cascades, not 98 independent bugs. Full compatibility is unverified.

Engine evidence remains narrower: the last uncached sweep passed 66/73.
Deterministic call, chained pure call and portable disjunction/source-domain
controls passed. The matrix exposes additional source-inventory/replay gaps,
old report-layout references in mutation harnesses, old enqueue signatures,
a compile probe expecting the repository's older compiler pin, and census
failures. These must be triaged without weakening expected properties.

Subsequent focused repairs:

- 6e900582: compiler selection, source snapshot races and build closure pass.
- 34d727c3: 13 corpus manifest and seven Stage1 provenance tests pass.
- The expression-equality runtime probe now supplies the cumulative scheduled
  work counter, checks its exact limit, empties the queue and verifies new
  work remains refused. Its O0 compile, native link and execution pass.

No full matrix rerun or whole-prover success is claimed. Logs are retained
under engine build/validation: `prover-2a0d0804-all-build.log`,
`prover-2a0d0804-matrix.log`, `kernel-expr-equal-compile.log`.

The qualified-call source mutation harness was then migrated from removed
flat report members to `traces.records`, `traces.summary_names`,
`traces.summary_values` and the executable store. With the same strict fresh
Stage1 path, it compiles and executes successfully. Its nested source-owner,
omitted/duplicate/wrong-owner, argument order, source span, reassignment,
wrong-module and forged local-binding assertions remain intact. This repairs
one matrix harness; no full matrix success is inferred. Engine log:
`qualified-call-harness-layout.log`.

The reduced source-inventory test model now carries the production theorem
store and initializes the required context fields. All three report/branch/loop
probes compile strictly at O0, without permissive admission. Both assert-by
branch and loop probes link and run with status zero. The report-invariant
probe links and reaches status 34: `OMITTED_OPEN_OBLIGATION_WITH_ATTEMPT_ADMITTED`.
That adversarial assertion remains unchanged and failing. It is an open
inventory-boundary investigation, not a passing probe. Logs/objects are in
engine build/validation under `report-invariants-probe` and `assert-*-probe`.
