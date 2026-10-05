# R-011 paired-measurement guard — 2026-10-05

This update records a guardrail and harness test, not a performance result. The paired benchmark
must refuse to publish timings unless each proof/replay pair has matching build provenance and
the baseline/candidate share a toolchain. A refused run is not evidence that one product is
faster or slower.

## Benchmark behavior added

`scripts/perf_luna_benchmark.py` now validates each manifest sidecar digest and executable
digest, compares the proof and replay source tree, frontend, compiler, runtime, target,
optimization and flags, and compares baseline/candidate toolchain identity. It snapshots all
input binaries and manifest files, rereads the manifests against the measured binaries before
starting, and checks that no input changed before emitting a report. The second read closes a
window where a product could be replaced after its manifest was parsed but before its file hash
was recorded.

The default measurement protocol is seven alternating baseline/candidate rounds after one
warm-up round. Reports expose median and nearest-rank p95 wall time, median child user/system CPU,
and maximum observed RSS. Exact stdout/stderr agreement remains a required correctness check.
The self-test and `scripts/tests/test_perf_luna_benchmark.py` passed (15 focused unit tests).
These tests validate harness behavior and synthetic manifests; they are not a timing baseline.

## P-01 subprocess reaping correction

Running `scripts/test_p01_baseline.py` exposed a real race in its output/RSS limit path. With
`wait4` enabled, the fallback `Popen.kill()` could call `poll()` and reap the child before the
subsequent `wait4`, producing `ChildProcessError: [Errno 10] No child processes`. The fallback
now uses `os.kill` so `wait4` remains the reaper; if even direct signaling is denied, it uses the
Popen path and deliberately avoids a second `wait4`. The focused P-01 test passed five
consecutive runs after the correction (`c4798474`).

## Current product mismatch caught

At the time of this check, the proof and replay executables each had valid manifest checksums
and matching binary hashes, but they did not describe one source snapshot:

| Product | Binary SHA-256 | Proof revision | Proof source-tree SHA-256 |
| --- | --- | --- | --- |
| `build/elisa-proof` | `12c6347093b8cd95d77fc2d54eb843ca605bc166165b1b7c2c281699f35f7a54` | `ecf2263f375c87e6c871f391f02f0bd9c40dc7f3` | `8ad03c7528ac42631e0e9da5eb1f21c41f139508aa9fccf6b21d7673cad35715` |
| `build/elisa-proof-replay` | `74942b88d0cf9432dd770d57fb98c0254fae01969acc94d44c9676b071996ac9` | `fe396b2bedc7ae7029be5745c38011c4d3ae0f35` | `0de5d950de444ca02e82bc1d2013a0add559be8549ed4100f795432b0c62f35b` |

Both manifests identify the same clean Stage1 compiler source revision `e4a16fd24dacb2db54b7cc3aff2d19312ff2edf7`, compiler product SHA-256
`7bcb8590304617b61d1462f6b40c0bff006e3fbe537489d1ce867766e918bd39`, and pinned frontend revision
`7b27fa312c5af923f044f6ee0e5e1de4f811f595`. The difference is in the proof-source snapshot;
the available manifests do not establish why these products were built from different snapshots.

The benchmark preflight was run with the same proof/replay pair in both comparison arms and
exited 1 before invoking a verifier, reporting:
`baseline proof/replay products have incompatible build provenance: ['proof.source_tree_sha256']`.
No benchmark timing was emitted. This demonstrates the refusal path; it does not explain how the
pair became mixed.

## Remaining R-011 work

- Rebuild proof and replay together from one committed, immutable proof source snapshot and save
  the exact manifests with the seven-round report.
- Supply a separately built baseline and candidate from the same Stage1 compiler, frontend,
  target and options; compare proof and replay outputs before reporting speedups.
- Add the plan's missing field-equality, composed-call, resource-heavy, fact-growth, cold/no-op/edit
  and portable-replay workload classes. The current six-fixture harness does not meet this matrix.
- Report proof bytes, obligation counts and replay counts alongside time/CPU/RSS, and add end-to-end
  phase/work counters only where their ownership and denominator are explicit.
- Treat timeouts, memory stops and interrupted measurements as censored outcomes, never as fast
  runs or successful verification.

R-011 remains open; no optimization claim is made.
