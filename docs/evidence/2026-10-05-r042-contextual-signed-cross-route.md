# R-042 contextual signed arithmetic cross-route slice

Commit `23e3bccb` keeps explicit literal suffix metadata from serving as a fixed-width type
witness. This follow-up adds positive cases whose signed `i8` context comes from source function
signatures and bounds, with all arithmetic constants written without suffixes.

## Coverage

The regression in `scripts/tests/test_machine_integer_cross_route.py` checks:

- Source execution: `value: i8 -> i8` computes `126 + 1 == 127`, and bounded `i8` multiplication
  proves `value * value >= 0` for `-2 <= value <= 2`. At runtime, `10 * 10 == 100` exercises the
  same signed multiplication without overflow. The unsuffixed source expression
  `255u8 + 1u8 == 0u8` remains false.
- Source import and proof production: the contextual addition and multiplication postconditions
  prove and every accepted certificate replays; the suffix-only wrapping assertion stays
  unproved. Replay reports zero gaps.
- `decide`: contextual proofs are accepted and replayed; the suffix-only wrap claim is refused.
- Portable package export and replay: both contextual signed theorems and the safe suffix-spelled
  boundary theorem are exported and independently replayed.
- The existing exhaustive typed-u8 add/sub fixture still passes.

Validation command:

```sh
python3 scripts/tests/test_machine_integer_cross_route.py
```

It passed with pair generation `cb8f7d008dee43b1b21b7a160be9e1f7`, Stage1 revision
`7b27fa312c5af923f044f6ee0e5e1de4f811f595`, proof binary SHA-256
`8130cf05bbe5928902c1f51ea8ac00dd0b47b1ea86e715d842913e941427297b`, replay binary SHA-256
`c8713e6314408c1c2ee21d4e104a1d35244c7ff1a31f57576c4808dc1d75949a`, and runtime object SHA-256
`b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`.

## Unsupported or untested shapes

- A typed local assignment followed by a proof about that local is not established by this slice.
  The first probe (`square: i8 = value * value; proof square >= 0`) was refused by the producer
  with `wrap-guard-goal`; it was replaced by the bounded signed return postcondition above.
- Signed multiplication overflow is not tested as a proof claim or given an interpretation here.
  The initial runtime probe `12 * 12` in `i8` trapped, so the passing execution uses an in-range
  product.
- Signed division, remainder and shifts are not part of this cross-route regression. Their
  individual boundary behavior, broader mixed operation combinations, and cross-route parity
  remain open.
- Other widths, signedness-changing casts, bitwise operations, and the full operation-by-width
  matrix remain outside this result.

This closes only the bounded `i8` addition/multiplication contextual-evidence slice. It does not
change the suffix-only refusal or close R-042.
