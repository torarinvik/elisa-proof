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
