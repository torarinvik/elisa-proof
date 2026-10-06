# P0 unsigned tactic goal-binding audit

## Finding

The full test matrix logged three failures as `unsound unsigned tactic proof was accepted`:
`rejected_u64_max_decide`, `rejected_u8_overflow_decide`, and
`rejected_u8_overflow_simp`. Inspection showed the checked-in tactic scripts were pinned to old
goal fingerprints. The tactic runner rejected each script at source-goal binding before executing
the tactic, so the matrix's failure text did not establish that an arithmetic action was accepted.

The exact source is 1,677 bytes, with source fingerprint `3309411913`. Querying the imported goals
from the manifested proof binary gave:

| Control | Goal id | Stale fingerprint | Current goal fingerprint |
| --- | ---: | ---: | ---: |
| `rejected_u64_max_decide` | 7 | 3959704679 | 515359733 |
| `rejected_u8_overflow_decide` | 13 | 3492578551 | 1229197265 |
| `rejected_u8_overflow_simp` | 13 | 3492578551 | 1229197265 |

## Correction and validation

Updated the three tactic fixtures and both test expectations to the current source-bound goal
fingerprints. Strengthened `scripts/test_safe_constant_replay.py` to require a matching source-goal
binding, exactly one attempted action, zero accepted actions, and the specific refusal caused by
the tactic result contradicting the script's expected acceptance. This prevents a stale fingerprint
or malformed script from satisfying the negative control.

Validation passed:

- `ELISA_PROOF_BIN="$PWD/build/elisa-proof" python3 scripts/test_safe_constant_replay.py`
- The test verifies the positive small-constant simplification still replays and all three
  source-bound unsigned false-claim tactics are refused.
- `git diff --check`

The proof product manifest identifies strict Stage1/O2, build identity
`651e854e4bb734744840b746fd65c851dcfa14322d1405b4c64656f35682c66c`, proof binary SHA-256
`8c0880bf4bdfa02e019016f61649f7fc61d3506f9a05d1799bcd7e4b968cf03b`, and proof source-tree SHA-256
`0fecb41651fe5c860d21de10c9241b4440cbe515fbf13682a5e7f998cde81748`. Its Stage1 product SHA-256 is
`65a9308c53b510365aa69644a0bcaa9a071ea2006683dad6bf2ec12fc394f6b3`, from compiler revision
`6b475d894331f0a81c3112167ef7fcf5c642a424`; runtime object SHA-256 is
`b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`.

This result closes only the three tested tactic refusals. It does not establish complete fixed-width
arithmetic semantics across other operations, widths, repair, or portable replay; those remain open
under R-042/P0.3b.
