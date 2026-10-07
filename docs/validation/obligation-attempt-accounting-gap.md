# Source obligation and branch attempt accounting gap

The strict report-invariant runtime reaches status 34 on current source:
removing one open ledger event and decrementing the total leaves two open
attempts attached to one event, yet source admission accepts the report.
The existing adversarial assertion is retained.

The old attempts <= obligations rule cannot be restored: one source obligation
can legitimately have multiple branch attempts. The new
`report_branch_accounting_runtime.elisa` validates that positive case with one
proven ledger event, two attempts and two certificates. Its strict O0 compile,
native link and execution pass. It is wired into the standard matrix.

Required fix: record the accounting event identity for each attempt and validate
that association independently during admission. Permit many attempts per event,
permit unsupported events without attempts, refuse attempts for deleted events,
and reconcile event outcomes with their associated path results. Carry this
association through report serialization/cache/portable package boundaries and
mutation controls. Do not substitute a loose aggregate count check.

This is an open task. The positive control establishes the legitimate branch
case; it does not authenticate arbitrary claimed event identities. Production
admission has not been changed in this slice. Engine validation artifacts:
`report-invariants-probe` (status 34), `report-branch-accounting` (status 0).

An attempt-span prototype records the contiguous attempts preceding each
accounting event, including empty spans for unsupported events. Its checker
rejects gaps, overlaps, out-of-range spans and trailing orphan attempts.
The omitted-open-event mutation advances past status 34 under this prototype.
Integration is incomplete: synthetic source-coverage fixtures also introduce
extra branch attempts and must preserve their intended event associations.
The prototype patch is retained in engine build/validation as
`obligation-attempt-span-candidate.patch`; production source was restored.
A separate minimal nested-array clear control returns the expected count 2,
so the suspected reset defect was not reproduced and is not claimed.

The span implementation is now integrated. Each event records `attempts_start`
and `attempts_count`; the recorder consumes attempts since the previous event.
Admission requires ordered contiguous spans with safe bounds and complete
coverage. Empty event spans and multiple attempts per event remain supported.
The strict report-invariant harness now passes, including its omitted-open-event
control. The branch control passes and rejects missing trailing coverage,
nonzero first start and an out-of-range count, then accepts the restored span.

Both proof/replay products build with compiler 96761822. An uncached engine
sweep retains 66/73, with the same seven failures. Conditional, guarded-call,
deterministic-call and portable disjunction controls pass. The source-admission matrix subsequently passed after its stale focused-goal
expectation was aligned with the documented complete-source CLI contract
(398b2c45). The full prover matrix remains failing. Logs: `prover-attempt-span-build.log`,
`proof-attempt-span-full-sweep.log`, `source-admission-span.log` in engine
build/validation. The new spans are internal report accounting metadata;
portable replay retains its separate source/certificate validation boundary.
Further resealed-metadata mutation and outcome-association coverage remain open.

## Static frame event evidence gap

The new admission diagnostic isolates goal-attempt-coverage for a minimal
void-returning frame write (`test/repro/frame_accounting_allowed.elisa`).
There are three successful events: a valid changes clause, an allowed write
and resource safety. Only resource safety creates a goal/certificate, which
replays. The report correctly remains refused despite 3/3 producer counters,
no source diagnostics, no findings and no replay gaps. This is independent
of postcondition and branch accounting.

The outside-frame control has 3 events, 2 marked successful, one replayed
resource certificate and frame-write-outside. The preservation control has
5 events, 4 marked successful, one replayed resource certificate and
frame-preserve-write. Both are semantically clean and refused.

The correction needs checked evidence for each static frame event, bound to
its source frame, actual write/call place, formal owner and policy operation.
A replayed resource certificate alone checks resource transitions; it does
not establish a changes/preserves policy. Do not remove these events, replace
them with literal-true certificates, relax the proven-attempt lower bound or
associate them with unrelated resource evidence. Header and body frame specs,
direct/dynamic writes, call frame mapping and preservation checks share this
accounting path and all need coverage. False frame containment and overlapping
preservation controls must remain refused after accepted checks replay.

The pending certificate rule now has a source-neutral frame relation model
in `kernel_replay/frame_policy_model.elisa`. Places use caller parameter
ordinals and canonical zero-to-three field paths. It checks the entire bounded
policy before looking for containment, and refuses writes overlapping a
preserved ancestor or descendant. A strict O0 standalone compile/link/run
passes 13 controls: exact and ancestor containment, sibling preservation,
outside-frame writes, ancestor/descendant overlap, foreign/out-of-range
parameter identity, malformed trailing policy entries, empty changes and
over-budget parameter count. Runtime artifact: engine
`build/validation/frame-policy-relations`. Certificate encoding, source
correspondence, replay dispatch and producer event integration remain pending;
this model alone is not used to admit any source theorem.
