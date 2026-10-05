# R-004 obligation ledger entry identity

The report ledger now stores `(identity, proven)` entries. `proof_obligation` assigns each
accounting event the ledger count before append, making identity a contiguous zero-based ordinal.
Shared report admission requires the stored ordinal to match its position, then totals the
`proven` fields as before. This catches duplicated, reordered, or identity-forged rows while
preserving entries for unsupported checks that did not produce a goal attempt.

The producer API is `proof_obligation(report, proven)` and has 144 call sites, including paths
with no extracted goal. This change deliberately binds the identity of each accounting event and
its order, not a semantic source location or obligation kind. Adding source semantics would
require threading reliable metadata through those producer APIs and remains a follow-up.

## Validation

- Proof source base commit: `1a4151b5eec9e5b1647bd3f9a3f8b70d1d8c1bea`; edited source tree SHA-256:
  `a0d64491d701a6a190ff2e87bf2d159eab0cf46989085e96c267af1bd985c565`.
- Stage1 compiler wrapper SHA-256: `6ea54e777ca7f07d5d0819367d0758463409d71fa8f38159f1c7a48c1222437f`;
  pinned compiler revision: `7b27fa312c5af923f044f6ee0e5e1de4f811f595`.
- Runtime object SHA-256: `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`;
  profile hooks SHA-256: `ff7eb87b67bbc470ee95c320bb95ff125300f1edc8c2e67585d282e27e0e9711`.
- Stage1 O0 compilation, native link, and execution of `examples/report_invariants_runtime.elisa`:
  passed (exit 0). Mutations swap two distinct ledger rows and forge an identity; shared admission
  rejects both.
- Strict O2 proof build: binary SHA-256
  `12e03fd5e03dbf68d02c02658bbfacd2ffedcff3c17c8ce413b48b82748215e2`.
- `scripts/tests/test_report_inventory_completeness.py` with that proof binary and the focused
  mutation harness: passed (`report inventory: source controls and shared admission mutation
  harness passed`). The test retains the unsupported computed-write-place refusal control.
