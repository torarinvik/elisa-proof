# R-004 open-attempt bound evidence

Date: 2026-10-05

## Change

Source admission requires `goal_attempts.count <= obligations`. The accounting ledger can contain
obligations with no goal attempt when unsupported analysis stops before goal extraction, so the
reverse equality is intentionally not required. Every recorded goal attempt, however, must have a
counted obligation.

The runtime mutation creates two open obligations and two corresponding attempts, then removes
one obligation row and decrements the obligation total while retaining both attempts. Before the
new bound, the remaining event ledger and aggregate total agreed and there was no proven-attempt
count mismatch. The mutation now fails source admission.

## Focused verification

- Base proof revision: `4e8e3fbb85f1725ac3401285048bab9dfb8dac56`
- Compiler: `~/.elisac/elisac-stage1`, provenance `7b27fa312c5af923f044f6ee0e5e1de4f811f595`
- Command: `~/.elisac/elisac-stage1 -permissive -emit obj -O0 -o /tmp/luna-r004-report-invariants.o examples/report_invariants_runtime.elisa`
- Link and run: `clang -o /tmp/luna-r004-report-invariants /tmp/luna-r004-report-invariants.o ~/.elisac/elisacore_runtime.o && /tmp/luna-r004-report-invariants`
- Result: the source harness compiled, linked, and exited 0.

## Remaining limit

This closes only a report consistency gap for a goal attempt that remains after its counted
obligation is deleted. It does not derive expected checks from source bodies, detect a skipped
source path that emits neither an attempt nor an event, classify unreachable paths, or exercise
all CLI/cache/tactic/repair/package admission routes. R-004 remains open.
