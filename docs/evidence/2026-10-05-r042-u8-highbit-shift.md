# R-042 true u8 high-bit right-shift slice

## Source and product identity

- Source commit: `8833a517c8601a20db89d38deba6f726730ba732`
- Source tree SHA-256: `af0cf33df7eafaea085d5a39caeee7a9da1b7d4d727cbf8dd004617293e3ef75`
- Build identity: `19cb1a9c4586ab5b009f3d3dbb7d313d2b56f4e52aec40bf1b910315e8150052`
- Build mode and target: strict Stage1 O2, `arm64-apple-darwin27.0.0`
- Stage1 wrapper SHA-256: `96eca8200bb268ea5cc1635a66d6b0da0cd85611331319c3227362d9421c2947`
- Stage1 compiler product SHA-256: `3e23836002e5b6035dba43185ea84a9ab5358707c1ee4148c4752cacb2f41a70`
- Pinned frontend revision: `7b27fa312c5af923f044f6ee0e5e1de4f811f595`
- Runtime object SHA-256: `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`
- `build/elisa-proof` SHA-256: `407818ad612aefb145b735f6719036f1057ee931ded97bb5b65269f28add7085`
- Portable replay product: not built for this focused slice; the proof product's independent kernel certificate replay was exercised.

## Focused commands and result

The proof product was refreshed with:

```sh
ELISA_COMPILER_BIN="/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/Elisa-compiler/bin/elisac-stage1" \
ELISA_COMPILER_SRC="/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/Elisa-compiler" \
bash scripts/build.sh
```

The build manifest records commit `8833a517`, `source_dirty=false`, and the identities above.
The focused checks then passed:

```sh
python3 scripts/test_typed_unsigned_shift.py
python3 scripts/test_typed_goal_identity.py
git diff --check
```

`examples/replay_typed_unsigned_shift.elisa` proves `128u8 >> 1u8 == 64u8`. Both the asserted
proof step and enclosing proof goal have replayed certificates; the report has zero semantic
errors, zero replay gaps, and no trusted assumptions. The regression also checks that
`128u8 >> 8u8 == 0u8` remains unproved with no replay gap. This count equals the value width, so
the bounded producer and independent replay evaluator both refuse it. The fixture uses explicit
`u8` literal suffixes, which produce deprecation warnings but no semantic errors.

## Scope

The rule accepts only closed, same-sort unsigned operands and only shift counts below the value
width. This validates one high-bit `u8` right shift and its independent replay path; it does not
complete R-042 or establish the other widths, signed shifts, casts, bitwise operations, portable
replay product parity, or runtime behavior for oversized shifts.
