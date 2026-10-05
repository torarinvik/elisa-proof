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

These tests check fail-closed behavior at the available product identities. The unsigned-sort
gap needs separate producer/replay follow-up. A fresh matched build from the audited branch head,
the broader R-003 inventory, and the full R-042 integer matrix remain open.
