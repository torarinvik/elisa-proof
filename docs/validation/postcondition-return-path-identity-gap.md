# Postcondition return-path identity gap

**Status (2026-10-15): multi-exit postconditions fail closed in current source admission; full path-bound replay remains an expressivity prerequisite before supporting them.**
The source changes are uncompiled and unqualified.

## Finding

Postcondition obligations are recorded once per return path, but their report
identity contains only the function, contract source line and postcondition
ordinal. The checked-view census currently requires exactly one ledger event
for each inventoried source contract. It does not require an event for each
source exit or associate an event's attempt span with the return that produced
it. Current positive source admission compensates by accepting only a narrow
straight-line body with one supported final return.

For a result-free postcondition, source admission checks the attempt goal against
the parser-owned ensure expression. It does not bind the attempt to a return
site. Attempt fact validation uses the attempt line and owner function. The
branch-fact validator scans the whole function body for a matching branch and
same-line assertion, and local-binding checks have no return-site cursor. These
owner-wide checks cannot support branch-local evidence across multiple exits.
The current single-exit source gate keeps this a path toward future unsoundness
if admission is broadened, rather than a demonstrated issue in the admitted
subset.

Example shape:

```elisa
def f(p: bool) -> i64:
    ensure p
    if p:
        assert p
        return 1
    else:
        return 0
```

The true arm can produce a successful attempt for `ensure p`; that attempt's
goal and owner also match the failed ensure event from the false arm. The current
source inventory marks the function unsupported because its body contains an
`if`, so source admission refuses positive evidence for this shape. Same-line
statements make line-based identity collisions explicit, but distinct offsets
would also need path lineage if this syntax becomes supported.

Relevant implementation paths:

- `src/proof/check/returns/contracts.elisa` records one postcondition obligation
  inside the return checker.
- `src/proof/model/report_postcondition_inventory.elisa` keys expected checks
  by function and ensure ordinal; checked-view source admission requires exactly
  one event for each inventoried ensure.
- `src/proof/model/report_goal_admission.elisa` compares result-free ensure
  expressions to attempt goals without a return-site association.
- `src/proof/replay/attempt_fact_source_validation.elisa` validates attempt
  facts without a return position.
- `src/proof/replay/boundary_branch_fact_sources.elisa` validates branch facts
  against the owner body, not the exact branch path and source prefix leading to
  a postcondition return.

## Required boundary

A full expressivity extension needs an independent source exit census and
path-bound attempt validation before it accepts branched postconditions:

1. Reconstruct every supported function exit from parser-owned source, including
   nested `if`, `match`, loops and expression arms. Reject unknown, ambiguous or
   over-budget forms.
2. Give each expected postcondition check a stable path identity. A `Return`
   `Ast::Pos` is sufficient only for distinct explicit return nodes; also retain
   enclosing branch/match/expression-arm lineage, or refuse lowered shapes whose
   synthetic returns reuse one position.
3. Require a one-to-one event census for each postcondition × exit. Bind every
   event span, attempt and certificate to the reconstructed identity.
4. Validate every fact against the exact path and source prefix ending at that
   exit. Branch facts must have matching ancestor/polarity; local bindings and
   updates must be live at that return. A return-position label by itself is
   insufficient if fact replay still scans the whole function.

The current fallback gates generic postcondition admission on a parser-owned,
supported straight-line return inventory row for the exact owner. The return
shape scan rejects explicit body branches and path-splitting return expressions,
including `if`, `match`, `catch`, short-circuit Boolean operators,
comprehensions, and expression blocks. For that supported single-exit subset,
checked-view admission now builds a bounded hash census of postcondition events
and requires exactly one event for every inventoried source contract. This also
checks rows without attempts, and rejects duplicate or omitted events without a
ledger rescan for every attempt.
The specialized literal ensure route remains limited to a direct body ensure
and one literal or parameter return, so it does not admit the branched example
above. This is conservative; it does not replace the full path identity and
per-exit census described above.

Implementation touched `src/proof/model/report_goal_admission.elisa`,
`src/proof/model/report_postcondition_ast_inventory.elisa`,
`src/proof/model/report_postcondition_inventory.elisa`, and
`src/proof/model/checked_view_admission.elisa`, plus the default-deny call path
in `src/proof/model/report_theorem_source_admission.elisa`. Static source review and
`git diff --check` only; no tests or builds were run. The parser inventory still
does not carry return positions or path lineage, and branch/local fact validation
is not bound to a return cursor, so the full requirement remains open.

## Lowering caveat

`proof_check_value_match_return` and `proof_conditional_value_arms` synthesize
return checks from arms while reusing the original enclosing source position.
Therefore a complete exit census must preserve branch lineage or refuse these
lowered paths; comparing line/offset alone would merge distinct exits.
