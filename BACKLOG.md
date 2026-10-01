# Elisa-Proof high-ROI backlog

Companion to [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) §20. The plan sets milestones and rules; this file lists concrete tasks ordered by return on investment. ROI means proved goals, user-visible usefulness or trust reduction gained per unit of work and per line added to the trusted base. Every task follows the plan's execution loop and §22 definition of done. That means positive, adversarial, malformed and budget tests; kernel-inventory updates for new trace kinds or replay calls; full chunks and dogfood green; an AUDIT.md entry; and a commit with evidence.

Tiers:
- **T0**: finish or unblock what is almost there. Days of work; closes known refusals.
- **T1**: multiplies coverage of real code. Weeks of work; each item unlocks a family of goals.
- **T2**: foundational; makes later work cheaper or claims stronger.
- **T3**: ambitious; needs a design decision recorded under plan §21 first.

Columns: **ID**, **Task** (the smallest coherent deliverable), **ROI** (why it pays), **Done when** (the evidence that closes it).

Tasks are grouped by theme (A–R); the tier sits beside each task's ID.

## W. Weakness program (do first; see plan §0)

| ID | Task | ROI | Done when |
| --- | --- | --- | --- |
| W-01 (T0, done 2026-10-01) | Z3 linear oracle: elisa-proof exports each unproven goal's linear rows, `scripts/smt_oracle.py` asks `z3` for Farkas multipliers, and `--linear-hints` feeds them back as C-02 certificates | First SMT reach with no growth in trust | Census with and without the oracle; forged and malformed hints are refused; replay passes without z3 installed |
| W-02 (T0, rules done 2026-10-01; prefix-sorted and triggered instances open) | Symbolic-range quantifier rules (cover, extend-by-one) in the checker and the kernel; triggered instances; trigger-free refusal (absorbs E-02) | Loops over unknown-length arrays become provable | Fill and prefix-sorted examples prove; adversarial off-by-one and wrong-range cases stay unproven |
| W-03 (T0) | Indexed-write frame: keep facts whose reads of `xs` are provably at other indices, plus `xs.count`; record `xs[k] == v` | Element writes stop erasing the proof state | Stale-binding and aliasing adversarial cases stay unproven; census gain |
| W-04 (T1) | Read-over-write for `push`/`pop`/`swap`/slices, and the remaining E-01 pieces | Collection algorithms keep invariants | Swap-based sort and partition examples prove |
| W-05 (T1) | Z3 quantifier and array oracle: answers come back as instantiation lists that the checker re-derives through W-02 rules | Automation for the hard goals W-02 alone cannot find | Hints replay without z3; a bogus instantiation is refused |
| W-06 (T1) | Invariant suggestion: generate candidate invariants (bounds, prefix quantifiers), prune Houdini-style with the checker, emit source text | Removes the biggest manual burden | 50% of A-05 corpus loops get a suggested invariant that checks |
| W-07 (T1) | Real-code corpus census per commit (A-05 made mandatory) | Coverage on real code becomes the score | `docs/census/corpus.md` updated by every W commit |
| W-08 (T2) | Scale: per-function budgets plus incremental reuse of unchanged functions' certificates | Large modules finish | A 5k-line module verifies in under 60 s |
| W-09 (T2) | cvc5 as a second oracle behind the same hint format | Portfolio robustness | Same hint replay; disagreements are logged, never trusted |

## A. Measurement first (T0; do before any tier-1 work)

| ID | Task | ROI | Done when |
| --- | --- | --- | --- |
| A-01 (T0) | `scripts/refusal_census.py`: run every example and dogfood unit, bucket each unproven goal by first refusing gate (guard name, tier, budget) | Every later task is chosen by count, not by guess. The memory rule "measure refusals by gate" becomes a tool | JSON + Markdown table checked into `docs/census/` with a date; reruns are deterministic |
| A-02 (T0) | Add a `refusal_gate` field to each failed goal in the JSON report (first guard that returned false) | Turns A-01 from instrumentation hacks into a supported report field; agents repair better | Every `ensure-unproven` carries a gate; schema test updated |
| A-03 (T0) | Census diff in CI: fail when proved-goal count drops or a new gate appears for an existing example | Stops silent regressions like the signed lower bound one | `scripts/test.sh` step compares against the committed census |
| A-04 (T0) | Per-function wall time and kernel node counts in `measurements`, with a top-10 slowest list | Finds replay blowups (the chained-call 10x case) before users do | Report field + a budget test that fails at 2x the recorded time |
| A-05 (T0) | Corpus of real Elisa code (compiler stage1 modules and Elisa-core, read-only copies) run nightly for the census | Coverage on real code is the plan's final measure (§22) | `docs/census/corpus.md` with proved/total per module |

