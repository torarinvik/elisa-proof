# Literal-array count denial replay — 2026-10-08

## Source repair

The clean `9db21d8e` pair reports `literal_index.elisa` as 18 certificates,
15 replayed and three gaps: `guarded_read` and both `same_slot` upper bounds.
A focused diagnostic validates all eight facts in the first certificate through
both AST and serialized-kernel trace admission. Final derivation refuses the
negated order because its literal-array count has no field-place width marker.
Substitution replaced the collection name with its array value; the marker still
names the original local.

The kernel denial integer-term rule now uses its existing bounded constant-leaf
reader for field terms before consulting width markers. That reader accepts only
`count` of an array whose length is in its existing 0–8 fragment. Arbitrary fields
and non-array receivers still need authenticated width markers. Existing arena,
source admission, scalar comparison and budget checks remain in force.

## Focused evidence

`test_literal_count_denial_compile.py` compiled against frozen compiler
`52d60fcff98ebdb8368ec460d5e60662a6008147` and its matching runtime exits zero:
all 18 original certificates replay. Private classification controls accept array
lengths 0–8 and refuse length 9, wrong field, identifier/string/float/tuple/record
receivers, out-of-range node and exhausted depth. These classification controls do
not replace public arena validation or establish malformed arena admission.
The test is registered in the integrated feature matrix.

Clean source `1cfbe9883e2c5bc4bfed25a31cb72ea98dfe5b42` paired generation
`a039d7c5c187463bbe74f577b6cb92a4` builds in 72.78 seconds at 1,513,376 KiB
peak RSS under 8 GiB. Both manifests identify clean source and matching generation;
actual executable hashes match. Identity evidence is in
`build/literal-count-product-identity.json`.

The original fixture proves/replays 18/18 through the source-backed product. Its
exported package replays 18/18 through the paired portable product; that route
retains its reported adapter trust boundary and does not authenticate source.
Reports are `build/literal-count-report.json`, `build/literal-count-package.json`
and `build/literal-count-portable-replay.json`.

Original `test_integer_disjunction_denial.py`, `test_float_integer_bounds.py` and
`test_indexed_boolean_denial.py` all exit zero with this actual product. Each
subprocess exit was independently checked. All 73 uncached engine reports retain
4,246 obligations with independent replay, zero diagnostics/gaps/trusted
assumptions in 4.02 seconds at 131,376 KiB under 3 GiB. Engine inventory is
`../elisa-engine/build/validation/literal-count-engine-inventory.json`.

Complete compatibility remains open. The separate immutable `9db21d8e` census
also stopped under explicit two-worker concurrency at 8,415,840 KiB after
1,651.92 seconds under the original 8 GiB limit. It remains incomplete; the
next diagnostic needs per-input RSS evidence.
Production prover is unchanged; this focused repair is not full release
qualification. Bundle this qualification note with the next source integration;
do not create a documentation-only commit.
