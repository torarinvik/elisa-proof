# W-05: Z3 quantifier and array oracle (design)

Status: design, 2026-10-03. Not yet implemented. Recorded under IMPLEMENTATION_PLAN §21
("Solver certificates") because it adds a new hint format and a new checker entry point.

## Problem

W-02 gave the checker and the kernel seven sound rules for `forall i in a..<b: P(i)` (empty,
cover, extend, weaken, weaken-and-extend, lower, vacuous) plus the instance rule (`Q(t)` from a
covering fact when `c <= t < d`). What W-02 cannot do is *search*:

- It instantiates a fact only at subscripts that already occur in the goal
  (`PROOF_SYMBOLIC_INSTANCE_CANDIDATES` = 8). A goal that needs `xs[j]` at a term that appears
  nowhere (`xs[k - 1]` to prove something about `xs[k]`, or two instances of one fact) fails.
- It tries cover/extend/lower against each fact in turn, but never chains them
  (extend a fact that was itself only reachable by weakening a third).
- Read-over-write after W-03/W-04 leaves facts of the form `xs[k] == v` and frame facts;
  choosing which ones to combine with a quantifier is a search the checker does not do.

The goals this leaves behind are exactly the ones an SMT solver with quantifier instantiation
and the array theory finds easily. W-05 lets Z3 do the search and keeps the decision in the
checker, the same way W-01 did for Farkas multipliers.

## Non-goals

- Z3 never decides a goal. No new kernel rule, no new trusted boundary kind.
- No general first-order proof terms. The answer format is a list of rule applications from
  the fixed W-02 vocabulary, nothing else.
- No `exists` goals and no nested quantifiers (two-binder bodies stay a W-02 follow-up).

## Alternatives considered

1. **Trust Z3's `unsat` for quantified goals.** Rejected: grows the TCB by a whole solver;
   violates the W-programme rule "SMT reach with no growth in trust".
2. **Import Z3 proof objects (`(proof ...)`) and check them.** Rejected for now: the proof
   format is unstable across Z3 versions, quantifier steps (`quant-inst`, `mp~`, `nnf-*`) need
   a translation layer larger than the W-02 rules themselves, and a translator is trusted code.
3. **Instantiation lists (chosen).** Ask Z3 which ground instances it used, hand those back as
   terms, and let the checker add each instance as a derived fact through the existing
   instance rule, then re-run its ordinary search. If the instances are wrong or useless the
   goal stays unproven. This reuses W-02 verbatim and the trust cost is zero.

Alternative 3 is the same shape as W-01: an untrusted oracle proposes a witness, the
producer turns it into the marker it would have emitted itself, and the kernel replays it.

## Export: what elisa-proof writes for the oracle

Each unproven goal's `near_miss` gains `quantifier_problem` next to `linear_rows`, emitted only
when at least one captured fact or the goal is a symbolic-range forall, or reads an array:

```json
"quantifier_problem": {
  "goal": "<goal expression, s-expression form>",
  "facts": [ { "index": 0, "expr": "..." }, ... ],
  "arrays": ["xs"],
  "terms": ["k", "n", "xs.count"]
}
```

- `facts` uses the same indices as the report's `facts` list, so an answer can name a fact by
  index exactly like a W-01 hint names a premise.
- Expressions are printed in a small s-expression grammar (`forall`, `select`, `+`, `-`, `<`,
  `<=`, `==`, `and`, `or`, `not`, integer literals, names). `scripts/smt_oracle.py` maps it to
  SMT-LIB: names become `Int`, arrays become `(Array Int Int)`, `xs.count` an `Int` with
  `0 <= xs.count`. Width facts already present as facts carry the bounds; no width is invented.
- Budgets: at most 32 facts, 8 arrays, 64 terms, expression depth 12. Past any of them the
  problem is not exported (and the report says so by omitting it), never truncated.

## Oracle: how Z3 is asked

`scripts/smt_oracle.py --quantifiers` asserts the facts and the negated goal with
`(set-option :smt.mbqi false)` and E-matching on default patterns, plus `:produce-proofs true`.
On `unsat` it walks the proof for `quant-inst` steps and collects, for each, the quantified
fact (traced back to its fact index through named assertions `(! ... :named f3)`) and the
ground term substituted for the binder. Terms Z3 introduced itself (skolems, `k!N`) are
dropped; if a needed instance mentions only such terms the goal is skipped. With MBQI off the
instances are almost always over source terms, which is what makes them printable.

