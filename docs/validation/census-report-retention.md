# Census report retention repair

The original full matrix and isolated two-worker census both exceeded the
unchanged 8 GiB aggregate RSS budget. Lower concurrency alone was insufficient.

`refusal_census.run` now returns a census projection after parsing and validating
its complete report, result lattice, executable exit status, obligation counters
and finding object list. The projection retains verdict/state, obligation counts,
replay-gap count and each finding's refusal gate, kind and message. Missing fields
and explicit null remain distinct. Certificate arenas, traces, source graphs and
unused finding payloads no longer survive in completed executor futures or the
aggregate results table. All inputs and existing failure categories remain.

The three callers (`refusal_census`, `census_diff`, `corpus_census`) consume these
retained fields. Raw stdout/stderr are released immediately after parsing, before validation and
projection. Parsing still temporarily holds one complete report per active
worker; this change does not bound a single report's size or compiler child RSS.

Acceptance remains open: unchanged deterministic census/refusal output and a
complete measured run under the original budget, with parent and child RSS
recorded. This source change alone does not establish the memory failure's full
cause or repair, and does not qualify prover compatibility.

## Diagnostic execution

`scripts/run_census_bounded.py` runs the complete census with explicit workers,
per-input timeout, aggregate RSS limit and wall-clock limit. It records parent
and child peaks, owned input commands, the process split at the aggregate peak,
real exit status and monitoring/census source hashes in `execution.json`.
Limit termination returns 125 and never presents a partial census as complete.
The normal census still checks binary hashes and source/compiler provenance.

A two-worker diagnostic with the original 8 GiB cap, 120-second per-input limit
and 1,800-second wall limit is in progress in
`build/census-retention-diagnostic/`. Its result remains pending.

## Input provenance guard

The census now hashes its complete input set and transitive textual includes
before and after execution. It refuses publication when either the input set or
dependency identities differ, and publishes `input-identity.json` alongside the
census with its digest in toolchain metadata. Missing dependencies are recorded
so their later appearance also invalidates publication. This covers direct and
brace include forms using byte-preserving paths and lexical resolution.

The running diagnostic loaded the preceding census implementation and therefore
does not exercise this new guard. It reads some harness includes from the mutable
compiler checkout; its memory result cannot establish immutable compatibility.
Endpoint comparison detects persistent changes, not edits that are reverted
between samples. Qualification still requires an immutable dependency snapshot.
Targeted acceptance passes with Python 3.14:
`python3.14 scripts/test_refusal_census.py`. Existing result/exit lattice,
provenance, deterministic-summary and timing checks pass. Added checks preserve
full-versus-compact refusal summaries and missing/null findings; cover direct,
brace, cyclic and missing dependencies; and invoke the real census main path to
confirm dependency mutation exits 2 without publishing a census. Complete memory
and immutable compatibility acceptance remain open.

The live `census_diff` path now captures input and product identities before the
initial run, checks the published census identity, and rechecks after unreadable
and timing retries. Changed inputs/products refuse comparison with exit 2. The
existing offline two-report comparison remains available without executing proofs.
`python3.14 scripts/test_census_diff.py` passes original comparison controls and
new stable, mutated-source, replacement-product and mismatched-record cases.
