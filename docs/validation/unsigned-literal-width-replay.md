# Full-width unsigned literal replay

## Failure and source repair

The original `examples/strict_order_disequality.elisa` produces 12 certificates
but only 10 independently replay on the clean `5077910c` pair. The two gaps are
zero excluding maximum u64, including its parenthesized spelling. The producer's
literal-width guard accepts a bare negative AST payload at unsigned width 64;
replay's width evaluator rejects every negative payload. Source integer literals
store their high bits in an i64 payload.

Replay now mirrors that leaf-only width check for a valid, untagged integer node
under unsigned width 64. This does not change signed constant evaluation or
admit unary negatives, computed intermediates or narrower unsigned widths.
Primitive/source admission and the disequality rule still establish the exact
unsigned term and distinct constants independently.

## Focused source acceptance

`scripts/test_unsigned_literal_width_replay_compile.py` compiles current source
with frozen compiler `52d60fcf` and matching runtime. The original fixture retains
12 certificates, all replayed; same-value u64 and unary-negative fixtures remain
refused. Direct arena controls accept only the full-width leaf, reject 8/16/32
widths, unary negation, computed arithmetic and an invalid root. The check passes
in 12.65s at 1,863,872 KiB under the unchanged 3 GiB / 300s watchdog.
Log: `build/unsigned-literal-width-controls-direct.log(.json)`.
The fixture is registered in the integrated feature matrix.

The previous frozen compiler checkout was removed during qualification. Its
committed source was recovered using `git archive 52d60fcf` into the engine's
ignored `build/validation/compiler-52d60fcf-toolchain`. Its exported source digest
matches the paired manifest exactly:
`2c7ca0c709abb98d67c4e5f4ebfe10b98622f9437ec39d2593f76b3ccc523da7`.
The retained frozen compiler binary and runtime object remain selected explicitly.

Clean paired build, original CLI controls, engine sweep and full compatibility
remain pending. Production prover is unchanged.
