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
