# R-042 signed unit-shift replay at i64 boundaries

## Scope

This slice adds two controls for the narrow conditional replay rule
`(at + 1) < count  ==>  at < (count - 1)`:

- A safe near-maximum positive case requires `at < I64_MAX` and `count >= 0`. It proves and
  replays the postcondition without relying on the guard to establish either operation's range.
- An adversarial case fixes `at == I64_MAX` and `count == I64_MIN_PLUS_ONE`. Under wrapping
  arithmetic, the guard can become true while the consequent is false. The verifier must not use
  that overflowing guard as its own range-safety premise.

The named constants are source-level constants so the boundary meaning remains reviewable. The
negative case's purpose is specifically to test the independent source-fact overflow guard, not to
assert that Elisa evaluates overflowing operations by wrapping.

## Exact product identity

The isolated matched pair was built from proof commit `b7f5dd7483dce0b0e0774b35d390a49a19d5ba93`
with a clean proof source tree digest
`ab762c07a202b0dcdc4d5a51a02f027996d1e04b3e2274773174217c0a2b053d`. The fixture/test additions
are committed separately in `3f7cee74` and are passed as source input to that immutable prover.

- Pair generation: `e1fa6f66d25e4859922d021e86ac95f9`
- Target/options: `arm64-apple-darwin27.0.0`, strict, O2
- Compiler revision: `bc8def2eadf41dd088adce22b4d3d9e74aadfee9`
- Stage1 product SHA-256: `96eca8200bb268ea5cc1635a66d6b0da0cd85611331319c3227362d9421c2947`
- Frontend tree: `13ca668b6620f927ec06bb6f348e6b4a75c88a6a`
- Runtime object SHA-256: `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`
- Proof product SHA-256: `5bf17632cd75ac3d5c5f24c0762ac2b9bbe22276f2308945282520eaa7610e2c`
- Proof build identity: `9e4baecb4d0f0f60693a34838376f848b205d6e5d01aff0b4d151af6dcf7855a`
- Portable replay product SHA-256: `f79b2262731cda42d0ff09259001f8f9fe90e12553dd6bae0d7f53928d25ee44`
- Replay build identity: `456746ac8b36f01e1049b03d09a494cc926b6cf9db8e1bf3e807cc91d98c1017`

The compiler source checkout passed `stage1_provenance.py check` at the exact revision above. The
installed `~/.elisac/elisac-stage1` wrapper pointed at older snapshot `7b27fa31`; the build correctly
rejected an invocation that inherited that stale provenance. The successful build explicitly
selected the checked compiler root, product, and matching runtime object.

## Results

- `scripts/test_conditional_ensure_replay_gap.py`: passed. The near-maximum positive has two
  certificates and two replays. The overflow-guard control fails at `wrap-guard-goal`, emits no
  goal certificate, and has zero replay gaps. Existing wrong-bound, overflow, missing-conjunct,
  wrong-guard, root-48 and root-51 checks also pass.
- `scripts/test_portable_replay.py`: passed. All 16 positive packages replayed; the structured
  mutation suite and 512 bounded raw-byte mutations completed without crashes or partial theorem
  replay. In this run one changed byte stream remained a valid package and replayed successfully.
- `scripts/check_source_length.py`: passed on the integrated worktree after the responsibility-based
  CLI split.
- `git diff --check` and Python syntax compilation: passed.

## Limits and follow-up

This evidence checks one `i64` upper-bound positive case and one wrap-sensitive refusal. It does
not establish all signed widths, both edge directions, or every route that can carry the guard into
the kernel. An exploratory positive variant using only `count > I64_MIN` as the lower range premise
produced one replay gap; replacing that premise with the simpler `count >= 0` yielded the intended
safe boundary control. The negative-lower-bound replay limitation remains an open arithmetic
expressiveness item and must not be reported as fixed by this slice. The matched pair predates the
latest report-inventory and call-witness commits; rebuild the integrated pair before claiming
whole-program current-product validation.
