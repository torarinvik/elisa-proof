# Exact unsigned subtraction counterexamples

The original strict-negative branch fixture was refused with a budget timeout;
the diagnostic evaluator could not evaluate its computed subtraction. The machine
diagnostic now admits same-width u8/u16/u32 subtraction only when both operands
inhabit that domain and the sampled left operand is at least the right operand.
Underflow, mixed signed/unsigned sorts and full-width arithmetic remain unknown.
Source operator guards cover the complete comparison and its premises, including
imported subtraction and ordering replacements. Theorem acceptance is unchanged.

Frozen compiler 52d60fcf and its matching runtime pass the compiled harness in
13.63 seconds / 1,785,392 KiB under the original 3 GiB focused budget. Controls
cover exact differences, zero, underflow, negative/out-of-range values, mixed
widths, untyped names, depth exhaustion and overloaded subtraction/ordering.
The original return-branch fixture retains 23 replayed certificates and now emits
a concrete disproving model for the strict-negative declaration.

The first two harness attempts failed on an inline darray argument that this
compiler backend declined as an aggregate expression. Explicit typed argument
arrays resolve that fixture construction issue. Logs are retained in
`build/unsigned-subtraction-controls*.log`; the passing run is `-values.log`.
The focused harness is registered in the integrated feature matrix.

## Clean product qualification

Source `5077910ccff0f90dc78f3d2f2e754bea634bfd84` builds both products cleanly
in 44.98s at 3,116,320 KiB peak RSS under the unchanged 8 GiB / 600s budget.
Pair generation: `6eb829755ac2493783f34e2f0ed58c67`. Both manifest source
identities and actual binary hashes were verified; evidence is
`build/unsigned-subtraction-product-identity.json` and
`build/unsigned-subtraction-paired-build.log(.json)`.

The original `scripts/test_return_branch_path_fact.py` now passes through the
actual CLI. An uncached engine sweep retains all 73 reports / 4,277 obligations,
including the mesh-shape additions, with independent replay and zero diagnostics,
gaps or trusted assumptions. Main engine evidence:
`build/validation/unsigned-subtraction-engine-inventory.json` and reports folder.

Three broader original scripts remain failed on both this pair and the prior
`452ab663` pair: counterexample domains sees compiler diagnostic 324 where its
fixture expects only 322; disjunction-domain expects refusal for a now-proved
fixture; strict-order-disequality's positive fixture is refused. Before/after
logs are retained in `build/unsigned-subtraction-*.py.log`. These require
classification against their contracts, not discarded assertions. Full
compatibility and production promotion remain open; production is unchanged.
