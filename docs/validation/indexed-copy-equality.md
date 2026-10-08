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
