# R-042 u8 shift boundary slice

## Source and products

- Source commit: `d0b946d6002b6b11b221cbe24c5b16df9e6fbe16`
- Source tree: `8892b7c71e803f8815b947614119e74256442ae7cfe0e82671c2034547003b82`
- Build mode: strict Stage1 O2, target `arm64-apple-darwin27.0.0`
- Stage1 executable SHA-256: `f77278c716dea7f3dba8f4fcbcf76ecc473426ab3f163c95fea4e358f6337653`
- Runtime object SHA-256: `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`
- Proof product SHA-256: `10f5f9a61012f9e0eafcae43aab7d90c1fd3f5051482dd048728753e003f9360`
- Portable replay product SHA-256: `913066442f2e22766aa7b858e6bc9a33a30c7ca73b3bca1e0da021f62426aef6`

## Audit and regression

The source constant evaluator `proof_shift_safe` and independent kernel helper
`proof_kernel_replay_shift_safe` both refuse negative shift amounts and amounts above the machine
word's maximum. The cross-width small-constant evaluators have matching guards: because their
term representation omits operand width, they only evaluate shifts below 7, which remain safe for
the smallest admitted integer width. They do not decide a u8 shift by exactly its width. This audit
found no producer/replay disagreement.

`examples/unsigned_u8_shift_boundaries.elisa` and
`scripts/test_unsigned_u8_shift_boundaries.py` exercise the following through source obligations
and independent certificate replay:

- `1 << 4 == 16` proves and replays.
- `1 << -1` emits the `shift count is negative` diagnostic and its postcondition stays unproven.
- `u8(1) << 8 == 0` stays unproven; the checker does not apply host or i64 shift behavior to the
  width-sized operation.
- A false `u8(128) >> 1 == 0` claim stays unproven; the high-bit input is not reinterpreted as a
  signed negative value to create a proof.

The report has zero semantic errors, zero replay gaps, and equal nonzero certificate and replay
counts. Command:

```sh
ELISA_PROOF_BIN=build/elisa-proof python3 scripts/test_unsigned_u8_shift_boundaries.py
```

Result: passed. The test is wired into `scripts/test.d/01-setup-and-python-suites.sh`.

This does not define execution behavior for oversized shifts or prove the true high-bit result
`u8(128) >> 1 == 64`; that true result remains outside the current cross-width constant fragment.
Other widths, signed shifts, casts, and bitwise operations remain outside this slice.
