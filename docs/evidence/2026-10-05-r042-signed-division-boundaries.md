# R-042 signed division and remainder boundaries

## Source and products

- Proof source commit: `c87fc1b9c186a40bf22cc52b55e5b6ac5040943b`
- Proof source tree: `43bc34bd11ff5db911be2365ecb64931a5a605153eb0a2665f6ecea49dc6974f`
- Build mode: strict Stage1 O2, target `arm64-apple-darwin27.0.0`
- Stage1 executable SHA-256: `f77278c716dea7f3dba8f4fcbcf76ecc473426ab3f163c95fea4e358f6337653`
- Runtime object SHA-256: `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`
- Proof product SHA-256: `66a85efab7b922ba2be6f493ca1d98adf45458cff72effd3f4f44b4a6ae14811`
- Portable replay product SHA-256: `97dc284f9210e60609f3c1652acee4c8730f2b5a46412932822f83a081893b6c`

## Audit and focused test

The source producer's `proof_div_safe` and `proof_mod_safe` refuse divisor zero and the `i64`
minimum with divisor `-1`. The independent replay helpers `proof_kernel_replay_div_safe` and
`proof_kernel_replay_mod_safe` have the same guards. The producer and replay interval evaluators
also agree: signed quotient intervals with positive divisors are admitted; modulo intervals refuse
unknown, zero, and `-1` divisors because the range alone does not exclude `MIN_I64 % -1`.

`examples/signed_division_boundaries.elisa` and
`scripts/test_signed_division_boundaries.py` exercise the boundary through generated certificates
and independent replay. Safe bounded division by `-1` and remainder by `-2` prove. The exact
`MIN_I64 / -1` and `MIN_I64 % -1` postconditions remain unproven. Division by zero and modulo by
zero each produce their expected diagnostics at lines 31 and 35, and their postconditions remain
unproven. The JSON report has zero semantic errors, zero replay gaps, and matching nonzero
certificate/replay counts.

Command:

```sh
ELISA_PROOF_BIN=build/elisa-proof python3 scripts/test_signed_division_boundaries.py
```

Result: passed. The new test is included in `scripts/test.d/01-setup-and-python-suites.sh`.

No producer/replay mismatch was found, so no arithmetic implementation change was justified.
This evidence covers only these `i64` signed division/remainder boundaries; width-specific minima,
other signs and widths, other operations, and the complete R-042 matrix remain open.