Timeout 2 s per goal, as in W-01. Without z3 installed the oracle proposes nothing.

## Hint format

Appended to the W-01 hints file so one `--linear-hints` run carries both kinds; a record kind
tag keeps them apart (the W-01 records gain an explicit tag `1`, read as-is when absent for
backward compatibility):

```
2 <goal_id> <count> (<fact_index> <term>){count}
```

`<term>` is the s-expression of the instance term, quoted, on one line. Limits: 8 instances per
goal, term depth 6, 4096 bytes per record. A record over a limit, an unknown fact index or an
unparseable term makes the whole file malformed (exit 2), as for W-01.

## Checker path

For a goal with a matching `2` record, after the ordinary search and the W-01 hint have failed:

1. Parse each term with the existing expression reader and reject it unless every name in it
   is in scope at the goal (a parameter, a live local or a binder of an enclosing proof
   context). A term naming the fact's own binder or the reserved marker is rejected.
2. For each `(fact_index, t)`: the fact must be a symbolic-range `forall j in c..<d: Q(j)`.
   Prove the side goals `c <= t` and `t < d` with the ordinary search. If both hold, push
   `Q(t)` as a derived fact through the *instance rule* exactly as W-02 does for a goal
   subscript, so its certificate step is the same instance step the kernel already
   replays.
3. Re-run the goal search once with the added instances. No further oracle round.

Instances that fail their side goals are dropped silently (and counted in `measurements`),
because a hint is only a suggestion. The kernel sees ordinary instance steps followed by an
ordinary proof; it never learns an oracle existed.

## Trust argument

Every fact the checker adds is `Q(t)` for a fact `forall j in c..<d: Q(j)` it already holds
and a `t` it proved to lie in `c..<d`. That is the W-02 instance rule, already in
KERNEL_INVENTORY with its own soundness note and adversarial tests. Adding true facts cannot
make a false goal provable. Hence the TCB delta is the parser for the hint record, which only
shapes untrusted data and is followed by the same scope and side-goal checks a source term
gets.

## Experiment and success criteria (plan §21)

Runnable experiment: `scripts/test_quantifier_oracle.py` over three fixtures written first.

- `examples/quantifier_oracle.elisa`: goals W-02 refuses today that need one or two unseen
  instances (`xs[k - 1] <= xs[k]` from a sorted-prefix fact; a fill loop whose postcondition
  reads `xs[n - 1]`; two instances of one bound fact combined linearly).
- `examples/rejected_quantifier_oracle.elisa`: a goal that is false, plus goals whose only
  "instance" lies one past the range.
- Hand-written hint files: a bogus instance outside the range, an instance on a non-quantified
  fact, a term naming an out-of-scope local, a term naming the binder, nine instances, a
  truncated record.

Success means all of:

1. Every positive goal proves with the oracle and **replays without z3 installed**.
2. Every rejected goal stays unproven with the oracle, and every bogus hint is refused (the
   goal stays unproven, or the file exits 2 for malformed records).
3. Census over `examples/` and the corpus: proven count strictly rises with the oracle, the
   plain census is unchanged, and the W-01 hint tests still pass with tagged and untagged
   records.
4. No new KERNEL_INVENTORY row.

Failure, and the decision to stop: if fewer than 5 census goals close with the oracle, or if
more than a third of Z3's needed instances mention skolem terms (so the printable-instance
assumption is wrong), record the numbers in AUDIT.md and park W-05 behind W-06 (invariant
suggestion), which attacks the same goals from the source side.

## Implementation order

1. Fixtures and the failing test first (they define the target).
2. `quantifier_problem` export in `linear/linear_hints.elisa`'s sibling
   `linear/quantifier_hints.elisa`, with its own budget test.
3. Tagged hint records in `app/linear_hints_input.elisa` (malformed-file tests).
4. Checker path (steps 1–3 above) in `linear/symbolic_quantifiers.elisa`.
5. `smt_oracle.py --quantifiers`, then census with and without it, then AUDIT.md.

## Open questions

- Whether instance terms should also be accepted for `xs[k] == v` read-over-write facts
  (a non-quantified fact): that is a pure fact-selection hint and could reuse the same record
  with a negative fact index. Defer until the census shows it matters.
- Prefix-sorted bodies need two binders; when W-02 grows them, the record needs one term per
  binder. The `<count>` field can carry pairs without a format break if a per-record arity is
  added then.
