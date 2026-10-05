# R-003 `Slide.inner` source trace — 2026-10-05

## Reproduction

Built `build/elisa-proof` from this clean proof tree with strict O2 using
`/private/tmp/elisa-p06-compiler-pinned-20261005/bin/elisac-stage1` and its matching runtime
object. The manifest records compiler SHA-256
`f77278c716dea7f3dba8f4fcbcf76ecc473426ab3f163c95fea4e358f6337653`, runtime SHA-256
`b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`, strict mode, O2, and
`arm64-apple-darwin27.0.0`. The proof binary SHA-256 is
`2f98c7849bf4e522b8714df3f38250cf38a63649b1779a800c9ee7cb0ef7e6a7`.

`ELISA_PROOF_BIN="$PWD/build/elisa-proof" python3 scripts/test_conditional_ensure_replay_gap.py`
passed. It observed six certificates, four replayed, and two refused gaps in the slide fixture;
the wrong-guard control remained failed with zero replay gaps. The focused arithmetic refusal
controls also passed: `scripts/test_unsigned_subtraction_upper.py` and
`scripts/test_negated_increment_peer.py` kept unguarded/overflow-sensitive subtraction, mixed
width and equal-progress cases refused with complete replay. The gaps are certificate roots 48
and 51.

## Source trace

Both goals are generated from the return expression
`1 if at >= 1 and at + 1 < count else 0` and the corresponding postconditions:

- Root 48 is `(if c then 1 else 0) == 0 or at >= 1`, where
  `c = (at >= 1) and (at + 1 < count)`. The exact kernel rule
  `proof_kernel_replay_conditional_fallback_or_guard` in
  `src/proof/kernel_replay/field_places.elisa` handles a conditional equal to its fallback value
  or its guard, but requires the guard disjunct to equal the entire conditional condition. Here
  the postcondition supplies only the first conjunct. The ordinary conditional split substitutes
  the arms, adds `c` or `not c` to branch facts, then tries direct disjunct replay; that direct
  check does not derive the first conjunct from the compound fact.
- Root 51 has the same conditional equality with fallback disjunct `at < count - 1`. The true
  branch needs the integer implication `at + 1 < count => at < count - 1`. This requires checked
  signed arithmetic, including that `at + 1` and `count - 1` are in range under the source
  preconditions `0 <= at < count <= 10,000,000`; no replay witness currently supplies that
  derivation.

Replay dispatch in `src/proof/kernel_replay/resource_model.elisa` tries the exact fallback/guard
rule and then `proof_kernel_replay_nested_conditional_goal`. The latter replays both substituted
goals, and for an `or` uses `proof_kernel_replay_disjunction_direct_branch`. Neither route admits
these roots on the current certificate. The earlier bounded experiment recorded in
`docs/evidence/2026-10-05-p07-slide-inner-conditional-gaps.md` tried conjunct recognition and
ordinary branch replay; a fresh build still refused both roots. That is useful negative evidence,
not a reason to broaden acceptance.

No sound, isolated replay or producer correction was established in this pass. R-003 remains open
for roots 48 and 51. The regression must continue to accept only complete replay or explicit
refusal, and the wrong-guard and overflow-sensitive refusal controls must remain in force for any
future rule.
