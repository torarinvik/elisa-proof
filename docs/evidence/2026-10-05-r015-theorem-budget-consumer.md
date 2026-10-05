# R-015 theorem-budget consumer generation pin

`scripts/tests/test_portable_package_theorem_budget.py` now imports the proof and
replay executables from `scripts/portable_replay_support.py`. The helper resolves
both products from one published generation, or accepts a complete explicit pair
through `ELISA_PROOF_BIN` and `ELISA_PROOF_REPLAY_BIN`. The exact-limit and
one-over theorem-count checks remain intact.

Focused validation:

```sh
ELISA_PROOF_GENERATION_ROOT=/private/tmp/elisa-r006-count-cap/build/elisa-proof-generations \
  python3 scripts/tests/test_portable_package_theorem_budget.py
```

Result: passed; the exact 65,536 theorem package replayed and the 65,537 theorem
package was refused before theorem replay.

The resolver selected pair generation `637b88407b6642da9168017be011da8d`:

- `elisa-proof` SHA-256: `9300837426ae905c623d294f24fd14d7b419dc848dcb7e6c1474d9e102311507`
- `elisa-proof-replay` SHA-256: `1eb870ab4cf6c63805d109bf0eff636ea3ff2ba0281f2130de398654181293ac`

This worktree had no local published `build/elisa-proof-generations/CURRENT`,
so validation used the available published pair under `/private/tmp/elisa-r006-count-cap`.
