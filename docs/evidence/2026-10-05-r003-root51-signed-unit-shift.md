# R-003 `Slide.inner` root 51: bounded signed unit shift

## Result

Root 51 now replays for the exact guarded implication in `Slide.inner`:

```text
(at + 1) < count  ==>  at < (count - 1)
```

This is not a general implication rule. The kernel recognizes only the positive-conjunct
shape `(x + 1) < y` and target shape `x < (y - 1)`, requires the compared expressions to
have one common, positively witnessed signed width, and invokes the existing checked linear
arithmetic replay. Before doing so, it checks the range safety of all source facts and both
arithmetic expressions using source facts only. The guard is added only as a premise for the
arithmetic entailment, never to prove its own overflow safety. Conjunction search descends only
through parentheses and positive `and`; it does not look through disjunction or negation.

## Compiler and immutable products

At task start the compiler checkout was clean at `bc8def2eadf41dd088adce22b4d3d9e74aadfee9`.
The current Stage1 provenance checker passed. The compiler product SHA-256 is
`96eca8200bb268ea5cc1635a66d6b0da0cd85611331319c3227362d9421c2947`; its matching runtime
object SHA-256 is `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`.
The products were built strict O2 for `arm64-apple-darwin27.0.0` in an isolated detached
worktree at proof commit `fcbc4b959552aa3984ad10a234aacaf105a2079e`. The manifest records a
clean proof source tree digest `ab762c07a202b0dcdc4d5a51a02f027996d1e04b3e2274773174217c0a2b053d`
and frontend revision `bc8def2eadf41dd088adce22b4d3d9e74aadfee9` / tree
`13ca668b6620f927ec06bb6f348e6b4a75c88a6a`.

| Product | Build identity | Binary SHA-256 |
| --- | --- | --- |
| Proof CLI | `cac084fdc0c8ccd34b68cf720680c146f71b2c35a2e3529cdb1ad96a6d0fb78d` | `733b74c78e3c6772c1c617ab4cce1ab7a21c4e747877e0a656b86fc8fcefae5c` |
| Portable replay | `0ade2ed9e21b4102cc9d97ef992d58b653a1b4f8aa36e8711e3cac3961868efa` | `d9f86117198f2c660c2a9989ffa434da325e73aa4cd7522d329e81407d962017` |

## Validation

- `scripts/test_conditional_ensure_replay_gap.py`: passed. `Slide.inner` reports six
  certificates, six replays, zero gaps; roots 48 and 51 both replay. The focused bounded
  signed-shift positive fixture replays 2/2.
- Wrong-guard, missing-positive-conjunct, overflow-sensitive, and wrong-bound fixtures all
  remain failed obligations with complete certificate replay and zero replay gaps. The
  wrong-bound case uses the same source ranges but asks for `at < count - 2`, which is false
  for a concrete in-range input.
- `scripts/test_unsigned_subtraction_upper.py`: passed, including its unguarded and mixed-width
  refusal controls.
- `scripts/test_negated_increment_peer.py`: passed, including overflow, mixed-width and
  equal-progress refusals.
- `scripts/test_portable_replay.py`: passed; 16 positive packages replayed and package-reader /
  semantic attacks were refused.
- `git diff --check`: passed. The source-length check did not pass in the snapshot because the
  unrelated baseline `src/app/cli.elisa` is 614 lines; all files changed for this slice remain
  below 600 lines.

## Limits

The new rule handles only a left-sided `x + 1`, a right-sided `y - 1`, and strict `<`, with
matching signed widths and source-provable non-wrapping ranges. It intentionally does not yet
handle reversed comparisons, other offsets, mixed operators, generalized linear consequences,
or arbitrary guard implications. This closes this replay gap only; it is not evidence that all
`Slide.inner` obligations, the broader R-003 inventory, or the proof system as a whole are sound.