## B. Close the known deferred refusals (T0)

| ID | Task | ROI | Done when |
| --- | --- | --- | --- |
| B-01 (T0) | Typed negative literals in goals: let `proof_signed_constant_at_width` accept `-(MAX+1)` as the exact minimum so `ensure result >= -128` proves without the `-127 - 1` spelling | Removes a user-facing trap found while landing the signed lower bound | `>= -128` on `i8` proves; `>= -129` refused as out of width; replay mirror updated in `kernel_replay/fixed_width_arithmetic.elisa` |
| B-02 (T0) | Determinism witness for effect-free callees: a callee with `requires` but no effects and scalar by-value arguments gets a `__elisa_deterministic_call` marker, retained by `proof_expr_call_stable` | Fixes `returned_chain` and likely `parse_twice_agrees`; a common idiom (call, call, compare) | Soundness argument in DESIGN.md; kernel replay checks the callee's effect set from `source_declarations`; adversarial: a callee with `can[...]`, a global read, or a mutable borrow argument is not retained |
| B-03 (T0) | Tuple-field `@r` for package_reader: resolve `result.field` for named-tuple returns into per-field summary facts | Named-tuple returns are the house style for multi-value parsers | package_reader example proves; wrong-label and positional-mismatch variants refused |
| B-04 (T0) | Define and close the "c4 scalar witness" item, or strike it: locate the original probe, write it as an example, then decide | An undefined item cannot be tracked | Either a landed fix with tests, or an AUDIT.md entry saying what it was and why it is dropped |
| B-05 (DONE) | `is` between enum values in contracts (`ensure result == (a is E.V)`) | Bool-valued predicates over enums are everywhere in parsers | `scripts/test_enum_tag_equality.py`: named tag equalities/conjunctions replay; wrong variant, wrong subject and call subject are refused. Conditional `if c is E.V: return true` is a distinct bool-literal-equality gap, not this item. |
| B-06 (DONE) | Qualified constants in `while` conditions, `for` ranges, assignments and call arguments | Finishes the body rewrite started in 4db58a8 with the same shadow guard | `scripts/test_qualified_constants.py`: all four contexts exercised, oversized values refused, and a shadowing `for` binder is refused. The u8 loop-decreases refusal is tracked separately. |
| B-07 (DONE) | Signed type bounds for locals, fields and tuple elements, not only parameters | Same fact, many more places; the parameter path already works | `scripts/test_signed_local_field_bounds.py` plus `scripts/test_signed_tuple_label_bounds.py`: both signed endpoints replay for locals, fields and named-tuple call projections; tighter tuple claims stay unproven. |
| B-08 (DONE) | Unsigned `u64`/`usize` upper bound through the relational path, since there is no i64 interval for it | Removes a whole class of "`index + 1` may overflow" refusals on usize | `scripts/test_usize_increment_under_count.py`: strict `usize`/`u64` peers prove in producer and replay; non-strict, absent and overshooting cases remain unproven. |

## C. Arithmetic and decision procedures (T1)

