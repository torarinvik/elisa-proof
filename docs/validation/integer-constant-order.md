# High-bit integer constant ordering — focused repair

## Defect and design

Clean literal-count pair `a039d7c5c187463bbe74f577b6cb92a4` leaves one of
23 certificates unreplayed in `return_branch_path_fact.elisa`: the positive
`subtraction_path_bound_u64` return at line 42. Its opaque `U64_MAX` name has only
a scalar witness, which does not distinguish integers from NaN-capable floats.

An unsigned-width witness was rejected as a repair: it removed the replay gap
by making that required positive contract unproved. The retained diagnostic is
`build/return-branch-width-candidate-diagnostic.json`.

`__elisa_primitive_integer_type(term)` now supplies scalar identity and integer
classification without a numeric pin or arithmetic width/range. High-bit immutable
u64/usize globals use this witness in place of the scalar-only fact, preserving
fact count. Integer +/- total ordering can complement a comparison even under
wrap; arithmetic range admission remains separate. Source and kernel denial
readers, scalar lookup/cache and marker retention/model handling recognize it.
The name is reserved against source declarations.

## Source admission and controls

The source-backed boundary independently requires a canonical one-positional-
argument marker, a unique owner at the consuming declaration line, exact visible
immutable high-bit integer declaration, matching declaration line, unshadowed
primitive type and no parameter/local shadow. A nearer unsupported declaration
blocks root fallback. Duplicate owners are refused even when only one resolves
the constant. This witness proves no numeric value equality.

Focused frozen-52 compiler regression:
`python3 scripts/test_integer_constant_source_compile.py`.
It preserves all 23 recorded certificates and four original positive declarations,
while the original strict and floating negatives remain unverified. Source
substitutions cover float declaration, parameter/local shadowing, unsupported
initializer, duplicate owner, primitive alias and mutable declaration. Canonical
controls cover zero/two arguments, named argument and parenthesized callee; wrong
owner refuses. The regression is registered in the integrated feature matrix.

Clean paired product, actual CLI negative/reserved-name controls, portable replay,
73-report engine inventory and full compatibility remain required. Production
prover is unchanged. This note does not claim broader qualification.
