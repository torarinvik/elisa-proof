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

The source-admission matrix now passes all six malformed classes across all
12 CLI routes. Its stale partial-source success expectation was corrected to
the documented proved-only result contract: even an independently replayed
selected goal returns unknown when the source is incomplete. A standalone
complete control returns proved. Production admission logic is unchanged.
The CLI result-lattice suite also passes, retaining exact-match, forged/foreign,
missing, open, incomplete and replay-gap refusals. Its selected-gap control now
uses the existing loop-counter replay-gap fixture instead of condition-call
positions, whose certificates now replay. Log: engine
`build/validation/cli-result-lattice-refresh.log`.

The kernel inventory gate now passes: ten tables and 185 entries match the
source. The documentation removes a duplicate deterministic-call row, records
qualified enum scope typing and const-enum facts, and lists the current shared
source-adapter/search and package preflight dependencies. It also distinguishes
shape checks from selected source validators. This is an inventory repair; no
production trust boundary or full-matrix verdict changed.

An isolated build repairs the first fresh matrix failure,
`source_context_scope.elisa`: numeric range iteration binders now shadow an
outer namesake without inheriting its reference/write capability or borrowing
its slot. Scalar iteration values also use the current child-state sentinel
instead of pointing into an inherited binding by accident. Loop-header
captures are parser-lowered separately. The all-products strict build passes;
`test_range_binder_resources.py` proves the scope fixture with complete replay
and retains false-shadow and genuine borrow-contract refusals. The kernel
inventory gate passes. Build log: engine
`build/validation/prover-range-binder-build.log`. This isolated correction is
not included in the still-running b8ff7592 matrix.

Additional isolated qualification retains complete replay for lexical borrow
(1/1), disjoint-field borrow (1/1) and scalar capture (7/7) fixtures. Invalid
scalar capture and moved-borrow fixtures remain refused with zero replay gaps.
The fresh engine sweep runs all 73 proofs uncached and passes 66, with the same
seven remaining rows: both ActionInput rows, audio animation events, triggers,
virtual audio, motion overlay policy and sound-event assets. Log:
`build/validation/proof-range-binder-full-sweep.log`.

The collection builtin escape regression now checks the single severity-one
error at line 15 in grow and its argument-2 local-storage escape message,
without requiring compiler ordinal 620. The current compiler's
DiagnosticKind.StoreRefToLocal ordinal is 622; report output already states
that kind_code is revision-specific. The exact remaining findings, failed
verification reasons and complete replay assertions are preserved. Replaying
the updated matrix assertion against the isolated product passes.
