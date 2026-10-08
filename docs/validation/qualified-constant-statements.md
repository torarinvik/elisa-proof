# Qualified constants in statement replay

The clean `57663d01` paired product (`aa71933424c7491098a87dcadd25dda9`)
retains three source-replay gaps in `qualified_constants_statements.elisa`:
assignment return, loop invariant preservation, and loop decreases. The producer
emits 17 certificates; source replay admits 14. Its one semantic warning remains
part of the fixture evidence.

The source repair normalizes constants inside assignment values and loop guard /
invariant expressions using the existing exact declaration, literal value and
unshadowed path validator. A serialized constant equation alone is insufficient.

Preservation and decreases checking independently instantiate the same loop
assignment with different reserved names. The loop source route reconstructs its
unique assignment, iteration context, stable value and source span before accepting
these equivalent definitions. The consumed name must occur in the certificate's
fact snapshot. Conflicting definitions and summary uses remain refused. Other
source routes retain their original single-symbol uniqueness rule.

`scripts/test_qualified_constant_statement_source.py` compiles with the frozen
`52d60fcf` compiler and runs the complete source fixture: 17/17 certificates replay.
It checks changed constant declarations, a shadowed module path, wrong context,
wrong value, conflicting definitions and an appended unused reserved symbol.
The harness preserves source byte buffers while each parsed tree is in use.

`scripts/test_loop_invariants_compile.py` also passes its original targeted
source-bound replay controls with the same frozen frontend, including its appended
reserved-name refusal; the fixture proves with zero replay gaps.

This is focused source qualification. A clean paired product, original public
qualified-constant controls, engine sweep and full compatibility gate must qualify
integration separately. No production promotion or full compatibility claim follows
from this focused result.
