# R-011 P-01 sentinel corpus follow-up (2026-10-05)

Commit `1b20400d` pins three additional semantic-shape fixtures in
`scripts/p01_sentinels.json` and registers them in `scripts/p01_baseline.py`:

| Sentinel | Source size | Source SHA-256 | Expected result |
| --- | ---: | --- | --- |
| `unsigned_boundary_refusal` | 407 bytes | `9f3a5b2ea7fb0ad2efcca161ae2e0481d4e169de4fbab64dadf69ae3be64fb45` | exit 1, `failed` |
| `quantifier_success` | 480 bytes | `1ac3c5e4f2a1b09586396a02cd2a19b9a28b4c766d50b080075b233aeb2bd655` | exit 0, `proved` |
| `region_lending_success` | 1,364 bytes | `924c11f3cea69f511366b77a7c47d9db0d005f6b977fb8c5a707bcf7916f13df` | exit 0, `proved` |

The manifest check passed with `python3 scripts/test_p01_baseline.py`. Each source was also run
with `elisa-proof --json` from published generation `5bc66d893a434871bdffeb79cdbd6960`; each
result matched the sentinel and reported zero replay gaps. The refusal had 4/4 certificates
replayed; the quantifier and region-lending successes each had 10/10 replayed.

## Product identity

- Pair generation: `5bc66d893a434871bdffeb79cdbd6960`.
- Proof binary SHA-256: `b3d2ebefe0c9e8da8e4f454476991ca737f01fe2582c44b91d1af6473f25a501`.
- Replay binary SHA-256: `154cd6d58d87a1819b926eacd7d28522d4ac4d7ed4a6e03547ad523076826cc1`.
- Proof source commit: `3ebb360598c3299820c9386f2ceb1844bd6dc1c6`; `source_dirty=true`, tree SHA-256
  `8769b1f76a1d78ee2d88ef075a1b9b7a70f1e3da24e6665d326bda0727ae646d`.
- Frontend revision/tree: `7b27fa312c5af923f044f6ee0e5e1de4f811f595` /
  `ab8926f6080a13d21b06606af251e6f0027c2db5`.
- Stage1 product SHA-256: `3e23836002e5b6035d0819367d0758463409d71fa8f38159f1c7a48c1222437f`;
  manifest stage1 revision `7b27fa31`.
- Runtime SHA-256: `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`.
- Target/options: `arm64-apple-darwin27.0.0`, strict O2.

The source tree was dirty when this product was built, and it predates the currently integrated
proof commits. This is a focused expected-outcome check, not a current-HEAD validation or a paired
performance result. The direct rerun used a 20-second subprocess wall timeout per fixture; it did
not impose separate CPU, RSS or output-size limits. The wider P1.1 shape list and seven-round P1.8
baseline remain open.
