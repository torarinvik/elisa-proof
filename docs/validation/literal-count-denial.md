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

A clean paired product build, original integer/float denial regressions, all 73
engine reports and complete compatibility remain pending. Production prover is
unchanged; this focused repair is not full release qualification.
