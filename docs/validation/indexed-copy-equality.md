# Indexed-copy scalar equality replay repair (2026-10-08)

## Source change

The collection-frame swap regression on clean `fdc96e2e` produced 80 obligations,
79 certificates proven/replayed and one gap at `swap_second` return line 15.
The compiled certificate-context audit refused premise offset 13 of the copied
`t == a` consequence: historical `t == xs[i]` (kernel root 91). That copy equation
is no longer a live collection equality after the writes on lines 13–14.

`index_copy_equalities.elisa` independently reconstructs the receiver-free scalar
equality from the source-exact precondition and an immutable typed indexed copy.
It requires unshadowed primitive types and parameters, a unique local declaration,
matching element/value types, a contracts-only prefix, and no later modification
of the copy, value parameter or index. Only conjunctions are traversed when locating
the precondition. Collection writes do not revive the historical copy equation.
Both source and kernel trace validation use the same source admission predicate;
the surrounding kernel validation still checks serialized AST/kernel correspondence.

## Focused evidence

- Frozen compiler `52d60fcf`, matching runtime, O0 executable:
  `python3.14 scripts/test_index_copy_equality_source.py` passed. The authentic
  consequence is accepted and fifteen forged trace/source controls are refused:
  wrong trace line, local, value, kind, summary index, copy index, precondition value,
  mutable copy, rebound copy, pre-copy write, mutable value/index, shadowed primitive,
  missing equality and nonconjunctive equality.
- The compiled certificate-context audit now exits 0 for the previously refused
  copied consequence (`build/collection-frames-copy-equality-audit`). This is a
  focused internal audit, not whole-product qualification.
- Earlier failing audit evidence and hashes are retained in
  `build/collection-frames-copy-premise-audit.json`.

Paired producer/replayer build, the full original collection-frame regression and
uncached engine sweep remain pending. Production prover promotion and full
compatibility remain open. No proof obligation or adversarial refusal was removed.

## Clean paired product qualification

Source `364edfdb`, clean paired generation `25ee696e9c19461d927d8ff024dbaaac`,
builds in 54.08s at 1,989,536 KiB RSS under the original 8 GiB limit.
Both manifests identify clean source and the same generation; actual binary hashes
match their manifests (`build/indexed-copy-equality-product-identity.json`).
The portable replayer is unchanged and reused with the new paired manifest.

`ELISA_PROOF_BIN=<generation>/elisa-proof python3.14 scripts/test_collection_frames.py`
passes the complete original regression and its alias, stale count, count-indexed
and budget refusal checks. The original positive fixture is now 80/80 proven and
80/80 independently replayed with zero gaps. Exact JSON is retained in
`build/indexed-copy-equality-collection-frames.json`.

The uncached engine sweep passes all 73 reports / 4,246 obligations with zero
semantic errors, diagnostics, gaps or trusted assumptions, in 2.33s at 183,616 KiB
RSS under 3 GiB. Engine artifacts are in
`../elisa-engine/build/validation/indexed-copy-equality-engine-reports/`, with
`indexed-copy-equality-engine-inventory.json` and `indexed-copy-equality-engine-sweep.log`.
Full prover compatibility and production promotion remain open.
