# Dispatcher budget repair — focused source acceptance

## Reproduced source defects

The original `examples/dispatcher_budget.elisa` contains 23 calls to one target
and 24 executable statements. The policy incorrectly used call-site count and
included requires/ensure declarations in the dispatcher body window. Correcting
both classifications exposed 132 live facts against the existing 128 cap.

A focused certificate-context diagnostic showed raw call-result summary premises
remaining live after independently traced summaries were rebound to the local
holding that call result. `bound_call_summaries.elisa` now removes the old live
premise only after the replacement is actually appended. Original traces and
prerequisite certificates remain available to independent replay. No cap changes.

## Focused evidence

Command: pinned compiler/runtime `52d60fcf`, snapshot frontend, Python 3.14,
`scripts/test_dispatcher_target_count_compile.py` through the engine's bounded
runner (3 GiB, 300 seconds). Initial source acceptance passes in 12.92 seconds
at 1,879,872 KiB RSS, log `build/dispatcher-bound-summary-controls.log`.
Original positive proves completely with zero replay gaps; original over-budget
negative remains refused. Direct controls cover repeated targets, four/five-target
boundary, unresolved IDs, invalid ranges and the scan limit.

A fresh run with strict positive and sole-finding negative assertions also passes:
12.15 seconds, 1,828,416 KiB RSS,
`build/dispatcher-bound-summary-strict-controls.log`. Expanded dispatcher controls pass in 12.48 seconds at 1,772,592 KiB RSS
(`build/dispatcher-summary-regressions.log`). They add body-window boundaries,
zero targets, compact mutating summaries, their false-contract negative, and
reference facts across widening casts. Positive cases prove and independently
replay; the false contract remains refused with zero replay gaps.

The existing source-binding replay harness passes on the current source in
18.18 seconds at 1,699,760 KiB RSS
(`build/dispatcher-source-binding-controls.log`), preserving its original
initializer/rebind, shadowing, overloaded operator/custom cast, widening and
typed-return forgery controls. The harness helper used the frozen compiler binary
instead of a missing checkout-local installation; the original assertions and
snapshot revision check were retained.

The new dispatcher harness is registered in the integrated proof feature suite.
A clean paired product, original CLI acceptance and engine inventory remain open.
This is not full compatibility qualification or production promotion.
