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

## Paired product evidence

Clean source `452ab663` produced paired generation
`cf8be5a1dc95437b8365038b580ad967` in 53.42 seconds at 3,058,048 KiB RSS.
Both manifests identify the clean source; actual executable hashes match them
(`build/integer-constant-product-identity.json`). The actual original fixture
replays 23/23 certificates and retains all four positive declarations. Original
integer-disjunction, float/integer-bound and indexed-boolean controls pass.
The reserved-marker declaration is refused with `proof-internal-name`.
A minimal positive public package independently replays 3/3 certificates; portable
adapter replay does not establish source authentication.

The engine's uncached inventory retains 73 reports / 4,246 obligations, zero
errors, diagnostics, gaps or trusted assumptions, with independent replay
(2.11 seconds / 204,064 KiB; engine
`build/validation/integer-constant-engine-inventory.json`).

The original return-branch regression script still fails: its strict-negative
finding has status `timeout`, while the script requires `disproved` or `unknown`.
Both the preceding literal-count pair and this pair have that same status. This
is an open producer-budget defect or classification issue, not a passing original
regression. Full compatibility and shared/native qualification remain required;
production prover is unchanged.
