# R-042 same-width unsigned quotient slice

## Source and strict products

- Source commit: `c87fc1b9c186a40bf22cc52b55e5b6ac5040943b`
- Source tree: `43bc34bd11ff5db911be2365ecb64931a5a605153eb0a2665f6ecea49dc6974f`
- Build mode: strict Stage1 O2, target `arm64-apple-darwin27.0.0`
- Stage1 executable SHA-256: `f77278c716dea7f3dba8f4fcbcf76ecc473426ab3f163c95fea4e358f6337653`
- Runtime object SHA-256: `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`
- `build/elisa-proof` SHA-256: `66a85efab7b922ba2be6f493ca1d98adf45458cff72effd3f4f44b4a6ae14811`
- `build/elisa-proof-replay` SHA-256: `97dc284f9210e60609f3c1652acee4c8730f2b5a46412932822f83a081893b6c`

The proof producer's `proof_unsigned_quotient_upper_goal` checks that the quotient and dividend
have the same nonzero unsigned width, requires a witnessed scalar dividend, checks the divisor's
width independently, and proves the divisor positive before accepting `q <= x` / `x >= q`.
The portable kernel has a separate `proof_kernel_replay_unsigned_quotient_upper_goal` that checks
the term shape, typed widths, scalar witness, and positive divisor fact directly from the proof
nodes and facts. This is not delegated to producer trust.

## Focused evidence

Commands, each run against the proof product above:

```sh
ELISA_PROOF_BIN=build/elisa-proof python3 scripts/test_unsigned_division_bounds.py
ELISA_PROOF_BIN=build/elisa-proof python3 scripts/test_unsigned_remainder_range.py
ELISA_PROOF_BIN=build/elisa-proof python3 scripts/test_monotone_orders.py
```

All passed. The quotient report had zero semantic errors, zero replay gaps, and equal positive
certificate and replay counts. Three positive cases proved: variable same-width `u32` divisor with
`divisor >= 1`, positive literal `7` for a `u16` dividend, and high-bit-capable same-width `u64`
with `divisor > 0`. Five negative controls remained open: mismatched divisor width, unconstrained
zero divisor, unsigned addition that may wrap, an unrelated ceiling, and a signed negative quotient.
The remainder and monotone-order focused regressions also passed.

## Scope limits

This validates only `unsigned x / d <= x` for witnessed same-width unsigned scalar terms and a
proved positive same-width divisor. It does not establish the complete width/sign matrix, casts,
remainder semantics, shifts, bitwise operations, target-sized types, or the overall R-042 gate.
