# P1 paired benchmark calibration: symbolic quantified contract

This is the first real, provenance-validated paired measurement in the P1 performance-truth
milestone. It benchmarks the complete user workflow for a quantified contract: proof report,
portable package export, and independent kernel replay. The machine-readable samples and embedded
build manifests are in
[`2026-10-06-p1-symbolic-quantifier-same-product.json`](2026-10-06-p1-symbolic-quantifier-same-product.json).

## Design and interpretation

Both arms deliberately use the same immutable proof and replay binaries. This is a repeatability
calibration of the paired-measurement path, not an optimization experiment. It reports no speedup
and does not compare the current dirty main worktree against another revision. Seven measured pairs
were collected after one warm-up pair, alternating arm order. Every proof, package and replay
semantic projection matched across arms and rounds.

The exact source snapshot is clean proof HEAD `414e569369fd8a3cc8b0fc6afba03475291e23a4`, with
`src` tree SHA-256 `558d7e9f7e09be3d3ab76bd05b78babd2b666e808223d38e4144294a26e04a9e`. The build used
Stage1 release `7b27fa31` and frontend revision
`7b27fa312c5af923f044f6ee0e5e1de4f811f595` / tree
`ab8926f6080a13d21b06606af251e6f0027c2db5`; compiler product/executable SHA-256
`3e23836002e5b6035dba43185ea84a9ab5358707c1ee4148c4752cacb2f41a70`; runtime object SHA-256
`b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`; profiler hooks SHA-256
`ff7eb87b67bbc470ee95c320bb95ff125300f1edc8c2e67585d282e27e0e9711`; strict O2 target
`arm64-apple-darwin27.0.0`. Proof binary SHA-256 is
`02f7dbe5e20a7e389e683b0384f5c7141bd1cc12bfe54651e4279474f7c3412f`; replay binary SHA-256 is
`853742b94f85ba9b884b50a094efd8f4b647d56a6268a31ef653af7f4f90081d`.
The installed Stage1 manifest does not report its full source-checkout revision
(`compiler.source_revision` is null); the recorded Stage1 release revision and executable/product
digests identify the exact compiler used. The manifest reports `compiler.source_dirty: false`.

## Semantic result and measured cost

The fixture proved all 81 obligations across 20 declarations. All 81 generated certificates replayed
in the proof report, with zero gaps; the package exported 81 theorems and standalone replay checked
all 81 with zero un-replayed theorems. The proof report listed zero trusted assumptions and 431
trusted boundary facts; its complete trust projection is retained by digest in the JSON evidence.
Obligation inventory, proof trust, package theorem inventory, replay status,
and replay trust were compared explicitly and matched between arms.

| Workflow phase | Wall p50 / p95 (s) | User CPU p50 (s) | System CPU p50 (s) | Peak RSS (KiB) |
| --- | ---: | ---: | ---: | ---: |
| Proof report | 0.543211 / 0.657601 | 0.531612 | 0.009170 | 59,632 |
| Package export | 0.574435 / 0.829272 | 0.556330 | 0.010566 | 60,656 |
| Standalone replay | 0.193600 / 0.237767 | 0.187572 | 0.003590 | 8,112 |

Each row has seven retained raw paired samples in the JSON. Peak RSS is the maximum observed across
the seven processes in that phase. Host: macOS Darwin, arm64, Python 3.9.6. These are machine- and
snapshot-specific measurements, not service-level budgets or a speedup claim.

## Reproduction and validation

Build the pinned clean source snapshot with the installed Stage1 product, then pass its exact `src`
tree and the emitted proof/replay generation to the paired runner. The evidence JSON records the
actual generation and full manifest bytes. Validate a saved report with:

```sh
python3 scripts/validate_perf_luna_evidence.py \
  docs/evidence/2026-10-06-p1-symbolic-quantifier-same-product.json
```

Validation passed: one fixture, seven rounds, exact manifest/product provenance, complete paired
samples, equal obligation/trust/replay outcomes, and no speedup assertion. The 37 focused benchmark,
evidence-validator and provenance tests, benchmark process/provenance self-test, repository source
length check, and `git diff --check` also passed.

The dirty working source tree was intentionally not benchmarked: a fresh Stage1 O2 build of that
state failed with `backend generated invalid LLVM IR; refusing to optimize or emit`. Resolving that
compiler/proof-source build issue and measuring the subsequent current-source product remain open;
this calibration does not imply that the dirty tree is buildable or performance-qualified.