| ID | Task | ROI | Done when |
| --- | --- | --- | --- |
| C-01 (T1) | Full difference-bound closure (Floyd–Warshall on ≤ 32 names) replacing the 4-round propagation cap | Chains of `a < b < c < n` are the bread and butter of index proofs | Budget test at 32 names; replay mirror; the round-cap comments removed |
| C-02 (T1) | Fourier–Motzkin elimination for small linear systems (≤ 6 variables) with a certificate of the combination used | Proves the sums-of-bounds goals that interval reasoning cannot | The certificate lists nonnegative multipliers; replay checks the linear combination only, not the search |
| C-03 (T1) | Farkas certificates for unsat linear facts, checked by the kernel with exact i128-by-parts arithmetic | Makes C-02 and contradiction detection independently replayable | Malformed multipliers and overflowing combinations refused |
| C-04 (T1) | Multiplication by a constant and division by a positive constant in the affine layer (`2*i + 1 < n`) | Strided loops and packing code | Positive and overflow-adversarial examples at every width |
| C-05 (T1) | Modular arithmetic facts for `%` with a positive divisor (`0 <= x % k < k`) and wrapping ops (`wrapping_add`) | Hashing, ring buffers, checksums | Replay rule plus a negative divisor refusal |
| C-06 (T1) | Bit-vector fragment: `&`, `|`, `>>`, `<<` with constant masks produce interval facts (`x & 0xFF <= 255`) | Decoders and packers, which are the compiler's own code | Mask facts replay; shifts past width refused |
| C-07 (T1) | Nonlinear sign rules: product of nonnegatives is nonnegative, square is nonnegative, monotone multiplication by a positive bound | Cheap, very frequent in size computations | Each rule is a named kernel rule with its own test |
| C-08 (T2) | Optional SMT portfolio (z3/cvc5) as an untrusted oracle whose answers must come back as C-02/C-03 certificates | Automation without trust growth | Oracle off by default; every oracle proof replays without the solver installed |
| C-09 (T1) | Counterexample minimization: shrink found counterexamples and report them in source terms (parameter names, field paths) | Refusal messages become actionable for humans and agents | Counterexamples printed as `v = -1, s.len = 0`; tested on 10 rejected examples |
| C-10 (T1) | Counterexample search over signed widths and negative values (the search currently favours nonnegative candidates) | Many refusals report "no counterexample" when one exists | `rejected_signed_*` examples each report a concrete witness |

## D. Calls, summaries and modularity (T1)

| ID | Task | ROI | Done when |
| --- | --- | --- | --- |
| D-01 (T1) | Frame conditions `modifies` / `reads` on functions, checked at the definition and used at call sites to keep unrelated facts | Today a call with a mutable argument drops almost everything; frames keep what the callee cannot touch | A call with `modifies a` keeps facts about `b`; a body writing outside its frame is refused |
| D-02 (T1) | `old(expr)` in postconditions | Required for every "increments", "appends one", "preserves others" spec | `ensure v.count == old(v.count) + 1` proves for push wrappers |
| D-03 (T1) | Summary caching keyed by callee fingerprint: reuse a callee's proven summary across files and runs | Cuts reverification of stable libraries to near zero | Second run of an unchanged module does no goal work; the cache key includes compiler pin and checker version |
| D-04 (T1) | Pure function unfolding: inline bodies of small pure functions (≤ N nodes, non-recursive) into goals | Removes the need to write contracts for trivial helpers | `is_digit(c)` style helpers prove callers without contracts; recursion refused |
| D-05 (T1) | Lemma functions: `lemma` declarations with no runtime code, callable in proofs, with totality checked | The standard way to package reusable facts | A lemma proves once, applies at many sites, and appears in the dependency index |
| D-06 (T2) | Contract inference for leaf functions: propose `ensure` clauses from return expressions and verify them | Agents and humans get specs for free on simple code | `--infer-contracts` writes suggestions; every suggestion is verified before it is shown |
| D-07 (T1) | Method receivers: summaries for `self`-mutating methods with field-level frames | Most real Elisa code is methods on structs | A method mutating `self.a` keeps facts about `self.b` |
| D-08 (T1) | Generic functions: verify once per type parameter bound, instantiate summaries at call sites | Collection helpers are generic | Two instantiations use one proof; a bound-violating instantiation refused |

## E. Data structures, ADTs and induction (T1/T2)

| ID | Task | ROI | Done when |
| --- | --- | --- | --- |
| E-01 (T1) | Collection model: `darray` as (count, element function) with push/pop/resize/index/extend axioms, each replayed | Most refusals in parsers are about collection contents, not counts | `v.push(x); ensure v[v.count - 1] == x` proves |
| E-02 (T1) | Quantified invariants over ranges (`forall i in 0..<n: a[i] >= 0`) with instantiation triggers | Required for any array algorithm spec | Sort-prefix and fill examples prove; trigger-free quantifiers refused with a clear message |
| E-03 (T1) | Loop invariants that compile: lower `invariant` into proof-only annotations the backend ignores (today stage1 declines bodies with them) | Unblocks real loop proofs; currently loops must be rewritten | Loops with invariants compile and prove; mutation tests on each invariant |
| E-04 (T1) | Structural induction over recursive enums with an automatically generated induction principle | Trees, ASTs and lists are the domain of a compiler | List length and tree size lemmas prove by `induction`; non-structural recursion refused |
| E-05 (T1) | Match exhaustiveness as a proof fact: after an exhaustive match, the disjunction of arms is available | Complements variant exclusion (d197bd7) | A match over all variants lets a later goal case-split on the arms |
| E-06 (T1) | Enum payload facts: after `x is E.V(p)`, facts about `p` flow from `x`'s invariants | Parsers carry tokens in payloads | A payload bound provable from an enum-level invariant |
| E-07 (T2) | Struct invariants (`invariant` on struct types) checked at construction and field writes, assumed at reads | Removes repeated `requires` on every function taking the struct | A struct with `start <= stop` never needs it restated |
| E-08 (T2) | Standard proof library: verified `darray`, `sview`, `min`, `max`, `abs`, `clamp`, search and sort specs | Everyone needs these; proving them once pays forever | `lib/proof/` with 30+ lemmas, each replayed, documented in README |
| E-09 (T2) | String/sview content model (bytes, slicing, prefix, equality) | Tokenizers and parsers | `starts_with` and slicing lemmas prove; out-of-range slices refused |

