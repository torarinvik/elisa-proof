# P-01 proof-kernel dogfood baseline

This run adds the proof kernel's own source file to the pinned P-01 corpus. It is a real proof
module, not an example wrapper: the verifier reports 37/37 obligations proven, 37/37 certificates
replayed, zero replay gaps, and zero semantic errors.

## Identity and method

- Fixture: `src/proof/kernel_core.elisa`, SHA-256
  `a2ca3f4dce07d7caa327a1498800bc79bd0debd382fbf0cb15172522d70331ca` (14,237 bytes).
- Verifier binary SHA-256: `7853d569d72847587dcdbd184b85a16b8892c16c422bdd63e6d4ea3f2396a914`.
- Proof build identity: `2560ad4d7212113d3f79bb69e2d1808049aee4bf01be524ceaf6b954adde31e4`; proof source-tree SHA-256 `8a889ae0c6293355f1e097e2d4913db5e28380ed3fd3f2c12ba7e3dbb4b46a4f`.
- Frontend revision `7b27fa312c5af923f044f6ee0e5e1de4f811f595`; frontend tree SHA-256
  `ab8926f6080a13d21b06606af251e6f0027c2db5`.
- Compiler source revision `72a752820ab581d46bb17b3fb7158ba3879a16e3`; compiler product SHA-256
  `fc535ef132be340c9f50cc6d3f789178fabf049f58e29663dd3bf13c480aa5e2`.
- Runtime object SHA-256 `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`.
- Strict O2, target `arm64-apple-darwin27.0.0`; macOS 27.0.1 arm64; one verifier process at a time.
- Seven repetitions per scenario after one warm-up. Each sample was a fresh CLI process. `warm`
  means a repeated fresh process after warm-up, and `no_op` means the same source plus a comment;
  neither is a persistent report-cache hit.

## Measurements

| Scenario | Median wall | p95 wall | Median child CPU | p95 child CPU | Maximum RSS |
| --- | ---: | ---: | ---: | ---: | ---: |
| Cold | 68.233 ms | 69.074 ms | 39.339 ms | 40.641 ms | 20,272 KiB |
| Warm repeat | 68.108 ms | 111.228 ms | 39.986 ms | 51.780 ms | 20,272 KiB |
| Comment-only edit | 67.978 ms | 68.352 ms | 39.806 ms | 41.490 ms | 20,272 KiB |

All 21 measured reports were complete and had identical 37/37 replay coverage with zero gaps.
This is a correctness and cost baseline, not evidence of incremental reuse or an internal phase
timing breakdown. Internal import, parse, semantic, proof-search, replay and report timings remain
unavailable.
