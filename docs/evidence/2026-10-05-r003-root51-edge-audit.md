# R-003 root 51 signed unit-shift edge audit

This audit adds focused source controls around the existing bounded signed implication
`(at + 1) < count ==> at < (count - 1)`. The existing bounded positive fixture remains
unchanged. The checks do not generalize or close conditional arithmetic.

## Products and commands

The available matched strict O2 pair is the immutable pair recorded in
[`root 51 signed unit-shift evidence`](2026-10-05-r003-root51-signed-unit-shift.md):

| Product | Build identity | SHA-256 |
| --- | --- | --- |
| Proof CLI | `cac084fdc0c8ccd34b68cf720680c146f71b2c35a2e3529cdb1ad96a6d0fb78d` | `733b74c78e3c6772c1c617ab4cce1ab7a21c4e747877e0a656b86fc8fcefae5c` |
| Portable replay | `0ade2ed9e21b4102cc9d97ef992d58b653a1b4f8aa36e8711e3cac3961868efa` | `d9f86117198f2c660c2a9989ffa434da325e73aa4cd7522d329e81407d962017` |

The products were built strict O2 for `arm64-apple-darwin27.0.0`, from proof revision
`fcbc4b959552aa3984ad10a234aacaf105a2079e` and frontend revision
`bc8def2eadf41dd088adce22b4d3d9e74aadfee9`. The branch audited here starts at `a43e31bf`;
the matching products were available and reused, but were not freshly rebuilt from that later
HEAD. This distinction limits the result to the recorded implementation snapshot.

The focused command passed:

```sh
ELISA_PROOF_BIN=/private/tmp/elisa-r003-root51-final.kXDvQ9/source/build/elisa-proof \
  python3 scripts/test_conditional_ensure_replay_gap.py
```

The positive fixture also exported two package theorems and the matched portable replayer
replayed both (`replayed: 2`, `not_replayed: 0`). The source CLI reports the positive fixture
proved with two certificates, two replays, and zero gaps. `Slide.inner` roots 48 and 51 both
replay in the same focused command.

## Controls

| Control | Result |
| --- | --- |
| `minimal_conditional_signed_unit_shift_near_max_refusal.elisa` | Fixed `at` and `count` to signed i64 max; ensure refused, one certificate replayed, zero gaps. |
| `minimal_conditional_signed_unit_shift_near_min_refusal.elisa` | Fixed both values to signed i64 min; ensure refused, one certificate replayed, zero gaps. |
| `minimal_conditional_signed_unit_shift_wrong_width_refusal.elisa` | Mixed i32/i64 comparison; ensure refused, one certificate replayed, zero gaps. |
| `minimal_conditional_signed_unit_shift_wrong_sort_refusal.elisa` | Unsigned u64 mutation is not admitted. Producer reports `proved_with_replay_gaps` (2 certificates, 1 replay, 1 gap); the kernel rejects its goal certificate. This exposes an existing producer/replay disagreement and is not a clean proof-level refusal. |
| `minimal_conditional_signed_unit_shift_wrong_bound_refusal.elisa` | Requests `at < count - 2`; ensure refused with complete replay. |
| `minimal_conditional_signed_unit_shift_missing_conjunct_refusal.elisa` | Requests a result requiring an unrelated `at >= 1` condition; ensure refused with complete replay. |
| `minimal_conditional_signed_unit_shift_missing_premise_refusal.elisa` | Removes the source premise `at < count`; body/ensure remains unproved, with zero replay gaps. |
| `minimal_conditional_overflow_refusal.elisa` | Unbounded source inputs; ensure refused with complete replay. |

These initial checks used an earlier matching product pair and exposed the unsigned producer/replay
gap. Follow-up remediation and validation against a fresh pair from this branch are recorded below.

## Producer/replay guard agreement follow-up

Commit `f915072c2b3aab191ef2bad7ffe183e8a563b6d5` adds a narrow source-producer guard for the
exact fallback shape recognized by the kernel's signed unit-shift rule. If that shape carries an
unsigned width witness, the producer records the goal as unproved before its generic mathematical
integer search can emit a goal certificate. The existing kernel rule remains signed-only. Signed
instances continue through the range-checked source and replay paths.

A fresh matched strict O2 pair was built from a clean worktree at proof HEAD
`6753e0df2dc2128e380b010b0b9b5953776418b1`, source tree
`51d6d770b5212386b9b9f73fe70d0b13025793071139da4aa52a133a320c2cef`, and frontend revision
`7b27fa312c5af923f044f6ee0e5e1de4f811f595` / tree
`ab8926f6080a13d21b06606af251e6f0027c2db5`. Both products were built strict O2 with the clean
Stage1 compiler at `bc8def2eadf41dd088adce22b4d3d9e74aadfee9`; their shared pair generation is
`55467af5b6364627a786bbbd47d393b1`.

| Product | Build identity | SHA-256 |
| --- | --- | --- |
| Proof CLI | `dc80e3c7aae30670c6de595b975a64dcb133209aa7ce2afadf808bc3004772b1` | `ff098da001445ff7d257ff865e58bf274382587b78fd914c712c4f7ffed7034b` |
| Portable replay | `2323aa202d3e38f0085f020cda64740aaaa441daf5c63d3a78ff2405612e737e` | `bc0a1cbff0dc419833d21e875d1892cd24c3ce6a41b43e22fd0afbb748b81c0c` |

Validation against these products:

- `ELISA_PROOF_BIN="$PWD/build/elisa-proof" ELISA_PROOF_REPLAY_BIN="$PWD/build/elisa-proof-replay" python3 scripts/test_conditional_ensure_replay_gap.py` passed. The positive source fixture proved with 2/2 internal replays; `Slide.inner` roots 48 and 51 both replay; every negative control, including u64, failed with zero gaps and complete replay.
- Exporting the positive fixture with `build/elisa-proof --package` and replaying it with `build/elisa-proof-replay` returned `replayed`, 2/2 theorems, zero not-replayed.
- The u64 control now reports `failed`, one certificate replayed, zero gaps, and declaration reason `body-unverified`; its unsupported goal reports `not_certified` with no certificate id. Signed near-min/max and wrong-width controls remain ordinary unproved obligations with complete replay.
- `git diff --check` passed before the evidence update; the evidence-only update is whitespace-checked before commit.

This closes the producer/replay disagreement for this exact unsigned fallback shape only. The
broader R-003 inventory, generalized conditional replay, and full R-042 integer matrix remain open.