## F. Resources, ownership and aliasing (T1)

| ID | Task | ROI | Done when |
| --- | --- | --- | --- |
| F-01 (T1) | Exact sview returned-call witness (plan P1-03) | Listed in plan; blocks provenance through wrappers | Plan P1-03's completion evidence |
| F-02 (T1) | Per-field alias analysis so a mutable borrow of `s.a` does not drop facts about `s.b` | Large struct-heavy code loses most facts at every call today | Field-disjoint borrows keep facts; overlapping ones drop them |
| F-03 (T1) | Region-scoped facts: facts about a borrowed value survive until the borrow ends, not until the next statement | Fewer spurious drops in loops | Loop body with a shared borrow keeps count facts across calls |
| F-04 (T2) | Separation-logic style resource traces exported in the certificate for independent checking | Moves resource reasoning from trusted to replayed | Resource traces replay; a forged trace refused |

## G. Kernel and trust (T2)

| ID | Task | ROI | Done when |
| --- | --- | --- | --- |
| G-01 (T2) | Rule-by-rule soundness notes: each kernel rule in KERNEL_INVENTORY.md gets a one-paragraph argument and a counterexample test for its most tempting weakening | Makes the TCB reviewable by an outsider in a day | Every inventory row links to its argument and test |
| G-02 (T2) | Mutation testing of the kernel: flip each comparison or constant in `kernel_replay/`, and every mutant must break some test | Measures test strength where it matters most | Mutation score ≥ 95% recorded; surviving mutants either killed or justified |
| G-03 (T2) | Differential replay: a second, deliberately naive checker for the linear fragment (in Python, test-only) cross-checks every certificate | Catches kernel bugs the kernel's own tests share assumptions with | Both checkers agree on the whole corpus; a disagreement fails CI |
| G-04 (T2) | Fuzz the certificate reader with structure-aware mutations (swap roots, off-by-one children, huge values) | Malformed input is the main attack surface | 1M fuzz cases, zero accepted malformed certificates, no crash |
| G-05 (T2) | Shrink the trusted source-adapter list: move `proof_expr_equal` and similar out of the trusted path by checking against kernel nodes | Each adapter removed is TCB removed | KERNEL_INVENTORY adapter count decreases and tests pass |
| G-06 (T2) | Self-verify the kernel's arena validator and interval evaluator with full functional specs (not only safety) | Plan M13's strongest claim | `kernel_core` functions carry `ensure` clauses that describe results, and they prove |
| G-07 (T3) | Export certificates to Lean 4 for the linear-arithmetic fragment | An external, widely trusted checker validates our claims | A reproducible script that checks the corpus's linear certificates in Lean |

## H. Human proof language and agent API (T1)

| ID | Task | ROI | Done when |
| --- | --- | --- | --- |
| H-01 (T1) | `assert ... by <tactic>` and `calc` blocks in source for step-by-step proofs | Lets users bridge goals the automation misses without leaving Elisa | `calc a <= b <= c` proves; a broken step names its line |
| H-02 (T1) | `proof` blocks with `have`, `cases`, `induction`, `apply lemma` in source, lowered to the existing tactic protocol | One proof language for humans and agents | Every tactic in `action_protocol.operations` has source syntax and a test |
| H-03 (T1) | Goal explanation: for each unproven goal, list the facts that almost proved it and the missing fact | The single most useful thing for repair | JSON `near_miss` field; tested on the rejected examples |
| H-04 (T1) | LSP server: diagnostics, hover shows facts at a line, code action inserts a suggested `requires` | Adoption; the feedback loop moves into the editor | VS Code extension running on the examples folder |
| H-05 (T1) | Stable agent protocol v2 with a versioned JSON schema file and compatibility tests | Agents break silently on field changes today | `schema/elisa-proof-v2.json`; old reports validate against v1 |
| H-06 (T2) | Proof-state diff between runs, so an agent sees exactly which goals changed after an edit | Faster agent repair loops | `--diff old.json` output tested |
| H-07 (T1) | Human-readable report mode with source excerpts and carets, grouped by function | Humans read terminals, not JSON | Snapshot tests of the text output |

