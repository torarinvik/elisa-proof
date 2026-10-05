# R-004 proven-attempt inventory evidence

Date: 2026-10-05

## Change

`proof_report_proven_attempts_consistent` counts successful `ProofGoalAttempt` rows and requires
the result to equal `ProofReport.proven`. Source admission and whole-report completeness both
apply the predicate. `examples/report_invariants_runtime.elisa` mutates the report by omitting a
successful attempt and by removing it after recording; both forged report states are refused.

## Product and toolchain

- Proof revision: `43796a5eac31ce5707645e2815b294dd16ab4b5d`
- Proof source tree SHA-256: `4e870372e87f2d3ea7e3112f546542c036b9d2514b1f8b248aafb181a1f8a2df`
- `elisa-proof` SHA-256: `9363e938ab063baf212ff8ebd9e3d75e8a0f46470897d738c8f0f5222a3814eb`
- `elisa-proof-replay` SHA-256: `b0ddf0e7d279a003b468e317566471c0227ef78d3e309ddd22083900922bb7ed`
- Build: strict Stage1 O2, target `arm64-apple-darwin27.0.0`
- Stage1 source revision: `7b27fa312c5af923f044f6ee0e5e1de4f811f595`
- Stage1 compiler SHA-256: `f77278c716dea7f3dba8f4fcbcf76ecc473426ab3f163c95fea4e358f6337653`
- Runtime object SHA-256: `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`

## Verification

The strict build completed successfully with the repository build script and pinned toolchain. The
report-invariant runtime harness was compiled at O0/permissive with that Stage1 compiler, linked
against its matching runtime object and the existing profile hooks object, and exited 0. The
source-admission regression passed on the exact strict O2 proof binary:

```text
ELISA_PROOF_BIN=build/elisa-proof python3 scripts/test_source_admission_matrix.py
source admission matrix: 6 malformed classes refused on all 12 routes
```

The matrix also exercises admissible incomplete-goal cases so the strengthened counter check does
not require unrelated open goals to become solved.

## Remaining gate

The current check ties the producer's success counter to its successful attempts, and the
declaration-detail count to the declaration counter. It does not independently derive the
expected obligation set from source, detect removal of both an attempt and its count, or prove
that every unsupported analysis path records its missing check. R-004 remains incomplete.
