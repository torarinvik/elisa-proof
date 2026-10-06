# R-003 `Slide.inner` root 51 — current validation

## Result and rule boundary

The current clean proof source already contains the exact signed unit-shift replay rule, so this
pass did not add a second arithmetic rule or change producer trust. It added an explicit
Stage1-compiled runtime boundary control and a fresh-process portable-package replay regression.
The older source trace at
[`2026-10-05-r003-slide-inner-source-trace.md`](2026-10-05-r003-slide-inner-source-trace.md)
records the earlier root-51 refusal and is retained as historical evidence.

The kernel admits only `(x + 1) < y => x < (y - 1)`: exact syntax and operand identity, both
constants equal to one, strict `<`, one common witnessed signed width, primitive-comparison
source witnesses, and operation-range proofs from source facts. It does not add the branch guard
to the facts used to establish its own overflow safety. Only parentheses and positive `and`
conjuncts are searched. The producer blocks the corresponding unsigned shape before certificate
creation, avoiding producer/replay disagreement.

## Fresh product identities

Built proof CLI and portable replayer together, strict O2, Stage1, target
`arm64-apple-darwin27.0.0`. The clean proof worktree was at commit
`fba43d201e8c6e1872b6c1b0b79564383b322ad4`; compiled `src/` tree digest was
`3b553607bfdc27a7eafd8812ee66cd168a9b5c2601f9110496f9f7ad5d143377` and `source_dirty` was false.
Frontend revision/tree were `3778d8fd7ec8679371199458dacb9ff414d73a0c` /
`2bc528666da1d064cba5c1be5bcf59149b98f0e0`.

| Product | Build identity | SHA-256 |
| --- | --- | --- |
| Proof CLI | `a673a3fcdaa7d90488fba189d6af47ee82a8cf0155ae4b641919d5512bd1f986` | `529d0d1fcfeb39f05d01626b1d26dcea660f165417f0160ee0cdad1a0558880b` |
| Portable replay | `769bdf503f70b6b1bcd926395765afc5a57147a4577bbb653781f4f1a00f65fb` | `ccd86bdee02401c99f8de07243aa783bcc243ffc511d039c5f2e234a35cdfcb9` |

Both manifests name pair generation `fe32c3ad9dad4d46bfb8b92530c48999`. They record the Stage1
product SHA-256 `c22bfdf55e6882e5bd1a262d7ed2c9317223891f9c81ee1e74e9b89266b27bd9`, source revision
`3778d8fd7ec8679371199458dacb9ff414d73a0c`, committed source-tree digest
`c97dba6b9f59434b668ac9f02baec917a0b6f5795a0038d748412a731ab85d38`, and build-recipe digest
`a1fbbac38ae3c1dd91798f751f7b6960391e2173979faa54046535c7f5416c1c`. The linked Stage1 runtime
object SHA-256 is `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`.

## Validation

- `scripts/test_conditional_ensure_replay_gap.py`: passed. `Slide.inner` had six certificates,
  six replays, and zero gaps; roots 48 and 51 both replayed. The bounded positive signed-shift
  fixture replayed 2/2.
- Wrong-guard, missing-conjunct, missing-premise, unsigned, mixed-width, wrong-bound, and signed
  near-min/near-max overflow controls remained unproved with complete replay and zero gaps.
- Added a portable round-trip for the positive root-51 source. It exported two theorems and the
  standalone replayer accepted both in a fresh process, with zero not-replayed theorems.
- Added `examples/conditional_signed_unit_shift_runtime.elisa` and wired it into the Stage1 test
  matrix. The independently Stage1-compiled native program returned success for an interior true
  guard, a fallback case, and the largest non-overflowing `i64` increment (`I64_MAX - 1`). The
  compiled runtime executable SHA-256 was
  `cfdb99e5952d87f0f17c5a8f516df74403c70fc27fe4e6b082dc46ca545a570c`.
- `scripts/test_portable_replay.py`: passed, including its package mutation/fuzz controls and
  the new signed-shift round-trip. `scripts/test_unsigned_subtraction_upper.py` and
  `scripts/test_negated_increment_peer.py` also passed.
- `git diff --check` passed. The repository source-length checker still reports the unrelated
  pre-existing `scripts/test_build_dependency_closure.py` at 691 lines; this task did not edit it.

## Residual scope

This closes only the bounded signed `+1`/`-1` conditional implication and its replay gap. It does
not justify arbitrary implications, reversed or non-unit shifts, unsigned modular arithmetic,
or general fixed-width linear reasoning. Those cases remain refused or outside this rule and
require separate source-semantic and kernel evidence.