## I. Performance and scale (T1)

| ID | Task | ROI | Done when |
| --- | --- | --- | --- |
| I-01 (T1) | Incremental checking by function fingerprint: only changed functions and their dependents re-run | Large modules verify in seconds on edit | Editing one function reruns one function; a changed contract reruns its callers |
| I-02 (T1) | Parallel verification of independent functions | Linear speedup on multi-core | `--jobs N`; results byte-identical to `--jobs 1` |
| I-03 (T1) | Fact-set pruning: drop facts not sharing a name with the goal's transitive name closure before solving | Keeps the 64-fact budget from being hit by unrelated globals ("kernel globals cost every function") | Standalone audit regains headroom; no goal lost in the census |
| I-04 (T2) | Hash-consed kernel arena across a whole run, not a 256-node window | Memory and replay time drop for large files | Node counts drop on the corpus with identical results |

## J. Real-world validation (T1; continuous)

| ID | Task | ROI | Done when |
| --- | --- | --- | --- |
| J-01 (T1) | Verify one real tokenizer end to end (memory safety and "tokens cover input") | The flagship demonstration | Example plus write-up; every function proves |
| J-02 (T1) | Verify the proof tool's own JSON writer for well-formedness of emitted brackets | Dogfooding with a functional property, not just safety | Spec and proof in the dogfood set |
| J-03 (T2) | Verify a compiler pass from stage1 (for example constant folding) against a reference evaluator | Plan M13 | Stated theorem, proof, and replay artifact |
| J-04 (T1) | Tutorial: ten graded exercises from "prove an index is safe" to "prove a sort's output is ordered" | Onboarding; doubles as an integration test suite | `docs/tutorial/` whose examples run in CI |

## K. Incremental quick wins (T0; each a few hours)

| ID | Task | ROI | Done when |
| --- | --- | --- | --- |
| K-01 (T0) | `abs`, `min`, `max` builtins as known pure functions with exact summaries | Frequent, trivial, currently opaque | Each has positive and off-by-one examples |
| K-02 (T0) | `x != y` facts feed strictness (`a <= b` and `a != b` give `a < b`) | Common after equality guards | Rule in producer and replay |
| K-03 (T0) | Early-return guards as facts for the rest of the body (`return if i >= n`) in every statement position, not only at top level | Guard-clause style is the house style | Nested guards inside loops and ifs produce facts |
| K-04 (T0) | `bool` locals as fact carriers: `ok: bool = i < n; if ok:` gives `i < n` in the branch | Common readability refactor that loses proofs today | Positive example plus a reassigned-flag refusal |
| K-05 (T0) | `char` range facts (`'0' <= c <= '9'` implies `c - '0' <= 9`) | Every lexer | Digit-parse example proves |
| K-06 (T0) | `.count` of a literal array beyond empty (use the kernel-safe usize constant route) | Table-driven code | `[1, 2, 3].count == 3` proves without the old cascade cost |
| K-07 (T0) | Better message for the i8 `ensure` front-end diagnostic so users know the proof engine still ran | Confusing status seen during signed-bound work | Report states "front end diagnostic, engine: proved" |
| K-08 (T0) | `--explain <goal_id>` CLI printing facts, origins and the refusing gate | Makes A-02 usable by hand | Snapshot test |

## Execution order

1. A-01, A-02, A-03 first. Every later choice uses the census.
2. B-01 through B-08 and K-01 through K-08, in census order.
3. Tier 1 in this order: C-01, D-01, D-02, E-01, E-03, C-02/C-03, H-03, D-04, E-02, F-02, I-03, I-01.
4. J-01 once E-01, E-02, E-03 and D-02 land. It is the headline result and validates the stack.
5. Tier 2, and tier-3 items only after their plan §21 decision is recorded.

Re-rank after every ten landed tasks using the census delta. A task whose census impact came in under a third of its estimate is a signal to re-measure before the next one ("the obvious refactor is usually not what the cluster needs").
