# R-015 linear certificate consumer generation pin

`scripts/test_linear_certificates.py` now imports `BINARY` and `REPLAY` from
`portable_replay_support`, matching the shared resolver used by the portable replay consumer.
This resolves the proof producer and replay kernel as one pair before the script starts, and the
shared resolver rejects a partial `ELISA_PROOF_BIN` / `ELISA_PROOF_REPLAY_BIN` override.

Validation on 2026-10-05:

- `python3 scripts/tests/test_linear_certificate_consumer_resolution.py` passed.
- `scripts/test_linear_certificates.py` passed with both executables from the same
  `main-proof-gains-validation/build` output: `linear certificates: search, replay, forgeries
  and budgets agree`.

The repository checkout used for this change had no published `build/elisa-proof-generations`
directory, so the focused run used the explicit paired override above rather than a published
immutable generation. The shared consumer resolver remains responsible for selecting a published
generation in normal use.
