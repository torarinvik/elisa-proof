# Loop control source-work accounting

## Original finding

`proof_replay_boundary_trace_shape_valid_with_cache` creates a local
`control_work` meter for loop-condition, loop-invariant, and loop-range traces.
In `boundary_trace_shapes.elisa`, it returns from a combined failure check when
`proof_replay_control_loop_fact_source_with_work` returns false; the addition
of `control_work` to the shared `source_work` happens only after that check.
Consequently, work performed by an unsuccessful loop validation is not charged
to the report-wide source-work counter.

This can repeat for invalid traces. `trace_memo.elisa` records memo entries only
for valid, untouched traces, so repeated consumers can re-run a failing
boundary validation. Loop checks may perform several bounded declaration and
owner scans before ultimately rejecting a mismatched or unsupported trace.
Each invocation obeys its local limit, but the aggregate work across retries
can exceed the shared report limit.

## Correction recorded in the working tree

Store the control validator's Boolean result instead of returning immediately.
Then merge its consumed work into `source_work` on both success and failure,
using a checked remaining-budget subtraction. If the local counter is invalid
or the aggregate addition would exceed the shared limit, saturate the shared
counter and fail closed. Only after accounting should the validator result
determine acceptance.

The caller now captures the validator result, charges its local work through
`proof_replay_source_work_charge_or_exhaust`, and only then returns the validation result.
If the charge would exceed the shared limit, the helper marks the shared counter
as exhausted and the trace fails closed. This ordering charges consumed work on
both successful and unsuccessful validation paths.

## Remaining budget precision

The current caller computes the shared report allowance before loop validation
and seeds the smaller control meter so the validator can spend no more than that
allowance. It extracts and charges the consumed delta before returning the
validation result, including when the trace is rejected. If no report allowance
remains, it skips validation.

The loop-invariant comparison had a separate SUMMARY-limited meter nested under
the CONTROL-limited validator. A new limit-aware wrapper seeds that meter from
the caller's remaining allowance and merges the consumed delta back into CONTROL.
Both direct entry-certificate matching and expanded-goal matching use this
wrapper. The general summary caller still uses the original SUMMARY meter
directly.

These source changes have not been compiler-checked or behaviorally validated.
The source guard pins the caller seed, consumed-work delta, zero-allowance path,
both nested-meter bridge call sites, and the adapter's invalid-limit,
zero-allowance, virtual-counter, and over-budget debit paths. The focused guard
passes; this is source evidence only.

Relevant code: `src/proof/replay/boundary_trace_shapes.elisa` around the loop
trace dispatch, `src/proof/replay/trace_memo.elisa` around valid-only memo
insertion, and repeated identifier declaration scans in
`src/proof/replay/boundary_control_sources.elisa`.

A repository-wide call-site search found the combined loop-fact validator is
consumed in-tree by this boundary-trace dispatch. Its local convenience
wrappers are otherwise only used to delegate within `boundary_loop_fact_sources.elisa`.
The nested argument comparator is also used by the SUMMARY-limited entry path;
that call continues to use the original helper.

## Regression status

`scripts/test_source_admission_inventory_budget.py` pins the current loop
branch ordering, caller allowance calculation, local meter seed, consumed-work
debit, and nested summary-meter bridge. It also checks that failed shared
charges saturate the counter before rejection and that the nested adapter
rejects invalid limits, zero allowance, counter underflow/overflow, and
over-budget deltas before accepting either a match or mismatch. The guard
passes against the current source.

The behavioral regression remains outstanding. It should exercise a loop
trace that scans source and fails late, then confirm repeated invalid
validations exhaust the aggregate budget rather than receiving a fresh local
allowance. A successful trace should debit exactly once, and an over-budget
merge should fail closed. It should also cover a reduced caller allowance in
the nested summary comparison and verify an over-budget comparison fails closed.

This correction is source-only. No build or runtime behavior test was
performed; compiler qualification and bounded replay validation remain
outstanding.

## Current runtime qualification blockers (2026-10-15)

Rechecked during the current goal continuation: both gate failures below remain
current. No stale-product override or compiler build was used.

The focused source guard passes, but current runtime artifacts were refused by
their provenance gates:

- `bash scripts/qualify_prebuilt_test.sh --json` exits 2 because the proof build
  manifest lacks the required `native_link_inputs` identity field.
- `bash ../Elisa-compiler/scripts/assert_stage1_fresh.sh
  ../Elisa-compiler/bin/elisac-stage1` exits 2 because the installed Stage1
  provenance uses unsupported schema `elisa-stage1-provenance-v1`; the checker
  requires v5.
- The proof tree pins compiler revision `c5a6616a740434c2e2002582970b004b5ca0ecfa`,
  while the adjacent compiler checkout is at `6b452e3ae7134cd71c50aced87e73304bc64e043`.
  The pinned frontend commit exists in that checkout's object store, but the
  pinned Stage0 commit was not found in the sibling compiler repositories
  checked during this audit.

No stale-product override or compiler build was used. Requalify or rebuild the
matching compiler/proof pair before running the behavioral regression; the
source guard is not runtime evidence.
