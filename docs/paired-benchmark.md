# Reproducible paired proof/replay benchmarks

`scripts/perf_luna_benchmark.py` runs a bounded baseline/candidate comparison without building
either product. It is intentionally a measurement tool, not a verifier admission path. It will
not report a performance result when product identity, workload identity, proof semantics, trust
roots, or replay behavior cannot be established.

## Required source evidence

Each arm requires the exact `src` directory snapshot used to build its proof and replay binaries,
plus the expected SHA-256 of that tree. The hash algorithm matches `scripts/build_manifest.py`'s
`tree_digest`: sorted directory traversal, relative UTF-8 paths separated by NUL, then each file's
SHA-256 digest. The benchmark independently hashes the supplied directory and requires that value
to match both the command-line expectation and each binary manifest's
`proof.source_tree_sha256`.

The manifest's proof-source dirty marker may be true only because the caller supplied and
verified that exact source tree. Compiler sources must be clean: a proof-source hash cannot
attest unrecorded compiler edits. The benchmark re-hashes the compiler executable, compiler
product, runtime, and profiler hook files named by each product manifest. Missing, replaced,
unmatched, or unverifiable files are a hard refusal.

Example (compute each value from its exact archived build snapshot; never copy a hash from a
different checkout):

```sh
BASE_SRC=/path/to/baseline/snapshot/elisa-proof/src
CANDIDATE_SRC=/path/to/candidate/snapshot/elisa-proof/src
BASE_SHA=$(python3 -c 'import sys; sys.path.insert(0,"scripts"); from perf_build_provenance import source_tree_identity; from pathlib import Path; print(source_tree_identity(Path(sys.argv[1])) )' "$BASE_SRC")
CANDIDATE_SHA=$(python3 -c 'import sys; sys.path.insert(0,"scripts"); from perf_build_provenance import source_tree_identity; from pathlib import Path; print(source_tree_identity(Path(sys.argv[1])) )' "$CANDIDATE_SRC")

python3 scripts/perf_luna_benchmark.py \
  --baseline-proof /path/to/baseline/elisa-proof \
  --baseline-replay /path/to/baseline/elisa-proof-replay \
  --candidate-proof /path/to/candidate/elisa-proof \
  --candidate-replay /path/to/candidate/elisa-proof-replay \
  --baseline-source-root "$BASE_SRC" --baseline-source-sha256 "$BASE_SHA" \
  --candidate-source-root "$CANDIDATE_SRC" --candidate-source-sha256 "$CANDIDATE_SHA" \
  --rounds 7 --warmup-rounds 1 --timeout 120 --output paired-results.json
```

## Focused workflow mode

Use `--fixture` to benchmark one or more reviewed workflows without running the whole corpus.
For example, `symbolic_quantifier` exercises a realistic quantified contract proof, package
export, and independent portable replay. The benchmark retains exact per-phase semantic projection
digests for both arms; `scripts/validate_perf_luna_evidence.py` checks report schema, source and
product identities, shared compiler/frontend/runtime/target provenance, semantic parity, replay
closure, and complete paired samples without rerunning the workload.

Reports retain every measured pair (wall time, user/system CPU, and peak RSS where available), as
well as the aggregate statistics. They embed the exact build-manifest bytes; the offline validator
checks those bytes against manifest identities and cross-checks each manifest against the reported
build context and measured executable hashes:

```sh
python3 scripts/validate_perf_luna_evidence.py paired-results.json
```

For a reproducibility calibration (not a speedup experiment), supply the same immutable proof and
replay products to both arms, select a focused fixture, and use at least seven paired rounds. The
report labels this as a same-product reproducibility benchmark and does not assert speedup. A
candidate-vs-baseline speedup claim still requires genuinely different immutable products and
paired samples; semantic parity alone does not imply a performance improvement.

## Protocol and report

Before timing, each binary pair must have valid manifest checksums and executable identities;
proof/replay must agree on source tree, frontend, compiler stage/revisions/products, runtime,
hooks, target, optimization, compile mode, and exact flags. Baseline and candidate toolchains
must agree; their proof-source hashes may differ, but each must be independently verified as
above. The six benchmark fixtures have pinned source hashes and expected outcomes.

An untimed preflight runs proof, package export, and standalone replay for every selected fixture. It
compares canonical semantic report projections (including declaration and obligation inventory,
trust roots, certificates, and replay), package source/theorem inventory, and replay results.
Any mismatch aborts before timed samples. Timed rounds then alternate baseline-first and
candidate-first ordering, excluding warm-up. Timing summaries use nearest-rank p95 and report
p50, spread/min/max, user/system CPU percentiles, and peak RSS when the host exposes it.
Measurement-only report fields are excluded from semantic equality; semantic fields are not.

Each fixture/phase must retain the same semantic output across all measured samples. A timeout
or watchdog termination is emitted as a structured `status: "censored"` report with
`timing_valid: false` and `speedup: "not-reported"`; it is never converted into a fast sample.
Other integrity or identity failures are hard errors. The process watchdog kills the entire
child process group and preserves exit/output evidence.

## Validation and limits

Run `python3 scripts/tests/test_perf_luna_benchmark.py` and
`python3 scripts/perf_luna_benchmark.py --self-test`. These are synthetic provenance, semantic
projection, sampling, timeout, and cleanup checks; they do not establish a real speedup. A real
comparison requires archived snapshots and all four build products with re-verifiable manifests
and linked artifacts. Results are machine-specific and should include the generated JSON without
being treated as portable performance guarantees.
