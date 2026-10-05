# R-015 string-budget consumer generation pin

The string-budget regression now imports `BINARY` and `REPLAY` from
`scripts/portable_replay_support.py`. The consumer adds `scripts/` to Python's
module path before importing the shared helper. Product resolution happens once
for both executables; an explicit override must still provide both
`ELISA_PROOF_BIN` and `ELISA_PROOF_REPLAY_BIN`.

Focused run:

```sh
ELISA_PROOF_GENERATION_ROOT=/private/tmp/elisa-r006-count-cap/build/elisa-proof-generations \
  python3 scripts/tests/test_portable_package_string_budget.py
```

Result: passed; printed `portable package aggregate string budget: over-budget input refused`.
The resolver selected pair generation `637b88407b6642da9168017be011da8d`:

- `elisa-proof` SHA-256: `9300837426ae905c623d294f24fd14d7b419dc848dcb7e6c1474d9e102311507`
- `elisa-proof-replay` SHA-256: `1eb870ab4cf6c63805d109bf0eff636ea3ff2ba0281f2130de398654181293ac`

This worktree had no local published `build/elisa-proof-generations/CURRENT`,
so the run used the valid pair generation from `/private/tmp/elisa-r006-count-cap`.
