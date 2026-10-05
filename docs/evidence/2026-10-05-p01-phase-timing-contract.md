# P-01 phase-timing contract hardening — 2026-10-05

The P-01 runner now validates its observational `phase_timings_seconds` record before accepting
a sample into a complete baseline. It requires exactly the three measured external/harness fields
(`proof_cli_invocation_wall`, `proof_cli_child_cpu`, and `baseline_harness_json_decode`), finite
non-negative durations, and exact agreement between invocation wall/child CPU fields and their
existing top-level measurements. Missing, extra, NaN/infinite, negative, Boolean, or inconsistent
values fail closed. Existing internal phases marked unavailable remain unavailable; this change
does not infer or estimate any internal proof phase.

This is measurement validation only. These durations do not enter proof decisions, certificate
construction, or replay. The P-01 runner does not compare a candidate against a baseline and this
change establishes no speedup.

## Verification and identities

Passed:

- `python3 scripts/test_p01_baseline.py`, including new adversarial checks for missing schema,
  NaN, wall-time mismatch, and child-CPU mismatch.
- `python3 scripts/tests/test_perf_luna_benchmark_hardening.py` (7 tests).
- `python3 scripts/perf_luna_benchmark.py --self-test`.

The P-01 semantic fixtures exercised by the focused contract test are:

- `branch_join`: SHA-256 `bc7bcbfa81ef187405e5e0ac3b3348d800b4ef4787848bad959760eb03eb190f`.
- `rejected_branch_join`: SHA-256 `42ee1d1323fc8beefe6b691bc231f2a566c56a66db023399c88ee9474680705f`.
- `proof_kernel_core`: SHA-256 `6e78ff9e07900b2d97da8044dc1cae855f84dd30fb8ef5348c9868b72335e590`.

No real proof-product timing run was used as evidence for this change. The inspected local product
was `build/elisa-proof`, SHA-256
`2fcbce64b6fe2e2f0a25b227f7436e6a68169ae0d15daa4163ef303b906cbf5d`, with manifest SHA-256
`4956091d9140cd6d57fc7a7d8b2df366c6d26263e62f2eb03189bbec82a3950b` and build identity
`9a62294da00632383ec405a53f1c91aad7b484dfd2c05e6c535f4e5eeaf81cdf`. The product hash matches
the manifest, but the manifest marks compiler sources dirty (`source_dirty: true`), so this binary
is not accepted as a clean reproducibility/performance product. A clean compiler-source snapshot
and a fresh matched product pair remain necessary for real baseline or paired speedup claims.
