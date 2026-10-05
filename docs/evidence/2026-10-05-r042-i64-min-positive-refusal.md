# R-042 near-I64_MIN strict-lower-bound shift refusal

## Scope and reproduced gap

The durable positive premise `count > I64_MIN` should establish that `count - 1` is in range. The existing signed conditional shift kernel does not currently derive that interval through a named constant. Replaying the fixture against the pre-change proof binary (SHA-256 `12c6347093b8cd95d77fc2d54eb843ca605bc166165b1b7c2c281699f35f7a54`) reproduced the recorded failure mode: `proved_with_replay_gaps`, 2 certificates, 1 replay, 1 gap. The recorded baseline edge evidence in `2026-10-05-r042-signed-shift-i64-edges.md` also reports this gap.

The producer now recognizes the exact conditional unit-shift shape when its source facts contain the matching `count > I64_MIN` premise. It records the goal attempt as unproven before certificate search. The independent replay kernel therefore receives no unsupported goal certificate. This is a conservative refusal; support for deriving the named-constant interval remains open.

## Fixture and result

Fixture: `test/repro/minimal_conditional_signed_unit_shift_near_min_positive_refusal.elisa`.

On the rebuilt proof executable, the fixture returns `failed` with `verification_reason: body-unverified`, an `ensure-unproven` finding, no goal certificate, and replay counts 1 certificate / 1 replay / 0 gaps. The sole certificate is the unrelated resource-safety certificate. Existing near-maximum and ordinary signed shift positives still prove and replay; existing overflow, wrong-width, wrong-sort, wrong-bound, and missing-premise controls remain refused.

Focused validation passed:

- `scripts/test_conditional_ensure_replay_gap.py`
- `scripts/test_portable_replay.py` (16 positive packages and structured/raw mutation suites)

## Matched strict O2 Stage1 products

Built from clean proof source commit `befb162add5c00379361336f624da754ec86a46d` and pinned compiler frontend revision `7b27fa312c5af923f044f6ee0e5e1de4f811f595`; target `arm64-apple-darwin27.0.0`; strict mode; O2.

- Pair generation: `cc25853870aa430c831e8f91cefb1eaa`
- Proof product SHA-256: `ec150ffb6581ff0fcfee35fb6af0f091c8dce33cedf7b1cdfd6948b0d4ee2ba1`
- Proof build identity: `52ba053e570a60a97704059fc3596d87248ee5f1876eec056acb237c7d672808`
- Portable replay product SHA-256: `31a80135ca396d40d386084128e5cc2dfae9c4ee213068838e1bb08586f9b97e`
- Replay build identity: `7100f82963c0a7105332469f7b5ded814bcbe33707cae59f6aa1c15ff960318d`
- Frontend source tree: `ab8926f6080a13d21b06606af251e6f0027c2db5`
- Runtime object SHA-256: `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`

Both products share the same pair generation and report a clean proof source tree. The producer refusal currently keys on the source constant name `I64_MIN`; alternate names or equivalent lower-bound expressions are not covered by this narrow regression. Signed widths other than i64, alternate conditional shapes, and positive near-min replay remain open.
