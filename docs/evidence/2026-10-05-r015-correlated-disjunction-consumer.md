# R-015 correlated-disjunction consumer

`scripts/test_correlated_disjunction.py` now imports both the proof producer and replay
executable from `portable_replay_support`. This pins JSON diagnostics and persisted-package
replay to the same published generation; an explicit executable override is accepted only when
the shared resolver receives both override variables.

## Evidence

- `python3 scripts/tests/test_correlated_disjunction_consumer_resolution.py` passed. The static
  guard requires the shared paired import and rejects direct environment reads or hardcoded
  executable paths.
- `scripts/test_correlated_disjunction.py` passed against validated generation
  `3832e97fbe8c40fd936e53e5c81cfaf0`, selected via the shared resolver using the existing
  checkout's generation root. All four positive obligations replayed, and the stronger and
  unguarded negative cases were refused.
- The worktree has no local `build/elisa-proof-generations/CURRENT`; validation used the matched
  product store from the main checkout. No fresh Stage1 build was run.
