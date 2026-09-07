# Full implementation audit — in progress

Passing the current suites is regression evidence, not completion of the full audit.
The objective covers all existing implementation code, scripts, proof fixtures, and their
assumptions about the compiler. No module below is yet certified as fully audited.

## Repaired: unsigned local substitution erased fixed-width semantics

Reproducer: `examples/rejected_unsigned_local.elisa` (with `rejected_unsigned_local_states.elisa`).

Observed at revision `8f3dfbf`: `x: u8 = 255` followed by `proof x + 1 > x` was certified,
because the declaration path substituted the initializer literal for the name and every later
tier reasoned about signed `255 + 1`. The interim containment rejected any function with an
unsigned local, which also excluded `kernel_core.add_node` and
`proof_kernel_replay_difference_query` from verification.

Repair (`src/proof/check.elisa`): an unsigned local is bound to its own symbol, exactly like an
unsigned parameter, and carries the same traced `type-bound` facts (lower bound, width marker,
and exact upper bound below 64 bits). Its value is recorded as a traced `local-binding` equality
only when the value is range-safe under the current facts; a possibly wrapping initializer leaves
the symbol opaque within its type range. Replay admits `local-binding` as a boundary fact kind.

Re-symbolization is now explicit and transitive. Declaring a spelling that already denotes a
symbol (a shadowed local, a parameter, or a forgotten binding), rebinding an unsigned local, and
any compound assignment purge every fact mentioning the old symbol and forget every other binding
whose recorded value mentions it, re-establishing only the compiler type facts of cascaded
bindings. A self-referential initializer such as `x: u8 = x + 1` yields an opaque value.

Fact invalidation inside symbolic execution keeps type-bound facts of live bindings and
parameters (`proof_clear_facts_keep_type_bounds`); a scoped `proof` block likewise keeps only
those facts. Previously a cleared marker would have let later arithmetic on the binding be folded
as unbounded signed arithmetic. Type facts are added idempotently; without that, joins and
rebindings multiplied identical facts and traces until the standalone replay audit did not finish.

Coverage: `examples/unsigned_local.elisa` proves bounded declaration, rebinding, `usize` from a
count, an ensure through a `u8` local, unsigned subtraction under an order precondition, and the
type range inside a scoped block. The rejected fixtures cover wrapping declaration, rebinding,
compound assignment, branch and loop locals, a wrapping initializer, a local shadowing a
parameter with a precondition, and a dependent binding that must be forgotten on rebinding; the
tests require that no arithmetic goal in them proves or certifies. `kernel_core` and its
call-site fixture now prove completely and the standalone replay audit verifies
`proof_kernel_replay_difference_query` again, with 187 proven obligations instead of 160.

## Added: ground congruence closure over the primitive scalar fragment

Before this change the checker had no congruence rule. Equality reasoning was limited to
identifier alias chains, so `a == b` did not prove `a + c == b + c` or `(a < 5) == (b < 5)`.
Every such obligation had to be discharged by hand, which is exactly the bureaucratic plumbing
the design is meant to automate.

The rule lives in the replay kernel (`src/proof/kernel_replay.elisa`), not in the AST producer.
The producer lowers its premises and goal into a scratch arena and calls the same routine that
re-derives the certificate during replay, so it cannot find a congruence the checker cannot
reproduce, and there is one implementation to audit rather than two that can drift.

### Elisa's operators are not unconditionally primitive

The first draft of this rule treated field selection, indexing, and the aggregate constructors as
congruent formers, on the assumption that `==` is Leibniz equality. It is not. Elisa's backend
rewrites `==`, `!=`, `+`, `-`, `*`, `/` and the four ordering operators to a user
`__eq__`/`__add__`/`__cmp__` whenever an operand's type is a struct
(`src/backend/codegen_expr_binary_tail.elisa`), and `Eq`'s `__eq__` is an ordinary method that may
compare a subset of the fields. A struct with

```
impl Eq for Version:
    def __eq__(self: Self, other: Self) -> bool:
        return self.major == other.major
```

made the draft rule certify `p == q |- p.minor == q.minor`, which is false for
`p = {1, 0}`, `q = {1, 5}`. The defect was found by auditing the compiler's dispatch rather than
by a failing test, and the reproducer confirmed it before the rule was narrowed.

The repair restricts the rule to the fragment where the operators are the language's own. The
universe is closed under integer, Boolean and character literals, identifiers carrying a
producer-emitted primitive-scalar type witness, and the arithmetic, comparison, bitwise, logical
and conditional formers over those. A goal outside the fragment declines; a premise outside it
contributes nothing. The witness (`__elisa_primitive_scalar_type`) travels through the same
traced-fact channel as the unsigned width marker, is emitted from declared parameter types
resolved through the existing alias/refinement resolver, and is opaque to every arithmetic tier;
an unsigned width marker is accepted as the same witness. Both bounded-model evaluators were
taught to read a type marker as trivially true, since it holds at every point of a bounded domain
and constrains nothing — without that, adding the marker would have silently disabled bounded
model checking for every function with a scalar parameter.

Soundness now rests on four restrictions, each checked in the kernel:

- Only formers whose result is a function of their operand values participate, and only over
  scalars. `call` also carries no determinism witness; `move`, unary `&`, `is`/`as`, `::`,
  `get … else`, and `quantifier` are excluded for the reasons given in DESIGN rule 13b. A
  quantifier body is never entered, so a bound occurrence cannot join a free term's class.
- A former enters the universe only after all of its operands do, so no term is ever merged on
  the strength of an operand the rule has not accepted.
- Only positive equalities seed the relation. `and` is transparent and `not (a != b)` is the same
  premise; disequalities, order comparisons, and equalities under a disjunction contribute
  nothing. Without a non-trivial merge the rule declines rather than degenerating into the
  structural equality that earlier tiers already decided.
- The rule runs after the existing fixed-width safety guards, so a cross-width equality such as
  `x: u8 == y: u16` cannot travel through a wrapping former.

### Coverage

`examples/congruence.elisa` proves 22 obligations with no replay gap across sums, differences,
products from two premises, nested formers, a class derived by congruence and then equated
further, Boolean and bitwise formers, conditional selection, `char` and `bool` parameters, and
bounded unsigned arithmetic. `examples/rejected_congruence.elisa` requires that twelve adversarial
goals neither prove nor certify: a disequality premise, an order premise, an equality under a
disjunction, an unrelated second operand, a different former, a struct equality premise, an
indexed element, an aggregate construction, congruence through a verified total-pure call, an
equated pair of call results used as operands, a cross-width equality, and a same-width wrapping
sum. `examples/kernel_congruence_runtime.elisa` drives the kernel directly with 37 assertions so
source proof search cannot mask a kernel bug; it runs under stage1 and stage0. Six deliberate
mutations of the kernel were each caught by that harness: dropping the scalar-type witness,
re-admitting `field` as a former, treating `call` as a former, seeding from `!=`, dropping the
selector identity check, and treating unary `&` as a value former.

### Not covered

Field selection, indexing, slicing, and the aggregate constructors need a witness that the
receiver's selector is the language's own and that the selected type's equality is primitive.
That witness is not represented in the term language, so those formers stay excluded and the
adversarial fixture pins the refusal. Congruence through a call additionally needs a determinism
witness. The scalar witness is currently emitted for function parameters only, so a congruence
whose universe includes a local declaration declines.

Auditing operator dispatch for this rule also exposed the same hazard in the pre-existing
reflexivity and identifier-alias tiers, which are not reached by congruence. That is repaired
separately below.

The new routines are also not yet self-verified by the standalone replay audit: only the bounded
accessors and the classification predicates prove there, for the same resource-summary and
unsupported-expression reasons that leave most of the kernel unverified.

## Targeted repairs

### Repaired: non-reflexive comparisons accepted by replay's identity shortcut

The independent kernel's early identity rule used the existence of a comparison negation as
its admission test. This admitted `x < x`, `x > x`, and `x != x` with no premises. A native
reproducer exited with `FALSE_REFLEXIVE_COMPARISON_ADMITTED` before the fix and succeeds after
restricting the rule to `==`, `<=`, and `>=`. The source decision procedure already had the
correct restriction, which is why source-only rejection tests did not catch this kernel flaw.

`examples/kernel_comparison_runtime.elisa` checks all six operators over shared nodes,
distinct equal nodes, and definitionally equal `x + 0` terms, through both public goal replay
and public `decide` tactic replay. It is part of dogfood's native test layer.

Stage1 native tests and the full normal-worktree test matrix pass for this repair; the
shared-front-end build errors noted below did not recur. Snapshot-based dogfood also passes.
The initial stage0 parity attempt could not compile single-line match arms in arena shape
validation (`1: return ...`). These now use ordinary indented match bodies, preserving pattern
matching while allowing the bootstrap parser to read them.

### Repaired: partial range predicates used at hostile-input boundaries

Fourteen replay call sites used `ElisaProofKernelCore::range_valid` to check untrusted slices,
despite that helper's precondition requiring the range to be valid already. Stage0 rejected the
first such call in `proof_kernel_replay_unsigned_marker_info`. All replay references now use
the existing total `proof_kernel_replay_child_range_valid` helper, including structural equality,
substitution, quantifier enumeration, and tactic instantiation. Stage1 test/dogfood suites pass;
the comparison harness also compiles, links, and passes under stage0 with a stage0-built runtime.
Dogfood now performs that targeted bootstrap check whenever stage0 is installed.

### Repaired: stage0 full arena-harness crash

After the syntax/precondition fixes, `examples/kernel_arena_runtime.elisa` compiled under stage0
but exited 139 when linked with stage0-compiled `native_runtime_support.elisa`, while the stage1
harness passed. LLDB placed the invalid read in `proof_kernel_replay_resource_has_pending_join`.
The crash reduced to `examples/kernel_resource_bootstrap_runtime.elisa`: one valid trace that
opens a region, allocates, uses the value, and closes the region. Empty traces did not trigger it.

Cause: `proof_kernel_replay_resource_events` and `proof_kernel_replay_resource_call` are
region-polymorphic (`[@r, @e]`) but took `state: mutable ProofKernelReplayResourceState&` with no
region annotation. Stage0 placed the darray growth performed through that reference in a region
that was released when the callee returned, so the caller's state buffers dangled. Stage1 handles
the same source correctly. Giving the parameter its own region variable (`& @s`) makes the
allocation region explicit and both stages agree; the full arena harness now passes under stage0.
This is a bootstrap-compiler defect, not a prover-logic defect, and stage1 remains authoritative.
Standalone attempts to isolate the pattern outside the replay module are rejected by stage0 with
"darray push requires an active in <arena>: scope" instead of being miscompiled, so the reduced
replay trace is the reproducer. Dogfood now builds the reduced trace and the full arena harness
with stage0 whenever it is installed.

### Repaired: a source-bound tactic could not import an all-positional call

The compiler AST uses either an empty argument-name vector for an all-positional call or one slot
aligned with every argument; `kernel.elisa` states that convention and enforces it. The tactic
script importer instead required a full vector, so reimporting any state whose goal or hypotheses
mentioned a positional call failed with `invalid source-bound proof script` and an `invalid`
initial goal. That included every compiler type marker, which is why the defect had been latent:
the unsigned width marker is a positional call, so a source-bound script could never have
targeted a goal inside an unsigned function either.

`tactic_json.elisa` now applies the same rule as the AST and the certificate encoder: an empty
vector means all-positional, a full vector names every argument, and a partial vector is still
rejected because it would attach names to the wrong arguments. `tactic_script_repair_target.json`
now exercises the path, since its target goal carries a primitive-scalar type marker among its
hypotheses.

### Repaired: a failed conditional case split consumed the goal

Adding congruence exposed a producer/kernel asymmetry. Both tiers eliminate a conditional
expression in a comparison goal by checking both branches, and both then returned that result
directly, so a failed split ended the whole goal. The two tiers disagreed about when the rule
applied: the AST producer matches an `If` operand without stripping parentheses, while the
encoder erases them, so `(c if a < 5 else d) == (c if b < 5 else d)` reached congruence in the
producer and was consumed by the split during replay. The obligation proved and then appeared as
a replay gap.

A failed case split proves nothing either way, so it must not consume the goal. Both tiers now
return only on success and fall through to the later tiers otherwise. This is monotone: it can
only admit goals that a subsequent independently sound rule decides. `examples/congruence.elisa`
regressed to a gap before the fix and replays completely after it.

### Repaired: builds compiled the live compiler working tree

`src/main.elisa` and the executable examples include the compiler's semantic layer through
`../../Elisa-compiler/...`. `build.sh` compiled that path directly, so a half-typed edit in the
sibling checkout entered the proof build; one build in this audit failed on a mid-edit compiler
source and passed on retry, which made the suites depend on an unversioned input.

Repair: `scripts/compiler_snapshot.sh` exports the commit pinned in `ELISA_COMPILER_REV` with
`git archive` into `build/snapshot/Elisa-compiler` and copies `src/` and `examples/` beside it;
`build.sh` and the dogfood harnesses that include compiler sources compile from that snapshot
only. The export is keyed by commit hash and rebuilt when the pin changes; a missing pin,
missing repository, or unknown commit fails the build instead of falling back to the checkout.
Verified by appending a syntax error to the checkout's `semantic.elisa` and rebuilding: the build
succeeded, and both suites pass.

### Repaired: scalar copies out of region-owned references were treated as region aliases

Unmasked by the repair above: once `proof_kernel_replay_resource_events` and
`proof_kernel_replay_resource_call` were resource-checked at all, sixteen
`region-use-after-destroy` findings appeared, and their counterexample status flipped the
standalone audit to `disproved`. Reproducer: `examples/region_scalar_copy.elisa`. A
`usize` declared from `store.names.count` inherited the region of the `@s` reference, was then
reported as an unsupported region alias with a dead live bit, and every later use or rebinding
of that plain integer was flagged as a use after region destruction. A scalar read is a copied
value, not a view into the region. The resource state now records bindings declared with a bare
scalar primitive type, and neither declaration nor assignment propagates a source region into
them. Aliases and refinements are not guessed and keep the conservative behavior. Note that the
report line numbers for the standalone audit are offset by that example's include prologue.

### Repaired: unsigned assumptions entering signed decision procedures

`examples/rejected_unsigned_fact_explosion.elisa` originally certified `x == 0` from
`x: u8 == 255`, `y: u8 == 0`, and `y == x + 1`. These premises describe a real wrapping
execution, but the signed arithmetic tiers treated them as excluding that execution.
The producer and independent replay now check arithmetic safety of premises, not just goals,
before using signed decision procedures. Direct assumption reuse remains admissible.
Subtraction safety uses only plain scalar order facts, so an unchecked modular arithmetic
premise cannot establish its own non-wrapping interpretation.

Regressions cover false-source-goal rejection, bounded-safe arithmetic premises, direct reuse
of a wrapping premise, and direct hostile arena replay without the producer. This repair does
not add modular arithmetic or resolve the separately tracked typed-binding work.

Validation used an isolated copy with both the stage1 compiler and included front end from the
installed snapshot at revision `3c8924aa`. The shared compiler worktree was concurrently edited;
normal builds during this fix encountered parser mutability errors there. Those unrelated edits
were not changed. Snapshot validation does not establish that the moving shared-front-end build
is currently working.

## Repaired: reflexivity and symmetry assumed for user-defined equality

Found while auditing operator dispatch for the congruence rule above.

Elisa rewrites `==`, `!=` and the four ordering operators to a user `__eq__`/`__cmp__` whenever an
operand's type is a struct (`src/backend/codegen_expr_binary_tail.elisa`). There is no built-in
struct equality to fall back on: a struct `==` without `impl Eq` fails to resolve at codegen, and
the semantic pass does not flag it, so elisa-proof saw a clean file. A user `__eq__` is an
ordinary method, so it is not required to be reflexive, symmetric, or coherent with `__cmp__`. An
`__eq__` modelling partial equality — the same shape as IEEE NaN, which this kernel already
excludes for exactly this reason — made `p == p`, `p <= p`, and `q == p` from `p == q` provable
for such a type.

The claim was reachable through five independent inference paths, each concluding that a
comparison holds because its operands denote the same value:

1. `proof_unsigned_goal_identity` and the kernel's identity shortcut in
   `proof_kernel_replay_goal_depth` (`t == t`, `t <= t`, `t >= t`).
2. `proof_linear_goal`'s leading `proof_definitionally_equal` test and the kernel's
   corresponding `proof_kernel_replay_definitionally_equal` site.
3. `proof_linear_goal`'s identifier-alias rule, which turns `proof_names_equal_from_facts` into
   `==`/`<=`/`>=`.
4. The cancellation tier, where `proof_delta_constant` reports a zero difference.
5. The affine and difference-constraint tiers, which close over `==` premises between
   identifiers.

Repair. Each of the five now requires the operand's primitive-type witness when the operand is a
bare identifier, in both the producer and the replay kernel. A richer operand shape is left to the
numeric tiers, which cannot construct an interval for a struct anyway. The witness is the same
`__elisa_primitive_scalar_type` marker introduced for congruence, so no new trust is added; an
unsigned width marker is accepted as the same witness.

Making the gate complete without losing working proofs required the witness to reach every symbol
the producer creates, and to survive the havoc points:

- Scalar locals now carry the marker, like scalar parameters.
- A counting-range loop binder carries it: the range endpoints are integers, which is the same
  semantic source as the two bounds already recorded for the binder.
- `proof_type_bound_name` recognizes the marker, so it survives every havoc that keeps type
  bounds, rather than being dropped at the first call or control-flow join.
- `proof_invalidate_moved_roots` cleared the whole fact set, which discarded an unrelated
  binding's declared type after a move. It now keeps the traced type bounds of live, unmoved
  names, matching the retention rule already used at call and control-flow havoc points.
- The filtered order-fact set used by unsigned subtraction safety carries the markers across, so
  the gated order tier can still see them. Without this, `usize` subtraction under an explicit
  `a <= b` precondition stopped being range-safe and `examples/unsigned_local.elisa` regressed.

Coverage. `examples/rejected_reflexivity.elisa` requires that five goals neither prove nor
certify: reflexive `==`, `<=` and `>=` on a struct parameter, symmetry from an equality premise
between two struct parameters, and reflexive `==` on a struct local.
`examples/kernel_comparison_runtime.elisa` now supplies the witness for its six operator checks
and additionally requires that the three true comparisons are refused without it, so the kernel
is exercised directly. A mutation making the witness unconditional is caught by that harness.

Left open at the time. The gate covered only a bare identifier; any other operand shape was
admitted without a witness. That residue is closed in the next section.

## Repaired: non-identifier operands admitted without a type witness

The reflexivity gate above asked for a witness only when the operand was a bare identifier;
every other shape passed. `examples/kernel_comparison_runtime.elisa` and the adversarial
fixture only pinned the identifier case, so the residue was recorded rather than caught by a
test. Probing it directly showed `h.part == h.part`, `h.parts[0] == h.parts[0]` and
`h.part <= h.part` proved with kernel-backed certificates for a struct-typed `part`, and
`examples/quantifier_structural_terms.elisa` had been asserting `[value] == [value]`,
`Pair{...} == Pair{...}`, tuple and dictionary equalities as theorems. Compiling such a
comparison confirmed the language's position: "aggregate values do not support ==; compare
their contents explicitly". Those obligations were not merely unproven propositions; they were
propositions no Elisa program can state.

Repair, kernel side. `proof_kernel_replay_primitive_comparison` now requires both operands of
the identity, definitional, affine and difference tiers to satisfy
`proof_kernel_replay_scalar_term_witnessed`, and the congruence closure admits an atom only
under the same relation. The relation is closed: a scalar literal; a `__elisa_primitive_scalar_type`
marker whose argument is structurally equal to the term; an `index`/`index-n` term reaching
exactly the depth of a `__elisa_primitive_scalar_element(container, depth)` marker over
witnessed subscripts; or a former with a primitive operator over witnessed operands. There is no
default case. The marker readers validate the call shape, the argument arity, and the depth
literal's range.

Repair, producer side. The gap could not be closed by refusal alone without losing legitimate
proofs, so the producer now resolves expression-level types from the compiler's declarations:
each scalar field of a struct-typed parameter or local (recursively through struct-typed
fields to depth three, under a per-binding budget of twelve witnesses), the `count` of a
built-in container, and the container's element depth from `darray[T]`, `view[T]`,
`array[T, N]` and `T[N]` spellings — never from a struct, whose subscript is an `__index__`
call. A `const enum` resolves as a scalar; a plain enum does not. A call is witnessed only for
a verified total-pure callee whose declared return type is a scalar, over witnessed arguments,
because that classification is what makes two occurrences of the call one value. Retention
follows the root symbol of the witnessed place, so a field witness dies with its binding and
survives the havoc points that keep type bounds.

Two adjacent defects surfaced while restoring completeness and were fixed in the same change.
The error arm of an expression-position `catch` cleared every fact, including type bounds, and
so did a value arm whose expression contained an unapplied call; both now keep type bounds like
every other havoc point. A signed scalar local bound to an opaque initializer substituted
`invalid` for its own name, so `reading == reading` was decided over two copies of nothing; it
is now kept as its own symbol, exactly as an unsigned local already was, with no binding fact.
That made `examples/rejected_unknown_assert_reuse.elisa` prove: a local bound once to an opaque
call, asserted, and returned unchanged is one execution, and the unsigned spelling of the same
program was already accepted. The fixture now pins the two genuine hazards — reusing the call
term itself, and a binding reassigned after the assertion — and the accepted shape moved to
`expression_witness.elisa`.

Consequences. Aggregate equality is refused everywhere; `examples/constructor_kernel.elisa`
and `examples/quantifier_structural_terms.elisa` were rewritten to project a scalar out of the
aggregate or to pass it to a verified pure function, where only an exact child graph lets the
hypothesis contain the goal; `examples/slice_kernel.elisa` now asserts that its slice forms
lower into the arena and are refused; and the refused aggregate forms live in
`examples/rejected_aggregate_equality.elisa`. The projection is reduced before lowering, so
quantified substitution through `construct`, `field-init` and `record-update` nodes lost its
end-to-end fixture; `examples/kernel_arena_runtime.elisa` now covers it natively by containment,
with a wrong field value, a wrong field name, and a wrong update base each required to fail, and
its nested-call case was likewise moved from call reflexivity to containment with a negative
control. `call_result_operand` moved from
`rejected_congruence.elisa` to `congruence.elisa`: an equated pair of verified pure call
results over witnessed arguments legitimately travels through arithmetic, which is a different
claim from carrying an equality *through* a call, still refused as `call_congruence`.

Coverage. `examples/expression_witness.elisa` proves twenty-nine obligations across struct
fields, nested fields, a field through a reference, elements, `count`, two-dimensional
subscripts in both spellings, field and element congruence, a struct local, a `const enum`, a
verified pure call, and an opaque-call-bound local. `examples/rejected_reflexivity.elisa` adds
a struct field under `==` and `<=`, a struct element, and an opaque call. The native harness
gained twelve cases: an unwitnessed field, a witnessed field, a witness on a different field of
the same root, an unwitnessed element, a witnessed element, an unwitnessed subscript, a depth-1
marker against a depth-2 subscript and the reverse, a call with and without its exact witness,
and a former with and without operand witnesses. Five deliberate kernel mutations — an
unconditional gate, a marker matching any term, a subscript ignoring depth, a subscript not
collected, and a former admitted without operand witnesses — each make the harness exit with a
distinct code.

Loop binders. A binder is represented by its own proof atom `(name, offset)`, and the first
version of this change keyed the counting-range witness by the bare spelling, which no goal ever
contains: `for i in 0 ..< n: proof i == i` had been admitted only through tuple reflexivity and
so regressed to unproven. The witness is now keyed by the atom, retention follows the atom's
name, and a binder over a container whose element witness has depth one inherits the scalar
witness, so `for v in values: proof v == v` and congruence through `v` are proved. A binder over
a container of structs binds an aggregate and stays unwitnessed; its fields are not witnessed
either, because the element's declared type is not carried through the element marker.

Not covered. Type resolution stops at what the producer can see: the fields of a struct-typed
loop binder, a pattern binder from a struct pattern except through its substituted place, and a
field of a call result all decline. The witness budget and depth are fixed constants and their
exhaustion is silent.

## Added: exhausted searches are reported as timeouts

A goal whose search ran out of budget was reported with the same `unknown` status as a goal no
rule applied to. `examples/rejected_quantifier.elisa` already contained a `too_large_bounded_forall`
case that was reported this way, so the two states had been collapsed since that fixture was
written. An agent repairing the first should shrink the range or supply a lemma; an agent
repairing the second needs a different specification.

The decision procedures now thread an advisory exhaustion flag out of the quantifier range-width
and instance-count limits, the quantifier nesting cap, and bounded model checking's per-name and
product-domain limits. `proof_certify_goal_with_rule` records it on the goal attempt, and
`proof_add_goal_failure` reclassifies the diagnostic from `unknown` to `timeout` — but only when
no counterexample was found, so a refuted goal keeps the stronger `disproved` answer.

The flag is observational and cannot widen admission: an exhausted attempt is unproven exactly as
before, no certificate is emitted for it, and the replay kernel is unchanged. `proof_goal` keeps
its old signature and discards the flag, so the tactic and resource callers are unaffected.

Coverage. `examples/rejected_budget.elisa` requires all four states from one file: two exhausted
searches (a quantifier range wider than the instantiation budget, and a bounded-model product
domain wider than the enumeration limit), one goal no rule decides, and one refuted goal with a
counterexample. The test matrix additionally requires the focused-goal API to report the exhausted
goal as `timeout` with no counterexample.

Extended. The congruence term and saturation-round budgets and the case-split depth cap now
report exhaustion too. The kernel's term budget is enforced in one routine,
`proof_kernel_replay_congruence_push`, and saturation records whether its last round was still
merging classes when the round budget ended the loop; both feed an advisory flag returned by
`proof_kernel_replay_congruence_report_status`, which the producer threads into the same
exhaustion channel. The producer also reports a disjunctive premise or a conditional operand
that the split budget refused to open. `examples/rejected_budget.elisa` gains four `timeout`
cases — a goal wider than the term budget, nine layers of top-down premises that need more
saturation rounds than the budget grants, a fifth disjunction, and a fifth nested conditional —
and `examples/kernel_congruence_runtime.elisa` requires the flag on the first two and requires
it clear on a decided goal. Removing either kernel report, or lifting the round limit so the
layered goal is admitted, each makes the harness exit with a distinct code.

Not covered. The kernel-side replay budgets do not report exhaustion: a certificate that replay
cannot re-derive within budget is a replay gap, indistinguishable from one whose rule does not
apply. The witness budget and depth for expression-level type witnesses are silent as well. The
report's `trusted_assumptions` list remains empty, which is currently accurate: compiler-derived
inputs are counted separately as boundary facts rather than as assumptions inside a proof.

## Added: declared effect containment

Elisa functions carry an effect row (`can[...]`), and the checker imported nothing from it. A row
is a specification an agent can read and reason about, so leaving it out meant the proof surface
silently ignored a declared property of every function it checked.

The row is now imported into the declaration summaries, into the JSON `effects` field, and into
the function table, and a new obligation is checked for every function that writes one: the
declared row must cover the declared row of each function it calls. The accepted containment is
lowered into `effect`, `effect-row`, `effect-call` and `effect-containment` nodes and re-derived
by an independent kernel rule that runs with an empty fact set, so nothing about the containment
rests on the AST pass that produced it.

What the claim is. Exactly: the declared rows of this function's callees are members of this
function's declared row. It is not a claim that the body performs only those effects. An effect
performed directly by the body, without going through an imported call, is the compiler effect
checker's obligation and remains outside this system. A function with no written row makes no
claim and is not checked.

Fail-closed cases are kept distinct rather than collapsed into a refusal. A callee whose row was
never imported yields `effect-call-opaque` with status `unsupported` — a missing row is not read
as an empty one. An abstract row, whose members are not concrete names, yields
`effect-row-abstract`: it has no comparable members, so containment is meaningless rather than
false. An imported callee whose row has a member the caller's row lacks yields
`effect-row-exceeded` with status `disproved`. In each of those three cases no certificate is
emitted, so nothing enters the replayed evidence stream.

Coverage. `examples/effect_containment.elisa` proves fifteen containments with no replay gaps.
`examples/rejected_effect_containment.elisa` pins one instance of each of the three refusals and
requires that none of the three produces a certificate. `examples/kernel_effect_runtime.elisa` is
a native harness that drives the kernel rule directly and is built under both stage1 and stage0;
deliberately mutating the containment test in the kernel makes it exit non-zero.

## Added: facts that a call or a branch cannot falsify

Every call to a callee without a `changes` frame discarded all of the caller's facts except
compiler type bounds, whether the callee was opaque or a verified summary. That is correct but far
stronger than the language requires, and it made a very common shape unprovable: a bounded
recursion whose guard establishes `depth < 127`, and whose *second* recursive call therefore has
nothing left to establish `depth + 1 <= 127` with. On `examples/kernel_replay_standalone.elisa`
this accounted for the large majority of unproven obligations.

A callee reaches its caller's state only through references and globals. A fact is therefore
*call-stable* for a frame when it is built only from literals and by-value scalar locals and
parameters of that frame whose names the body never references — never takes an address of, moves,
allocates into a region, uses as a method receiver, or passes as a bare argument either to a
reference parameter or to a callee whose signature is not imported. `proof_collect_aliased_names`
computes that name set once per function, before symbolic execution; a lambda anywhere in the body
pushes a `*` sentinel that disables the analysis for the whole function, and the set is tagged with
its owner so a stale set can never be consulted. `proof_expr_call_stable` then admits literals,
const-enum shorthands, loop-binder atoms, and primitive formers over those, and requires a positive
primitive-scalar witness on every name — the same witness relation that gates equality reasoning.

Three places now retain that class of fact instead of dropping it: `proof_clear_facts_after_call`
(opaque-call havoc), the frame havoc inside `proof_apply_function` (verified callees without a
`changes` frame), and `proof_check_frame_calls_in_expression` (a call nested in a larger
expression). A branch join re-imports it too: when one arm falls through, from that arm, and when
both do, only from facts standing at the exit of both. An arm that assigns to a scalar has already
purged the facts over it, so a direct write inside a branch cannot come back this way, and a fact
mentioning an arm-local binding is not call-stable for the enclosing frame and cannot leak out.

Conjunctive guards needed one more step. `return empty if not valid(x) or depth >= 127` negates to
a conjunction whose left half mentions the call and whose right half is over `depth` alone; the
whole is not call-stable, so all of it was lost. `proof_add_branch_condition_facts` now records,
beside the condition, each part the condition entails — through `and`, through `not (a or b)`, and
through double negation, but never through `not (a and b)`, which is a disjunction. Each part is a
`branch-conjunct` **derived** fact: `proof_add_derived_fact_from` records the condition as its sole
premise, and replay re-proves the part from that premise rather than accepting a second assumption.

The kernel gained the matching rule. `proof_kernel_replay_fact_contains` was a one-directional walk
that projected out of conjunctions and cancelled double negations; it is now
`proof_kernel_replay_fact_contains_signed`, a single walk carrying a sign. Unnegated it projects
out of `and`; negated it projects out of `or`; a `not` flips the sign. All three are classical, and
the proposition shape of every fact and goal is already checked before the walk runs. The duals —
a disjunct out of `or`, a negated conjunct out of `not (a and b)` — have no rule and stay refused.

Nothing here weakens the trust boundary: no new assumption kind is admitted as an axiom,
`branch-conjunct` is validated on the derived-fact path in both the source and the source-neutral
trace validators, and every certificate is still replayed. On the kernel's own source the proven
count moved from 205 to 757 obligations with replay gaps unchanged at zero.

Coverage. `examples/call_stable_facts.elisa` proves six shapes with no findings and no gaps: a
state-writing call, two of them in a row, a bare-call guard, a branch that binds a local, a branch
that returns, and a guard whose conjunct is the only thing strong enough to close the goal.
Disabling any one of the four retention points — the two call-havoc restores, the branch-join
restore, or the conjunct split — leaves a distinct subset of it unproven.
`examples/rejected_call_stable_facts.elisa` pins the boundary: a scalar handed to a callee by
reference, a scalar a branch assigns, a scalar rebound after its guard, and the two disjunctive
shapes are all refused, each with a diagnostic and no certificate.
`examples/kernel_projection_runtime.elisa` drives the kernel rule directly under both stage1 and
stage0, and five separate mutations of the signed walk — dropping the negated-`or` rule, dropping
the sign flip, ignoring the sign on `and`, ignoring it on `or`, and accepting any negated goal —
each make it exit with a distinct code.

Not covered. Call stability is a syntactic over-approximation: a fact over a struct field, a
container element, or a scalar that is merely *mentioned* in an argument list is dropped even when
the callee provably cannot write it. Global state is assumed reachable by every callee, so no fact
over a global is ever retained. The conjunct split is applied to `if` conditions only; `match`
patterns and guards still record their conditions whole.

## Added: lending a reference the caller already holds needs no callee summary

A call that passed any capability required the callee's own converged `resource-safety` trace, and
a recursive component can never have one — it would be consuming a summary it is still computing.
Every recursive walk over a shared `darray[T]&` was therefore `borrow-call-opaque`, 622 of them on
`examples/kernel_replay_standalone.elisa` alone, and the diagnostic cascaded: a callee that failed
for any reason emitted no summary, so all of its callers failed too.

The summary is not what a lend needs. Elisa forbids moving out of a reference, and the capability
the callee receives ends with the call, so a *shared* lend leaves the caller's bindings, borrows
and regions exactly as they were. An *exclusive* lend is bounded just as tightly, and the kernel
itself says by how much: the summary composer refuses any callee effect that is not a `write`
rooted at a mutable formal. A write to the whole lent place therefore subsumes every effect any
summary for that callee could ever have exported, so the caller can take it without seeing one.

`proof_resource_call_is_confined_lend` admits a call when no argument is a `move`, a `new[r]`
allocation or an opaque borrow, its return type is neither a reference nor region-bound, every
by-value formal receives a value, every shared formal's place has no overlapping live mutable
borrow, every exclusive formal's place is one the caller may write with no overlapping live borrow
at all, and two lent places overlap only when neither is exclusive.

A lifetime parameter does not stop this. A region-polymorphic callee may allocate into a mapped
caller region, which the caller cannot observe, and it can never close one: a lifetime parameter is
external in the callee's own frame and no certificate may close an external region. What it stores
through an exclusive formal is bounded exactly as on the summary path, which also composes a callee
write without inspecting the written value — the compiler's lifetime typing, not the resource
layer, is what keeps a shorter-lived reference out of a longer-lived place, on both paths alike. So
the added obligation is the pinning itself: every formal lifetime must resolve to a caller region
active at the call, and every actual carrying a region must land on a formal declared with that
same lifetime. `proof_resource_collect_call_regions` enforces both directions, including for a
callee with no lifetime parameters, where any region-carrying actual is refused outright. The premise is the callee's declared parameter and return modes:
compiler-typing metadata, imported exactly the way the resource header already imports the current
function's own parameter modes.

The call does not disappear from the certificate. `proof_resource_record_lend_call` emits a
`resource-call-lend` event whose children are the actuals followed by the callee's declared mode
for each of the same formals, one pair per parameter, and `proof_kernel_replay_resource_lend`
re-derives every permission from them rather than trusting the producer: the node carries no callee
summary root, its child list is exactly twice its parameter count plus its lifetime count, each
actual is a `resource-call-arg` decoded by the same routine the summary path uses, each mode is a
`resource-call-formal` whose name matches its actual and whose secondary name is its declared
lifetime, a by-value formal receives no capability at all, a fresh region allocation is refused,
every lifetime is pinned once to a region active in the replayed state and to the lent binding's
own region, the exclusive-lend permissions and the pairwise disjointness are checked against that
state, and the event root is consumed once. A shared
formal writes nothing; an exclusive one pushes a whole-place `write` effect through the same
origin-resolution the direct write path uses.

Pairing the modes with the actuals by formal name stops a permuted list from letting a scalar
parameter's harmless mode stand in for the parameter that receives the place. Only the three modes
whose caller-side permission the kernel can re-derive have an encoding, so nothing else can be
smuggled in.

Shared and exclusive access to one place cannot be live at the same time, so the rule also refuses
a lend whose place is overlapped by a live borrow, on both sides. Unlike the summary path it
excludes nothing: there the summary establishes that the callee touches the place only through the
very reference being reborrowed, and here there is no summary to establish it, so every live
conflicting borrow of the lent place refuses the rule. The narrower reborrow-lend that this gives
up is not reachable from the current producer — such a call has a summary and takes the summary
path.

The summary path is unchanged and still preferred: the lend rule is consulted only when no mapped
callee summary is available. An escaping result keeps its existing diagnostic. On the kernel's own
source the proven count moved from 757 to 885 of 2023, `borrow-call-opaque` from 622 to 204 and
`region-call-opaque` from 280 to 252, with replay gaps unchanged at zero and 358 lend events
recorded, 178 of them carrying an exclusive formal and 32 a lifetime map.

Coverage. `examples/shared_borrow_calls.elisa` proves self-recursion over a shared collection, two
shared references at once, a mutable holder lending a shared reborrow, the same place lent twice in
one call, and a call to a callee with no summary of its own. `examples/writable_lend_calls.elisa`
proves self-recursion that writes through a mutable reference parameter, an exclusive lend beside a
shared one, two exclusive lends of disjoint places, and callers that own the lent value outright.
`examples/rejected_shared_borrow_calls.elisa` and `examples/rejected_writable_lend_calls.elisa` pin
the boundary: a callee that returns a reference, a moved binding, a shared lend across a live
exclusive borrow, the same place lent exclusively twice, a shared lend beside an exclusive lend of
the same place, and an exclusive lend across a live borrow are each refused with a diagnostic and
emit no event. Disabling the producer's pairwise-overlap check admits the two aliasing cases and
nothing else; disabling its exclusive-borrow check admits the third and nothing else.
`examples/region_lend_calls.elisa` proves a region-polymorphic recursive read and a two-lifetime
call lending one place shared and one exclusively; `examples/rejected_region_lend_calls.elisa`
refuses a lifetime with no actual to pin it and a region value reaching a formal that declares
none. `examples/rejected_borrow_call.elisa` now records that neither caller is opaque any more
while the callee's own indexed obligation still fails and both callers are reported as depending on
an unverified summary.

`examples/kernel_resource_bootstrap_runtime.elisa` drives the kernel rule directly under stage1 and
stage0 with eighteen cases — three admitted lends, one shared, one exclusive and one lifetime-
pinned, then a moved place,
a capability handed to a by-value formal, a miscounted child list, a reused event root, an unbound
place, a permuted mode list, a shared lend across a live exclusive borrow, a fresh region
allocation, an exclusive lend of a place the caller may not write, the same place lent exclusively
twice, a shared lend beside an exclusive one over the same place, and an exclusive lend across a
live borrow, a lifetime pinned to a region that is not active, a lent place whose own region is not
the one its lifetime is pinned to, and a formal lifetime pinned twice, each refused. Removing the
shared or exclusive borrow-overlap check, the name pairing, the by-value-formal check, the
writable-permission check, the lifetime pin, the duplicate-lifetime check, or either half of the
pairwise rule each makes it exit with the matching code; the miscount, region-allocation,
exclusive-formal-shape and dead-lifetime cases are each caught by two independent checks and need
both removed before they show.

Not covered. The remaining 204 `borrow-call-opaque` are calls the rule refuses on purpose or cannot
reach: a lent place that is already borrowed, two overlapping lent places, an escaping reference
result, and a `borrow-opaque` actual whose place the producer cannot name. The whole-place write is
deliberately coarse: a callee that writes one field of a lent struct is recorded as writing all of
it, which can conflict with a `preserves` clause that a real summary would have satisfied.

The 252 remaining `region-call-opaque` are dominated by one shape the rule cannot reach: a *local*
lent to a lifetime-annotated formal. `proof_kernel_replay_resource_events(nodes, children, roots,
&callee_state, &callee_effects, depth + 1)` lends `&callee_state`, a frame local with no region, to
`state: mutable ProofKernelReplayResourceState& @s`, and `proof_resource_collect_call_regions`
finds no actual carrying `@s` to pin it to. Closing this needs a frame lifetime — a notion that a
local's own extent instantiates a formal lifetime for the duration of the call — which the resource
state does not model today.

The callee's declared modes remain a compiler-typing import: the kernel checks that the recorded
modes are ones it can re-derive permissions for, that they pair with the actuals, and that every
permission holds in the replayed state, but nothing in the arena ties them back to the callee's
source — a producer that misreads a signature records a wrong but internally consistent claim.
Closing that needs the callee's parameter header in the arena, keyed so it cannot be mistaken for a
converged summary; for a self-recursive call, which is the case the rule exists to serve, the
header is already present as the resource root being replayed.

## Fixed: a constructed type read as a runtime value

A call to a region-polymorphic callee that *did* have a converged summary was admitted by the
producer and refused by the replay kernel, so the caller's certificate came back as a replay gap
and the verdict degraded to `proved_with_replay_gaps`. Minimal reproducer:

```elisa
struct Cell:
    value: mutable i64

def peek[@r](cell: Cell& @r) -> i64:
    return cell.value

def region_reader() -> i64 can[Memory.Allocate, Abort.Panic]:
    region r(4096):
        cell: Cell& = new[r] Cell{value: 3}
        return peek(cell)
```

The cause was not in the call composition at all. `resource-region-alloc` requires the allocated
value to carry no lifetime of its own, and `proof_kernel_replay_resource_value_term_has_no_region`
walked a `construct` node's left edge as a value term. That edge is the constructed *type*: the
encoder puts the type expression there, unlike a `record-update`, whose left edge really is the
base record being copied. So the walk looked the type name `Cell` up as a binding, found none, and
refused — meaning every struct literal allocated into a region was unreplayable. It stayed hidden
because almost no region-polymorphic callee ever obtained a summary for a caller to compose, and
because the shape only fails at the *caller*: the callee's own certificate replays.

`proof_kernel_replay_resource_type_term` now decides that edge instead. A type expression denotes
no runtime value and so carries no lifetime; the constructed value's lifetime comes from the
allocation holding it. Only a plain or qualified type name is accepted, so a region-parameterized
or otherwise unrecognized form is refused rather than assumed lifetime-free. The field values,
where a foreign lifetime could actually hide, are still walked one by one, and `record-update`
still checks its base as the value it is. A `call` node's left edge is deliberately left alone:
it is refused today because a callee name is not a binding, and loosening it without the callee's
return region in hand would admit `new[r] f(x)` where `f` returns a longer-lived reference.

Coverage. `examples/region_call_summary.elisa` proves the reproducer and a record update allocated
into the same region, with replay gaps at zero and `construct`, `record-update`,
`resource-region-alloc` and `resource-call` all present in the arena.
`examples/kernel_resource_bootstrap_runtime.elisa` adds three cases: a struct literal allocated
into a region is admitted, the same literal with a field value belonging to another region is
refused, and a construction whose left edge is not a type name is refused. Removing the type-term
rule or the field walk each makes it exit with the matching code. On the kernel's own source the
proven count moved from 885 to 891, with replay gaps unchanged at zero.

## Added: an executable call in a branch condition need not sit at the root

A statement whose expressions the checker cannot model does not merely go unproven: it invalidates
the path. `proof_statement_expressions_supported` gated a branch condition carrying an executable
call on `proof_expr_is_call_rooted` — the whole condition had to *be* the call. So `if f(x):` was
modelled and `if not f(x):` was `expression-unsupported`, along with `if f(x) < n:` and every other
shape where the call sat under an operator. On the kernel's own source that was the largest
non-resource gap: 251 findings, and the dominant shape was `return false if not <call>(...)`.

The root restriction was conservatism, not a requirement. The `if` handler already frames every
call in the condition, forgets symbolic values, and clears unstable facts on *both* arms before
recording the branch fact — which is exactly the model of a call that certainly happened. What it
does not model is a call that might not happen, so `proof_runtime_calls_evaluate_unconditionally`
admits a call only where evaluation is unconditional: under `not`, under a comparison or
arithmetic, in an index or a slice, in a call's own arguments, and on the left of `and`/`or`. On
the *right* of a short-circuit only a pure call is admitted, because there is no effect to skip.
Every shape the walk does not reason about explicitly falls through to "contains no executable
call", so an unrecognized form is refused rather than assumed to run.

The gate is deliberately narrow. `while`, `for`, `match`, `catch` and `assert` keep the old
root-only rule: an assertion publishes its expression as a fact through a path that hands back the
pre-call symbolic value, so widening it there proved
`examples/rejected_assert_nested_call.elisa`'s goal — a false claim that the test matrix caught
before the change shipped. Those forms are separate work, each needing its own handler audited.

Two calls of one impure function are not one term, and nothing here changes that. A guard naming
an impure call records a fact naming that call; a later obligation naming the same call is a
*different* call and is not discharged by it. `examples/rejected_condition_call_positions.elisa`
pins both directions: `bound_after_guard` and `stored_before_guard` each guard on `next(counter)`
and then index with a second `next(counter)`, and both keep `index-upper-unproven`.

On the kernel's own source `expression-unsupported` moved from 251 to 182 and
`function-summary-unverified` from 177 to 172, with replay gaps unchanged at zero.

Coverage. `examples/condition_call_positions.elisa` proves a bare call, a negated call, a compared
call, a call under arithmetic, an impure call beside a pure one across `and`, and the sound
reuse pattern of binding the result to a local before the guard.
`examples/rejected_condition_call_positions.elisa` refuses an impure call on the right of `and`
and of `or`, one inside a ternary, one inside a struct literal the walk does not recognize, and
the two repeated-call index shapes. Removing the short-circuit clause admits the first two;
`rejected_assert_nested_call` guards the statement forms that were left alone.

## Added: a goal rendered as an Elisa-like proof a person can read

Every surface for reading a result was machine-shaped: `--json`, `--goal`, `--theorems`,
`--suggest` all return structured trees. A reviewer who wanted to see *why* a goal holds had to
reassemble the proposition, its hypotheses and their origins out of nested JSON. `--proof <id>`
now renders one goal directly:

```
# elisa-proof-proof-v1
# source: fingerprint fnv1a32=834510316, complete=true, admissible=true
# goal 11 of 12, rule index-upper, in guarded_index at line 56
proof guarded_index_11:
    given measure(counter) >= 1    # function-summary, line 54, via measure
    given index == measure(counter)    # local-binding, line 54
    given index < values.count    # branch-condition, line 55
    show index < values.count
    by kernel certificate 11, arena root 473
qed
```

This is a *view of recorded evidence*, not a second proof. The hypotheses are exactly the goal's
certificate facts in order, each annotated with the origin the replay layer already records; the
conclusion is exactly the goal proposition; the justification names the certificate that replayed
and the arena root it replayed against. Nothing is inferred and no step is invented.

The block keyword carries the verdict, and only one of the three means the kernel checked it:
`proof ... qed` for a goal that is proven *and* whose certificate replayed, `unchecked` for one the
producer proved with no replayed certificate, and `open` for an unproven goal, which prints the
recorded failure kind, status and message instead of a proof. So the most human-facing surface
cannot overstate a verdict by omission: a reader who sees no `qed` has been told so.

`proof_push_elisa_expr` spells expressions back into source syntax. It decides nothing and is never
read back as evidence, so a form it does not model prints as an explicit `<unprinted expression>`
marker rather than as plausible-looking source, and a nested binary or ternary is always
parenthesized so the printed form is unambiguous without a precedence table that could drift from
the parser's.

Coverage. The test matrix pins the three shapes and the exit codes: a proved goal renders
`proof ... qed` with its `show` line, its `by kernel certificate` line and its branch-condition
hypothesis; an unproven goal renders `open` with an `unproved:` line and contains neither `proof`
nor `qed`; a goal id past the end exits `2` and renders no block. Dogfood then checks the
invariant *exhaustively* rather than by sample: for every goal of four fixtures it renders the
block and requires `qed` to appear exactly when the report says the goal is proven and its
certificate replayed, `open` with a failure line whenever it is unproven, one `show` line, and a
`given` count equal to the goal's recorded fact count.

`--check-proof <block> <file.elisa>` reads a rendered block back and checks it against the source
it names. The file is untrusted input: nothing in it is believed and no part of it decides
anything. The checker re-renders the canonical block for the goal the file's own header claims and
compares the two line by line, reporting every divergence with its line number, what the report
supports, and what the file says. So an edited keyword, an invented hypothesis, a swapped
conclusion, a renumbered certificate and a block taken from a different source all surface the same
way, and a block that names no goal of this source is refused rather than passed. Exit `0` means
the block matches what the report supports, `1` that it diverges, `2` that it could not be checked
at all.

Coverage. The test matrix renders a proved goal and checks it clean, then pins four tampering
shapes: an inserted `given`, an `open` block rewritten to `proof ... qed`, a block checked against
another source, and a file with no goal header — with the expected exit code and the specific
divergence entry for each. Dogfood then does the round trip exhaustively: for every goal of two
fixtures it renders the block, requires it to check clean, and then appends a marker to *each line
in turn* and requires every one of those mutations to be reported. A checker that accepted an
edited block would make the readable surface forgeable, so this is checked per line rather than by
sample.

`--script <block> <file.elisa>` closes the authoring half. It reads a proof written in the same
shape `--proof` renders and runs it, so a person can propose *a different* proof of the same goal
rather than only compare against the recorded one. The front end is untrusted elaboration and
nothing else: it translates the text into the `elisa-proof-tactics-v1` interchange that the checked
tactic engine already consumes and hands it to exactly that path, gaining no route of its own. A
text script and its JSON equivalent produce byte-identical output, which both suites assert by
comparing the two runs.

The grammar is deliberately thin. `by <action>` and `by <action> <index>` lines are the steps; the
`proof`/`open`/`unchecked` header, `given`, `show`, `unproved:` and `qed` lines are documentation
and carry no weight, because a source-bound script takes its hypotheses and its conclusion from the
goal itself. A line matching none of those refuses the whole script rather than being skipped, so a
typo cannot quietly become a shorter proof than the author wrote, and a script with no steps is
refused rather than treated as a proof of nothing.

Coverage. The test matrix asserts the text and JSON paths agree byte for byte and pins four refusal
shapes. Dogfood adds two more — a step with trailing text, and a script with no goal header — and
checks the property that matters most for a writable surface: an invented `given` line changes
neither the tactic result nor the state the engine started from, so writing a hypothesis into the
file does not make it an assumption.

`--repair <id> <file.elisa>` closes the loop. It searches a bounded, fixed vocabulary of tactic
scripts for one that closes the goal and emits the winner in the shape `--script` runs, so the
cycle is: report names a broken goal, repair proposes a proof, script runs it, kernel replays it.

The search is untrusted automation and is structured so that it can only ever propose. A candidate
is admitted solely when the checked engine reports `valid`, `solved`, `kernel_replayed` *and*
`certificate_replayed` — the same four gates a hand-written script passes, checked in the same
engine, with no path of its own. The vocabulary is a literal table of twenty argument-free action
sequences tried in a fixed order, so a repair is reproducible byte for byte, and the response
states `candidates`, `tried` and `exhaustive` rather than a heuristic budget: a success is
explicitly a bounded one. A failure is reported as `unrepaired`, which says the fixed vocabulary
contained no proof and deliberately does *not* say the goal is false — that distinction is the
difference between "unknown" and "disproved", and the report keeps them apart.

Coverage. The test matrix repairs a goal, requires the emitted script to re-run through `--script`
and come back solved with the kernel replaying its certificate, requires two runs to be
byte-identical, and requires a missing goal id to exit `2` with no script. It then requires each of
the three goals of `examples/rejected_repair_target.elisa` — a conclusion unrelated to its
hypotheses, one that reverses an inequality, and one needing arithmetic the vocabulary does not
have — to come back `unrepaired`, exhaustive, with `tried == candidates` and no script.

Dogfood checks the property across whole files rather than at sampled goals: for every goal of a
proved fixture and of the adversarial one, a repair reporting success must emit a script that
re-runs and replays, a repair reporting failure must emit none and exit non-zero, and no goal of
the adversarial fixture may be repaired at all. A proposal that could not be re-checked would be a
claim rather than a proof, so the re-check is what the test asserts, not the search's own verdict.

`--repair-all <file.elisa>` walks the whole unresolved queue in one pass. It repairs nothing the
checker already proved — only goals the report still reports as open are tried — reports each one
separately with its own verdict and script, and takes its own verdict as the conjunction: a file
with any unrepaired goal is `partial` and exits non-zero, a file with none is `nothing_to_repair`.
Dogfood pins the property that makes the batch trustworthy: the goals it walks are exactly the
report's unresolved ones, and for each of them `--repair-all` and `--repair` must agree on both the
verdict and the script, so neither can report something the engine did not decide.

Not covered. No fixture currently has a goal that is proven without a replayed certificate, so the
`unchecked` keyword is exercised by the renderer's logic but not by a live example. More
significantly, **no fixture has an open goal that the bounded vocabulary can close**: the source
checker is strong enough that the goals it leaves open are, so far, also out of reach of twenty
argument-free tactic sequences. So `repaired` is demonstrated on goals the checker had already
proved, and the batch's `partial` path is demonstrated but its all-repaired path is not.

That is not a statement about the vocabulary's size, and widening it would not help. The reason is
structural, and it was measured rather than assumed. A lemma can only close a goal the checker
cannot close inline when the checker can prove the lemma's statement *standalone* — with induction
or recursion — but not in the goal's context. Otherwise the composition collapses: the goal's facts
discharge the lemma's premises, the lemma's premises give its conclusion, and a checker that proves
both halves proves the whole thing directly, so the lemma is redundant exactly where it would have
been needed.

Probing that boundary found no case on either side of it. `n * m >= 0` from `n >= 0, m >= 0` is
beyond the checker inline; written as a recursive lemma with `decreases n` it is *also* beyond it,
because the inductive step needs distributivity to relate `n * m` to `(n - 1) * m + m`. The lemma
therefore fails its own `ensure`, is not verified, and cannot be applied — a lemma that could
repair the goal would have to be provable, and the same missing arithmetic blocks both.

So the repair gap is a checker-strength gap, not a search gap. What would move it is a proof
method the checker does not have — nonlinear arithmetic, or induction that can rewrite under a
recursive call — which is where a solver portfolio or a bounded bit-precise checker would pay for
itself concretely rather than as a wish. Until one exists, enlarging the repair vocabulary, or
deriving it from the theorem catalog, adds reach the system cannot use.

A third repair shape was built and reverted on the same evidence: proposing a *source patch* (an
`assert <goal> by: <theorem>(...)` block) instead of a tactic step, validated by re-running the
whole checker on the patched source. That needs no kernel change and is sound by construction —
the checker is the checker. It was reverted because its positive path has no demonstrable case for
exactly the reason above, and an untestable capability is a stub.

That next piece is a `lemma` tactic, and building it far enough to find the blocker turned up a
constraint worth writing down rather than rediscovering.

`--suggest` already matches a verified theorem's conclusion against a goal and reports the
parameter bindings, but no tactic can consume one: `apply` works only over an existing `A => B`
fact, and `have` requires the proposed fact to already be entailed, so neither can introduce an
instantiated lemma conclusion. A tactic mirroring `proof_apply_lemma` — match a verified theorem's
postcondition against the current goal, discharge each instantiated precondition from the current
hypotheses, and close the goal — is the missing piece, and it is what would let the repair
vocabulary be *derived* from the source's own theorem catalog instead of enumerated.

Two prototypes were built and reverted. The first found a plumbing constraint; the second solved
it and found the real one, which is not plumbing at all.

The plumbing constraint is store locality. `Ast::Expr` values are opaque handles into the parser
store that produced them, and the tactic engine deliberately runs in a *fresh* store, so a tactic
cannot read the report's theorem expressions — the first prototype matched nothing for that reason.
The fix is the one the source-bound path already uses for the goal state: export the verified
theorems' parameter names, preconditions and postconditions to the JSON expression interchange and
reparse them in the tactic store. The second prototype did this, and with it the tactic worked: the
engine reported the script `valid`, the goal `solved`, the recorded trace independently
`trace_replayed`, and the propositional kernel `kernel_replayed`.

It was refused by the last gate, and the refusal is correct. `proof_kernel_replay.elisa` carries a
whitelist of tactic actions the source-neutral kernel knows how to check, and `lemma` is not among
them. Adding it there would mean the trusted kernel accepting a step whose justification — the
theorem's own verified proof — is not in the arena the kernel checks. That is exactly "claiming
proof without trusted-kernel justification", and it is not a gate to widen.

So the design is now specified rather than guessed. A lemma step must carry its justification the
way the *checker* already does: a lemma-derived fact carries a `lemma-summary` fact trace, and
`replay.elisa` validates it by re-checking the lemma's own certificate and its dependency chain
(`proof_replay_lemma_summary_is_valid`, `proof_replay_dependency_is_checked`). The tactic step's
kernel encoding has to reference the theorem's certificate root the same way, and the kernel rule
then has something to check: that the instantiated conclusion equals the goal, that each
instantiated premise is among the facts, and that the referenced certificate is itself replayed.
Until that chain exists, the whitelist stays as it is and the repair vocabulary stays enumerated.

Three sub-results are now settled. The matcher can be made store-independent by taking the
parameter-name list instead of `(report, theorem)`, which leaves `--suggest` working unchanged. The
catalog export must carry only *verified* theorems, so an unverified one is absent from the tactic's
world rather than merely rejected by it. And the trace replay needs the catalog too, because a
`lemma` step records which theorem it used and `proof_tactic_replay` must re-derive it or refuse.

Both prototypes were reverted rather than landed. The tactic still needs its own adversarial
fixtures before it is worth having: an unverified theorem must not be usable, a conclusion that
does not match must refuse, a precondition that does not discharge must refuse, and a trace naming
a theorem the source no longer verifies must fail replay rather than silently apply another.

`split` and `cases` still need nested branch scripts, which the text grammar has no syntax for, so
a branching proof must be written as JSON and the vocabulary is branch-free. And nothing yet
re-derives which goals a source *edit* invalidated: the batch repairs what is open now, but does
not diff two revisions.

## Added: the sign of a product

Every arithmetic tier in the checker was linear, so `x >= 0, y >= 0 |- x * y >= 0` had no rule at
all — not because it is hard, but because it is the one nonlinear fact that follows from the
operands' signs and needs no reasoning about multiplication beyond them. The previous entry
measured that this exact gap is what blocks automated repair: a lemma cannot supply it either,
because a recursive lemma proving `n * m >= 0` fails its own `ensure` for want of the distributivity
its inductive step would need. The same missing arithmetic blocked both halves, so closing it here
is the piece that actually moves.

`proof_product_sign_goal` and `proof_kernel_replay_product_sign` conclude a sign for `A * B`
against a literal zero, in either order, from the operands' signs: nonnegative from two
nonnegatives or two nonpositives, nonpositive from a mixed pair, and the strict conclusions from
strict premises. `0 <= x` is accepted as the same fact as `x >= 0`.

Two design choices are load-bearing. The rule is **syntactic**: the required sign facts must be
present as facts, matched structurally, never re-derived by a second search. A tier the producer
and the kernel could only approximate would surface as a replay gap rather than as a proof, and
keeping the rule small is what lets the two state it identically. And both operands must be
witnessed primitive scalars, because Elisa rewrites `*` on a struct operand to a user `__mul__`,
which is an ordinary method under no sign law whatsoever.

Nothing about signed overflow is newly assumed. The prover already models signed arithmetic as
unbounded integers — it is how `x >= 0, y >= 0 |- x + y >= 0` is proved today — and the unsigned
range guards that gate fixed-width reasoning are untouched.

Coverage. `examples/product_sign.elisa` proves all six accepted shapes and
`examples/rejected_product_sign.elisa` refuses five near misses: a strict conclusion from
non-strict premises, a mixed pair claimed nonnegative, one known sign standing in for two, a bound
other than zero, and sign facts about unrelated terms. Both suites require the accepted file to
replay with zero gaps and the rejected file to prove no non-resource goal.

The two mutation results are the point. Disabling the producer's rule drops the accepted fixture
from 12 proven to 6. Disabling the *kernel's* mirror leaves the producer proving all 12 and
produces **6 replay gaps** — the kernel independently re-derives every one of these signs, and a
rule the producer alone believed could not pass as a proof. On the kernel's own source the proven
count moved from 891 to 896 with replay gaps unchanged at zero.

## Added: a lifetime pinned to the caller's own frame

A region-polymorphic call was mapped only when some actual already carried the formal's lifetime as
an active region. A borrow of a caller *local* carries no region, so `visit(&local, 0)` against
`cell: mutable Cell& @s` had nothing to pin `@s` with and was `region-call-opaque` — even though a
caller local outlives any call that borrows it, which is the entire content of the claim.

`proof_resource_frame_lifetime_pinnable` and `proof_kernel_replay_frame_region_name` add that case.
The mapping records `@call-frame`, a name outside the identifier grammar so no source region can
collide with it, and it is deliberately *not* a region with an extent: there is nothing to open or
close, because the frame outlives the call by construction. What both sides check in its place is
that every actual receiving the lifetime is a place the caller holds outright — a live, unmoved
binding carrying no region of its own — and that some actual receives it at all.

The fallback runs only after the ordinary pinning has already failed, so no call that maps today
changes behavior; this widens the rule strictly.

Coverage. `examples/frame_lifetime.elisa` proves an exclusive and a shared borrow of a local into a
lifetime parameter and two lifetimes pinned by two distinct locals.
`examples/rejected_frame_lifetime.elisa` refuses a local moved away before the call and a lifetime
no formal carries, and records no frame mapping at all in either case. Disabling the producer's
pinning drops the accepted fixture from proving; disabling the *kernel's* rule leaves the producer
proving all eleven and yields three replay gaps, so the kernel re-derives the frame claim itself.

**On the corpus this moved almost nothing: proven 896 to 897, and `region-call-opaque` stayed at
252.** That corrects the diagnosis recorded in the confined-lend entry, which named this shape as
the dominant cause. It is not. The 252 are dominated by 79 calls inside
`proof_kernel_replay_resource_events` and 46 inside `proof_kernel_replay_tactic_step_impl` reported
as "no converged lifetime summary", meaning the callee has no summary *and* the confined-lend rule
refused them — and the lend rule refuses them for some reason other than lifetime pinning, since
their lifetimes are carried by ordinary reference parameters. Whatever that reason is has not been
measured yet, and the next attempt on this gap should start by measuring it rather than by
extending a rule.

## Added: lending a region the callee cannot name

The confined-lend rule refused a region-owned actual reaching a formal that declares no lifetime,
in two places at once — once while collecting the call's lifetimes and once in the lend rule
itself. That made a region-allocated value unusable at any summary-less callee without a lifetime
parameter, and it is what actually accounted for the region-opaque bulk. The previous entry said
the cause had not been measured; it has been now.

The measurement is the method worth keeping. Instrumenting each `return false` in the lend rule to
emit a distinctly named finding, then counting them over `examples/kernel_replay_standalone.elisa`,
gave a first-failing-gate histogram: the region collector accounted for 237 refusals and nothing
else came close. Relaxing that gate alone changed nothing, because the refusal simply moved to the
*same rule restated* inside the lend gate, 159 refusals — which the second peel found. Refusals
peel; one histogram is not a diagnosis.

The relaxation is narrow. A region-owned actual may reach a formal with no declared lifetime only
when the callee declares **no lifetime at all**: such a callee can name no region, so it can
neither allocate into that region nor return anything from it, and a lend already requires it to
return no reference and no region. The reference's own liveness is still checked on both sides as
an ordinary borrow. A callee that *does* have a lifetime parameter can name regions, so an
unannotated formal carrying a different one could be mixed with them —
`examples/rejected_region_lend_calls.elisa` pins that refusal, and the first version of this change
broke it, which is how the boundary was found. The summary path is untouched: there the callee's
own trace is what places such an actual, so the refusal stands.

On the kernel's own source `region-call-opaque` moved from 252 to 107 and `borrow-call-opaque` from
204 to 59, failing obligations from 1992 to 1706, proven 897 to 901, with replay gaps unchanged at
zero and `trusted_assumptions` still empty.

Coverage. `examples/unnamed_lifetime_lend.elisa` lends a region-allocated value both shared and
exclusively to callees that export no summary, and requires every resource goal proven with no
`region-call-opaque` or `borrow-call-opaque` finding; undoing the relaxation drops both callers.
`examples/rejected_unnamed_lifetime_lend.elisa` gives the same shape a callee that *does* export a
summary and requires it still refused. Not covered: the by-value half of the rule — a formal
receiving a copy whose nested region values the callee could keep — is retained by construction but
has no fixture, because a by-value actual carrying a region is rejected earlier by the argument-kind
gate before this rule sees it.

## Measured: what `expression-unsupported` actually is

An unsupported statement does not merely go unproven — it sets `flow.valid <- false` and
invalidates its enclosing path, so each one costs everything after it in that function. There are
192 of them on `examples/kernel_replay_standalone.elisa`, second only to the region and summary
diagnostics, and until now nothing recorded *which* shapes they were.

Peeling the gates with the instrumentation method (see the memory note on measuring refusals) gives
a complete split, and it redirected the obvious plan twice:

| count | gate | meaning |
| --- | --- | --- |
| 113 | `proof_expr_supported` → `Ast::Expr.Block` | a block-valued expression statement |
| 46 | `proof_runtime_expression_calls_allowed` | a call in a `return`/statement value |
| 32 | `proof_runtime_branch_calls_allowed` | a call in an `if` condition that may be skipped |
| 1 | `Ast::Expr.Invalid` | — |

The first redirection: **zero** refusals come from `while`, `for`, `match` or `assert` conditions.
The recorded next step after the branch-condition work was to extend that rule to those forms after
auditing their handlers. That would have gained nothing, and the `while` handler turns out to
already frame its calls, forget values and emit `loop-condition-opaque` — the gate there is not
what is costing anything.

The second: the 113 are not an exotic shape. Mapped back to source they are all ordinary
`for x in xs |captures|:` loops, and they arrive at the value gate as `Ast::Stmt.Expr` carrying a
block — `Ast::Stmt.For` accounts for *none* of the refusals. So the loop form that the kernel's own
source uses everywhere is the one the statement walker does not model, and each occurrence
invalidates its function's path. That is very likely where a large share of the 191
`function-summary-unverified` comes from as well, since a function whose path is invalid exports no
summary and every caller then reports one.

The shape gate refuses such a block *on purpose*, and the reason is recorded next to it: a captured
block writes back into its outer bindings, and accepting it as a pure expression would let an outer
fact survive a hidden mutation. So the fix was never to widen the gate — it was to model the
write-back where the block's result is discarded anyway.

`proof_captured_block_statement` recognizes the statement form and the walker gives it the
treatment `parallel for` already uses: check the body in a private state so no nested obligation is
skipped, record the loop itself as an unverified obligation, then havoc the outer symbolic values
and clear the outer facts, keeping type bounds. The body is checked against the same `ensures`, so
a `return` inside it still has to establish them, while `break` and `continue` are absorbed by the
loop and never reach the enclosing function. A trailing block value is appended to the body as an
ordinary expression statement rather than ignored, so its own obligations are checked too.

What this bought is mostly *visibility*, and that is the honest way to read the numbers. On the
kernel's own source proven went from 901 to 1135, but total obligations went from 1706 to 2412 —
because 270 index-bound obligations *inside* captured loop bodies had never been checked at all.
Refusing the statement set `flow.valid <- false` and moved on, so the body was never walked. Those
obligations were not being claimed, but they were not being examined either, which is the worse
half of a fail-closed answer. `expression-unsupported` drops from 192 to 115 and the loops now
account for 137 `captured-block-unsupported` findings of their own; replay gaps stay at zero and
`trusted_assumptions` stays empty.

Coverage. `examples/captured_block.elisa` requires an index obligation *after* the loop and one
*inside* it both to be proven, which is only possible because the path stays valid and the body is
walked. `examples/rejected_captured_block.elisa` requires a fact and a symbolic value established
before the loop not to survive it, and an unprovable obligation inside the body to stay visible
rather than vanish with the path.

Not covered. Clearing the outer facts is retained as defence in depth but no fixture isolates it:
every write-back case reachable through a postcondition is already caught by forgetting symbolic
values, and an `assert` in a normal body is a runtime assertion rather than an obligation, so it
cannot be used to observe a surviving fact.

### The write-back is scoped to the capture list

The first version of the write-back havocked the whole frame, which was far more than the block can
reach. A captured block cannot *name* a binding its capture list omits, so it can neither read nor
write one; havocking those bindings discarded facts and symbolic values no execution of the block
could have falsified. That is what cost `value_outside_the_capture_list_survives`-shaped code its
postcondition even though the loop never mentions the binding it returns.

`proof_forget_captured_values` now gives a fresh opaque symbol only to the captured names, and
`proof_restore_uncaptured_facts` re-establishes the facts over the rest. Neither is a new trust
rule: both run the captured names through `proof_expr_call_stable` alongside `report.aliased_names`,
the same predicate the opaque call boundary and the branch join already use. So a binding anything
references is still forgotten — the block may hold that reference through a captured name — and a
recorded value expressed in terms of a binding the block does rewrite is forgotten with it, rather
than silently following the new symbol. When the frame has no usable alias set the whole-state havoc
is what runs, unchanged.

On the kernel's own source this moves proven from 1135/2412 to 1160/2430; the refusal histogram is
identical, so the gain is entirely in goals that now discharge rather than in refusals that were
relaxed. Replay gaps stay at zero and `trusted_assumptions` stays empty.

Coverage. `examples/uncaptured_binding.elisa` requires a symbolic value and a `requires`-derived
fact, both over bindings outside the capture list, to survive the block and discharge a
postcondition. The capture-list argument quoted above is false as stated -- a block can assign an
outer binding its list omits -- and is corrected under "A captured block wrote a binding its
capture list did not name" below; the write-back set there is the capture list plus what the body
writes and references. `examples/rejected_uncaptured_binding.elisa` is the adversarial half and pins the two
ways this could go wrong: a binding the list *does* name whose value the loop overwrites must not
keep its old value, and a fact the loop body establishes must not escape a loop that may run zero
times.

Not covered. The block's own exit state is still discarded rather than merged, so a loop with an
invariant proves that invariant inside its private state and exports nothing from it. Importing that
state is a larger step than this one: it needs the loop's post-state to be sound for the
zero-iteration path, which the capture-list argument does not have to reason about at all.

## An invariant-less loop did not assume its own condition

Measured first. Of the 270 unproven index obligations, the shape that dominates is
`while index < collection.count |...|:` -- the codebase's own loop idiom. A probe pinned the cause
exactly: `for index in 0..<values.count` proves its indexing, the same loop written as a `while`
does not, and a plain assignment in the body changes nothing while a *call* in the body loses the
bound. Two independent gaps, one behind the other.

The first is that the invariant-less branch checked the body without recording the loop condition.
The invariant branch already records it as a `loop-condition` traced fact; the branch that runs when
there is no invariant simply did not. The body runs only when the condition holds, so this is the
same premise, and it is the premise the indexing has to discharge against. A condition containing a
call is excluded: it may mutate the state the body is then checked in, and its value is already
reported opaque.

Four adversarial probes fixed what this must *not* give. `while index < 100` over a collection
proves no bound on that collection. A binding the loop rewrites must not carry its entry value into
the body -- checked through an index, through a signed local, and through a callee precondition,
because the body is checked from the loop-entry state and would otherwise reason about the first
iteration only. All four still refuse.

## A shared borrow's element count is stable across a call

The second gap: `index < values.count` is dropped at every call in the body, because
`proof_expr_call_stable` admits only scalars of the frame that nothing references, and a `.count` is
a field of a referenced binding. `proof_expr_call_stable` now also admits `p.count` for a parameter
`p` bound by a shared borrow, recorded per function in `report.shared_extent_names`. Nothing may
write through a shared borrow for its lifetime, and the borrow rule the compiler enforces means no
mutable path to the same object coexists with it, so no callee can resize it. The scalar-term
witness is still required, so an unwitnessed count is refused exactly as an unwitnessed name is.

That argument has one hole, and the compiler does not close it. A mutable global is reachable
without being borrowed: a caller may lend `ambient_values` into a frame as `darray[i64]&` while a
callee empties it directly, and `elisac` accepts that program. It is written out as
`examples/rejected_shared_extent_global.elisa`. Rather than deciding per call which globals a callee
can reach, the rule is withdrawn from the whole program as soon as one mutable global is declared.
`examples/rejected_loop_condition_facts.elisa` additionally pins that a *mutable* borrow earns
nothing here: a callee may resize it, so its count is not stable.

`examples/rejected_while_body_visibility.elisa` changed with this. It asserted that an index inside
an invariant-less loop body stays unproven, which was a statement about the old conservatism rather
than about soundness -- its access is exactly what the loop condition gives. Its access is now one
past the bound, so it still tests that the body is traversed and the obligation stays visible.

What this bought, honestly: on the kernel's own source, nothing. Proven stays at 1160/2430 with an
identical refusal histogram. Both gaps are real and both fixtures prove what they should, but the
kernel's own bounds do not come from a loop condition -- they come from guard helpers such as
`proof_kernel_replay_child_range_valid(node.children_start, node.children_count, children.count)`,
whose postcondition the caller cannot use because the callee exports no verified summary. The 270
index obligations sit behind the 348 `function-summary-unverified`, which is the next thing to
attack, and neither of these two changes could have moved them.

## The difference engine can only chain what it can name

Measured, again with probes rather than by reading. `a < b`, `b <= c` over three names proves.
Change `c` to `items.count` and it does not. Neither does `a < b`, `b <= items.count` written as an
index guard, which is the single most common bounds shape in this codebase. The cause is one line
of representation: `ProofAffine.base` is an `sview` naming one bare identifier, so a field place is
not an atom, and the whole difference-bound engine is blind to `items.count`. Its kernel counterpart
names atoms the same way, so the blindness is symmetric.

Widening the atom to a field place is the principled fix and it is a large one: `ProofBound`,
`ProofDifference`, `ProofAffine`, the difference matrix and every one of their kernel mirrors are
keyed by a single name. Structural transitivity gets the same goals with none of that. Two recorded
comparisons are chained through a middle term matched by the structural equality the kernel already
replays, so the rule needs no atom at all: `proof_comparison_chain_goal` in the producer and
`proof_kernel_replay_comparison_chain` in the kernel, added at the matching position in the two
goal dispatchers.

The rule is not "transitivity". `<` and `<=` are the primitive integer order only for witnessed
scalars; on a struct they dispatch to a user comparison that is under no transitivity law, exactly
as reflexivity and symmetry are. All three terms therefore carry the same scalar-witness guard the
neighbouring comparison rules use, and the composition is explicit: strict if either step is strict,
and a non-strict chain never discharges a strict goal.

Cost, which was a genuine mistake first time round. The first version scanned the facts once per
candidate and put the witness check in the outer loop; on this corpus, where a frame carries
hundreds of facts and most comparison goals have a side the engine cannot name, that made
`kernel_replay_standalone` unrunnable -- twelve consecutive attempts against four for the build
without it. Two changes fixed it: the goal is skipped outright when both sides *are* nameable atoms
(the difference engine already had its chance), and each endpoint's candidate facts are collected in
one pass and then paired, rather than rescanning every fact per candidate. Both candidate sets are
capped, and a spent cap refuses, which can only lose a proof. After that, `linear.elisa` runs in
750ms against a 692ms baseline and `resources.elisa` in 17s against 17s.

Coverage. `examples/comparison_chain.elisa` proves four goals the difference engine cannot reach,
including the index-guard shape, and requires zero replay gaps and no trusted assumptions -- the
kernel rule is what makes those certificates replay.
`examples/rejected_comparison_chain.elisa` pins the four ways this could be wrong: a strict and a
non-strict chain over a struct, a non-strict chain offered against a strict goal, and two facts
pointing the same way through the middle term rather than through the chain.

What it bought on the kernel's own source: 1168/2458 against 1160/2430. The 28 extra obligations are
this change's own code being checked; the pre-existing corpus barely moves. The shape that dominates
there is `left.children_start + index < children.count`, and a sum of two non-constant atoms is not
affine in this representation at all -- a second, separate gap that structural transitivity does not
touch.

## A summary withheld for a construct that was only over-approximated

An earlier entry named the target: `function-summary-unverified`, the largest finding class on the
kernel's own source -- 348 when it was named, 356 at this change's parent -- with the unproven index
obligations sitting behind it. That count is an amplifier rather than a population: a function that
exports no summary costs every caller its own summary in turn, so the question was only what puts
the first function into the set.

`proof_report_function_is_clean` answers it. *Any* finding against a function withheld its summary.
That is right for an unproven obligation, and right for `expression-unsupported`, which marks the
path itself unusable rather than merely widened. It is wrong for the two findings that record a
construct whose effect was *over-approximated*: `captured-block-unsupported` and
`loop-invariant-missing`. In both the checker forgets the symbolic values the construct can reach
and clears the facts over them, and only then goes on -- reasoning from a state weaker than any real
execution. A contract derived that way is exactly as sound as one derived by a function with no
findings at all.

Both are unconditional, which is what makes the rule safe to state at the level of a finding kind.
The captured-block branch emits the finding and calls `proof_forget_captured_values` /
`proof_clear_facts_keep_type_bounds` in the same straight line. An invariant-less loop initialises
`loop_exit_valid` to `invariants.count > 0 and ...` and nothing later sets it true, so the
`proof_forget_values` arm at the loop's exit is the only one it can take.

The summary becomes usable, and the declaration's `verified` flag is exactly what gates that, so the
flag stays true -- that is the change. What separates a fully checked contract from one derived
through an over-approximated construct is the `verification_reason`: `contract-verified-widened-state`
rather than `verified`. A reader who needs that distinction has to read the reason, not the flag --
and since a caller proving from such a summary is in the same position, the marking travels the call
graph. Components are scheduled in dependency order,
so every callee outside the current component already carries its final reason when it is read. The
file's `verification_state` is unaffected: `proof_finding_status` already ranks both kinds
`unknown`, which is a floor no amount of summary reuse can lift.

`proof_replay_dependency_is_checked` applies the same filter, so the kernel and the scheduler agree
about which dependencies are usable. It is restated there rather than shared:
`proof_replay_finding_only_widens_state` is the only reason `replay.elisa` would have called into
`check.elisa` at all, and replay's value is that it is a second opinion on the report rather than
the same code run twice. The two conditions that carry the weight in that function are untouched --
every goal the dependency recorded must be proven and every certificate it owns must replay.

Lemmas keep the strict rule, under `proof_report_lemma_is_clean`. A lemma body admits only
contracts, proof calls and assert-by blocks, so `proof_check_lemma_purity` already emits
`lemma-impure` beside any loop or captured block; the point is that the lemma scheduler should not
rest on that coincidence, because the relaxation is justified by a havocked execution state and a
lemma has none.

Coverage. `examples/widened_state_summary.elisa` requires a `for` and a `while` loop's callers to
import a summary they previously lost, requires the reason to be `contract-verified-widened-state`
three levels up the call graph, requires a sibling that reaches only checked code to keep `verified`
so the two reasons stay distinguishable, and requires the file to stay `unknown` with no open goal.

`examples/rejected_widened_state_summary.elisa` pins the boundary from five directions. An unproven
`ensure` beside a loop keeps its summary withheld -- that `ensure` *is* the summary. An unproven
index does the same, since the body may not reach its return. A summary also carries a frame, and
the frame is what lets a caller's disjoint facts survive the call, so a `changes` frame the captured
block writes outside of, and a `preserves` the captured block writes over, are both still refused --
`frame-write-outside` and `frame-preserve-write` are raised from inside the very construct the rule
forgives. The last is the pair the whole change rests on: an unframed widened callee is now
accepted, and the call boundary alone has to take its caller's stale fact away. It does.

What it bought on the kernel's own source: 1167/2456 against 1168/2458. Eleven functions move from
unverified to `contract-verified-widened-state`, and `function-summary-unverified` falls from 356 to
345. Ten of the freed call sites do not turn into proofs -- they reach the next real obstacle
instead, which is the point. `borrow-call-summary-unsupported` rises 80 to 85, `region-call-opaque`
107 to 111, and `call-requires-unproven` 15 to 16, the last because a caller that can finally see a
callee's `requires` now has to discharge it: a summary is imported with its obligations, not instead
of them. The one obligation lost is `proof_kernel_replay_effect_report`'s single `resource-safety`
goal. With its callee's summary available the call is modelled as a real borrowing call whose
summary this checker cannot express, so it refuses rather than emitting the goal. That function was
unverified before and after, so nothing that was claimed has become unclaimed -- the checker stopped
proving a goal it now declines to reach.

Both suites pass. `scripts/dogfood.sh`'s `replay_standalone` probe was run separately from the rest
of that suite, and did execute twice: both runs exit 1, the two reports are byte-identical, and the
report carries 1167 certificates all replayed with no gaps under independent kernel replay.

## A call boundary and a branch join forgot what they could not reach

### What was wrong

Two havoc points in `check.elisa` forgot every recorded binding value in the frame, not only the
ones the construct could rewrite.

At a call boundary -- a declaration or assignment whose initializer contains a call, a statement
call, a call in an `assert`, an `if` or `match` head, a `for` iterable or an `assert ... by:` guard
-- the checker gave every pre-existing binding a fresh opaque symbol (`proof_forget_values`,
`proof_forget_values_before`, `proof_forget_values_except`). The facts at the same boundary were
already treated more carefully: `proof_clear_facts_after_call` keeps a fact that is call-stable for
the frame, because a callee reaches the caller's state only through references and globals, so a
by-value scalar nothing in the body references cannot change across the call. The values were not
given the same treatment, and the asymmetry was visible: on the kernel's own source a loop binder's
range was proven on the first line of a loop body and unprovable on the next, because the call
between them had renamed the binder to a plain symbol the range facts no longer described. Even
`0 <= index` failed.

At a branch join whose arm may modify state, the checker forgot every value as well, then imported
the call-stable facts from the arms that reach the join. The arms had been executed symbolically,
so each arm's end state was available, and a value both reaching arms still agree on is the
binding's value at the join. This is the shape of every guarded statement call in the kernel
(`add_lower(...) if left_bound.has_lower`): the arm makes a call, the join forgot the binder.

Neither was unsound. Both were a loss of precision that took the dominant loop-with-calls shape out
of reach of the index rules, and the `index-lower-unproven` refusals it produced were pure noise:
nothing in a loop body can make a `for` binder negative.

### What changed

`proof_forget_values_after_call` replaces the three whole-frame forgets at the call boundaries. A
binding keeps its recorded value when the frame's alias set is usable, the binding's own name is
not in it, and the value is call-stable under `proof_expr_call_stable` against the aliased names --
the predicate the fact side of the same boundary already applies, so a value survives exactly where
a fact over it would. A declaration's own new binding and the slot that receives an assignment's
call result are handled as before. Without a usable alias set nothing is kept, which is the
whole-frame forget this replaces.

`proof_restore_branch_values` runs at the branch join after the existing forget. For each binding
in the pre-branch frame it imports the value from the arms that reach the join when every reaching
arm carries the same value (`proof_expr_equal`) and that value is call-stable. An arm that
introduced a binding of its own is not imported from at all, matching the rule the fact import
already uses, so an arm-local name cannot escape through a value. When only one arm reaches the
join its value is the whole state and is imported alone.

Neither helper adds a trust rule and neither touches the kernel or the replay: the certificates a
goal produces are the same shape, replayed by the same rules, with more of the goals now
certifiable.

### Fixtures

`examples/call_boundary_binding.elisa` requires a loop binder and a recorded literal to survive a
declaration call, an assignment call, a statement call, a guarded call and a returning branch, each
discharging a postcondition that the previous build refused in all six functions. The callee writes
through a reference, so it is not pure and the boundary is a real havoc.

`examples/rejected_call_boundary_binding.elisa` pins the ways this could go wrong. A binding passed
by reference to the callee must not keep its value; a value recorded as the symbol of a referenced
binding must not follow that binding's rewrite -- the false postcondition `result == 0` would
otherwise be derived from the callee's own summary; the same across a statement call; and at a join,
a value one arm overwrote must not be taken from the arm that left it alone, nor from the pre-branch
state when the other arm returns. All five fail with `ensure-unproven` and nothing else.

`scripts/test.sh` asserts every goal of the positive fixture proves and exactly those five owners
fail in the adversarial one; `scripts/dogfood.sh` repeats both against its own reports.

### What it bought

On `examples/kernel_replay_standalone.elisa`, measured against a binary built from the previous
commit, proven moves from 1167/2456 to 1177/2456. The ten goals are all `index-lower`, in
`close_equalities`, `names_equal`, `goal_depth` and `resource_lend`, and every one is a loop binder
that had lost its range at a call. `index-lower-unproven` falls from 69 to 59; no other refusal
count moves, no function changes its verification reason, and the certificate count rises with the
proven count with replay gaps still 0 and `trusted_assumptions` still empty.

The matching `index-upper` goals in those loops do not move, and the reason is now visible rather
than hidden behind a forgotten binder: `for index in 0..<left_names.count` bounds the binder by one
array and the body indexes a second one, `right_names[index]`, whose count the checker has no
relation for. That is a relational invariant the kernel source does not state, not a forgetting
problem. The remaining `index-upper-unproven` are almost all of this shape or the
`children_start + index < children.count` sums an earlier entry already describes.

Not covered: `match` arms are joined without per-arm values, so a guarded call written as a `match`
still forgets the frame; and the alias set is flow-insensitive, so a local whose reference was
taken anywhere in the body is forgotten at every call in that body, including calls that cannot see
it.

## A call on the right of a short-circuit refused the whole statement

### What was wrong

`proof_runtime_calls_evaluate_unconditionally` admitted an impure call in a branch condition only
where its evaluation was unconditional, and on the right of `and` / `or` only a pure call. The
return, statement, declaration and assignment value gate (`proof_runtime_expression_calls_allowed`)
was narrower still: the value had to *be* the call, or be pure. Anything else was
`expression-unsupported`, which does not merely go unproven -- it sets `flow.valid <- false` and
invalidates the enclosing path, so every obligation after it in that function is lost and the
function exports no summary.

The shape this refused is the kernel's dominant guard: `return false if not a(...) or not b(...)`
and `if a(...) and b(...):` with `b` taking a reference. 115 of the corpus's `expression-unsupported`
findings were this, and the earlier measurement of that finding kind had already identified them
as the largest remaining source.

### What changed

A call on the right of a short-circuit may or may not have run. The sound model is: check its
frames and preconditions as if it ran, apply its havoc as if it ran, and keep nothing that only
the run could establish. `proof_check_frame_calls_in_expression`'s `Binary` arm now does exactly
that for an impure right operand: it walks the operand against the current facts, then keeps of
the result only the facts that were already standing before the walk -- the ones the havoc could
not remove, which are true whether or not the call happened. A callee's `ensure` is dropped, since
it holds only on the path where the callee executed and this is not a branch that records one.
The precondition is checked against the facts without the left operand, which is stricter than
the run needs and therefore sound.

`proof_runtime_calls_evaluate_unconditionally` admits such an operand when it would be admitted
unconditionally, and a new `proof_runtime_value_calls_allowed` applies that rule to the value
forms whose handlers already walk every call in evaluation order and substitute the value only
afterwards. The `while`, `for`, `match`, `assert` and `assert ... by:` forms keep the root-only
rule: `rejected_assert_nested_call` records why an assertion cannot be widened this way, and the
others have not been audited for a nested call.

Is the dropped `ensure` ever needed for soundness rather than precision? No -- a callee's result
ensure is a statement about the call term, which the enclosing `and` / `or` only consults on the
path where the call ran, and its frame's state facts are already removed by the havoc. Keeping
the ensure would be sound too; dropping it is simply the conservative side, and the adversarial
fixture below shows that nothing is lost that a false claim could exploit either way.

### A gap this exposed, and its fix

With the guard shape admitted, the corpus produced its first replay gap: one certificate the
kernel refused. The goal was a trivial `0 <= 127` precondition inside `if a(nodes, p.root, 0) and
a(nodes, t.root, 0):`. The binding `t` came from an unverified callee, so its value was the opaque
placeholder the body checker keeps after a failed substitution. The whole condition therefore
mentioned the placeholder, `proof_kernel_expression_supported` rejected it, and it was omitted
from the certificate as designed -- but `proof_add_branch_condition_facts` had also derived the
admissible conjunct `a(nodes, p.root, 0)` *from that condition as its premise*. The conjunct
entered the certificate, its trace named a premise replay could never validate, and the kernel
gapped. `examples/rejected_branch_conjunct_placeholder.elisa`'s shape gaps on the previous
binary with no call in the condition at all: the defect was latent, the new admission merely
reached it.

Two changes close it. `proof_add_branch_condition_facts` records each admissible conjunct of an
inadmissible condition as a `branch-condition` fact in its own right: control reached this point
through the condition, so each conjunct holds for exactly the reason the condition does, and the
kernel validates a primitive branch fact by its arena alone. `proof_add_derived_fact_from` refuses
any derivation whose premise the kernel cannot represent, so no other derived kind can repeat the
mistake; the fact is simply unavailable, which is the conservative direction.

### Fixtures

`examples/short_circuit_call.elisa` proves the guard, declaration and return shapes with an impure
callee on the right, and a caller that uses the returning shape's summary; the previous build
refused all four functions. `examples/rejected_short_circuit_call.elisa` pins that a skipped call
establishes nothing (`counter == 5` before, `result == 0` claimed: unproven through `and`, `or` and
a guard), that its havoc is applied (`result == 5` claimed after a call that zeroes it: unproven),
and that its precondition is still an obligation (`call-requires-unproven` on a call that may be
skipped) -- five findings and nothing else.

`examples/branch_conjunct_placeholder.elisa` needs the admissible conjunct to bound a depth and
requires the goal to prove *and replay*; the previous build certifies it with a gap.
`examples/rejected_branch_conjunct_placeholder.elisa` pins that the conjunct carrying the
placeholder is recorded in no form and nothing is derived from the condition.

All four are asserted in `scripts/test.sh` and repeated against `scripts/dogfood.sh`'s reports.

### What it bought

On `examples/kernel_replay_standalone.elisa`, measured on a build carrying only this change,
against the previous commit's binary: proven moves from 1177/2456 to 1228/2395. The next entry
takes those 1228/2395 as its own baseline; the combined figure for this commit is at its end. `expression-unsupported` falls from 115 to 11. Three functions
change reason to `verified` (`collect_differences`, `proposition_shape`,
`proposition_state_valid`); `function-summary-unverified` falls 345 to 332; the index rules gain
28 lower and 22 upper bounds in bodies that were previously invalid paths. As before, ten of the
freed call sites reach the next real obstacle instead of a proof: `borrow-call-summary-unsupported`
85 to 96 and `region-call-opaque` 111 to 121, which is also where the three `resource-safety`
goals went -- `difference_comparison`, `goal_report` and `quantifier_report` now see a real
borrowing summary at a call the resource pass refuses, where before they saw an unverified callee;
all three were unverified before and after. Replay gaps are 0 and `trusted_assumptions` is empty.

Not covered: the same conditional treatment for the arms of a ternary and for a call under a
`match` guard, both still refused; and the loop, match and assertion forms named above.

## A loop body began every iteration with the values from before the loop

### What was wrong

A loop's body was checked against the state that reached the loop header, and that state was
never invalidated for the assignments the body itself performs. The symbolic values of bindings
the body writes, and every fact recorded about them, were live at the top of the body -- so the
checker reasoned about the *first* iteration and reported the result as if it held for all of
them.

Three false proofs followed from that, all of them reproduced on the previous commit's binary and
pinned in `examples/rejected_loop_entry_state.elisa`:

* An entry value reached the body. `total = 0` before `while ...:` let the body prove `total < 10`,
  which is the precondition of a call the body makes on every iteration. The obligation is
  `call-requires-unproven` from the second iteration onwards; the checker discharged it from
  `0 < 10`.
* The same held for a loop with no capture list. That case matters because a capture list is not
  what makes a loop able to write an outer binding: `elisac-stage1` compiles an uncaptured loop
  whose body assigns an outer mutable binding, and compiles an assignment to a `for` binder.
  Neither form may keep its entry value.
* A false `invariant` was reported preserved. With `step = 0` live, `step + 1 <= 5` proves from
  the entry value rather than from the invariant, so an invariant that no iteration preserves was
  accepted, and everything downstream of it inherited the lie.

The loop *binder* was already resymbolized. The bug was in everything else the body touches.

### What changed

`proof_forget_loop_entry` computes the set of names an iteration can write -- the names aliased
anywhere in the body (`proof_collect_aliased_names`), the roots of every assignment in the body
including those nested in inner blocks, branches, loops and match arms
(`proof_collect_assignment_roots`), and the function's existing `report.aliased_names`. If any of
those is the unbounded marker `*`, the whole frame is forgotten and only type bounds are kept.
Otherwise each written name that is still in scope is passed to `proof_resymbolize_binding`, which
gives it a fresh symbol and purges every value and fact that mentions it, and the type bounds are
restored afterwards. A body that writes and aliases nothing keeps its entry state unchanged.

It runs on every path that checks a loop body: the invariant-less `while`, the `while` with
invariants, the termination pass, and both `for` paths. It runs *before* the loop's own entry
facts are added, so the loop condition, the established invariants and the binder range are
asserted over the forgotten state and survive -- an invariant is now proved by induction rather
than from the values that happened to reach the header.

Getting it in the right place needed one structural correction. The source forms
`for x in xs |caps|:` and `while c |caps|:` do not parse as a loop with a capture list; they parse
as a *block* that carries the captures and wraps the loop, so the block is the statement and the
loop is inside it. Forgetting at block entry would therefore have run before the loop's facts were
established, and the establishment obligation would have become unprovable. `proof_check_captured_block`
now carries a `loop_entry` flag: the loop paths recognise the wrapper with
`proof_single_captured_block` and ask it to forget, substitute the entry conditions and invariants
over the fresh state, and propagate the body's breaks and continues back to the enclosing flow;
a captured block in statement position asks it not to, and keeps the write-back over the capture
list it had before.

### Fixtures

`examples/loop_entry_state.elisa` pins what still proves: a fact about a binding the body never
writes survives the loop, the loop condition bounds the body, a sound bounded invariant is proved
preserved, and the binder's range survives. `examples/rejected_loop_entry_state.elisa` pins the
four refusals -- the entry value in a captured body, the entry value in an uncaptured body, the
false invariant, and a `break` that must not make the exit condition available. The previous
commit's binary proves the first three of those goals; this one refuses all four.

### What it bought

Correctness, at a measured cost. On `examples/kernel_replay_standalone.elisa`, against the
build carrying only the previous entry's change: proven moves from 1228/2395 to 1210/2392.
Sixteen goal sites are lost and twelve gained; the losses are index bounds in bodies that were
being discharged from a length equality recorded before the loop, and the gains come from
invariants that now hold over a fresh state instead of a stale one. Replay gaps are 0 and
`trusted_assumptions` is empty.

For the commit as a whole, against the previous commit's binary: proven moves from 1177/2456 to
1210/2392, `expression-unsupported` 115 to 11, `function-summary-unverified` 345 to 333,
`index-lower-unproven` 59 to 48, `index-upper-unproven` 209 to 222,
`borrow-call-summary-unsupported` 85 to 95, `region-call-opaque` 111 to 120,
`index-bounds-opaque` 2 to 0, and `captured-block-unsupported` unchanged at 141.

Not covered: the lost index bounds are recoverable, but only by *proving* that an entry fact is
loop-invariant rather than assuming it, which is a separate inference this checker does not yet
perform -- the written set is a syntactic over-approximation and forgets facts about a name the
body writes even when the fact is untouched by the write. A captured loop's post-loop state is
still havocked over the whole capture list by the block write-back, so nothing the loop
established survives it. An unsigned increment still cannot be proved bounded without a constant
upper bound, so invariants over `usize` counters must state one.

## A captured block wrote a binding its capture list did not name

### What was wrong

The write-back at a captured block was scoped to the capture list. The reasoning recorded for it
was that a captured block cannot *name* a binding its list omits, so it can neither read nor write
one, and a fact over such a binding survives the block untouched. That premise is false for the
compiler this checker is written against.

`elisac-stage1` compiles

```
def main() -> i32:
    outside: mutable i32 = 0
    for j in 0..<4 |j|:
        outside <- outside + 1
    return outside
```

and the linked program exits 4. The capture list names only the binder, and the body assigns an
outer binding all the same.

So a fact over such a binding was restored after the block had falsified it, and the checker
proved things that are not true. The smallest case: a `usize` counter set to zero, incremented in
a loop whose capture list omits it, and then passed to a callee that `requires x < 10`. The
obligation was discharged from `0 < 10` and no finding was raised. Writing the identical function
with the counter *in* the capture list refused it, which is how narrow the hole was.

### What changed

The write-back set is no longer the capture list. It is the capture list together with every root
the body assigns and every place the body references, collected by the same two walks the loop
entry uses -- `proof_collect_assignment_roots`, which recurses into nested blocks, branches, loops
and match arms, and `proof_collect_aliased_names`, which covers `&`, `mutable`, `move`, method
receivers and arguments to reference or unknown callees. A lambda anywhere in the body still
yields the `*` sentinel, and that now forgets the frame and keeps only type bounds rather than
falling through a membership test no name matches. `proof_forget_captured_values` and
`proof_restore_uncaptured_facts` are unchanged; they are handed the wider set.

What the block still keeps is what it neither names nor writes, which is what the precision this
replaces was actually for.

### Fixtures

`examples/rejected_uncaptured_block_write.elisa` pins five shapes, each a binding written by a
block that does not capture it and then passed to a callee with a precondition: a plain
assignment, an assignment under a branch inside the block, a write through a reference handed to
a callee, an assignment in a block nested inside the block, and a `requires`-derived fact rather
than a recorded value. All five must produce `call-requires-unproven` and an unproven goal, and
the fixture admits no other finding kind. The previous binary proves all five.
`examples/uncaptured_binding.elisa` is unchanged and still requires both of its postconditions,
which is the evidence that the wider set did not swallow the precision it was introduced for; its
header claimed the false premise and now states the real rule.

### What it bought

Soundness, at no measured cost. On `examples/kernel_replay_standalone.elisa` the summary,
the finding histogram and the set of proven goal sites are identical before and after:
1210/2392 with 0 replay gaps either way. Every captured block in that corpus already names what
it writes, so the corpus never exercised the hole -- which is exactly why a fixture, not a
measurement, is what pins this.

Not covered: the block's own exit state is still discarded rather than merged, so a loop with an
invariant proves it inside the block's private state and exports nothing. The 141
`captured-block-unsupported` findings this produced on the kernel corpus were a separate defect,
resolved in the next entry.

## A capture list made the same loop unverifiable

### What was wrong

`for index in 0..<count: total <- total + 1` verified. The same loop written
`for index in 0..<count |index, total|:` did not: it recorded a failing obligation and a
`captured-block-unsupported` finding, and its function came back
`contract-verified-widened-state` instead of `verified`.

The two spellings are the same program. A capture list is how the source names what the loop's
body closes over; it does not change what the loop does, and it is not even a bound on what the
body writes -- the entry above this one shows a body assigning an outer binding its list omits and
the compiled program observing it. But the two spellings take different paths through the checker.
Without a list the statement is `Stmt.For` and the loop handler runs. With one it is a block that
wraps the loop, so the captured-block handler ran, walked the body -- which reaches the same loop
handler, which models the loop identically -- and then recorded its own failure on top.

That failure was not an unverified obligation. Every obligation inside the body is checked on both
paths. The loop's own approximation is reported on both paths where there is one to report: a
`while` with no invariant records `loop-invariant-missing` from the loop handler itself. What the
block adds is a write-back, and a write-back that havocs is a loss of information, not a step left
unproven. On the kernel's own source this was 141 failing obligations, which is every loop in it.

### What changed

`proof_body_is_one_loop` recognises a block body that is exactly one `While` or `For` statement --
the wrapper form -- and the captured-block handler skips its obligation and its finding for that
shape. The write-back itself is unchanged and still runs: the capture list together with what the
body assigns and references, havocked, with the facts over everything else restored. Every other
captured block keeps the finding, because for those the exit state really is discarded rather than
merged.

### Fixtures

`examples/captured_block.elisa`, `examples/captured_structural_accumulator.elisa`,
`examples/uncaptured_binding.elisa` and `examples/call_boundary_binding.elisa` now prove with no
findings at all, and their suite assertions say so rather than naming the finding.
`examples/loop_condition_facts.elisa` and `examples/widened_state_summary.elisa` keep exactly
`loop-invariant-missing`, which is the loop handler's own report and the thing this must not
silence. Every adversarial fixture over captured blocks is unchanged and still refuses:
`rejected_uncaptured_block_write`, `rejected_uncaptured_binding`, `rejected_captured_block`,
`rejected_loop_entry_state` and `rejected_loop_condition_facts`.

### What it bought

On `examples/kernel_replay_standalone.elisa`: obligations fall from 2392 to 2251 and failures from
1195 to 1054, with proven unchanged at 1210 -- 141 obligations that were never anything but this
finding. `captured-block-unsupported` goes 141 to 0. Not one goal site is lost or gained, and nine
functions move from `contract-verified-widened-state` to `verified`. Replay gaps stay at 0.

Not covered: a captured block that is not a loop still discards its exit state, and no fixture in
the tree produces the finding any more, so the remaining path is exercised only by the shape's
absence. The loop handler's own imprecision is untouched -- a `for` without an invariant still
forgets its whole frame afterwards.

## The checker died of a stack overflow on half a megabyte of source

### What was wrong

`elisa-proof` segfaulted on any source file past roughly half a megabyte. Bisected on generated
files of comment lines: 400 KB produced a verdict, 600 KB produced `SIGSEGV`. That threshold is
below `src/proof/check.elisa`, which is 605 KB, and only just above
`examples/kernel_replay_standalone.elisa`, which expands to about 430 KB. Two files in the tree
crashed it outright: `examples/tactic_runtime.elisa` and
`examples/lemma_summary_replay_runtime.elisa`, each of which pulls in the compiler as well as the
proof modules and expands to roughly nine megabytes across 480 files. Nothing in either suite ran
the checker on those two, so nothing caught it.

A crash is worse than a refusal. The tool produced no report, no finding and no exit status a
caller could act on, and a checker that dies on large input cannot be trusted to have checked the
large input it did survive.

The fault address sat on the stack guard page and the faulting instruction was the prologue of a
leaf function, with only seven frames below it. So this was not deep recursion: a single frame had
walked the stack pointer down eight megabytes. Reduced against `elisac-stage1`, the cause is one
construct:

```
def main() -> i32:
    index: mutable usize = 0
    total: mutable usize = 0
    while index < 700000 |index, total|:
        byte: usize = 10 if index == 0 else 20
        total <- total + byte
        index <- index + 1
    return 0
```

This compiles and dies with `SIGSEGV`. A declaration whose initializer is a *conditional
expression*, inside a *captured* loop body, leaks stack on every iteration. Each of these
variations runs to completion: the same declaration with a non-conditional initializer; the same
conditional as an assignment to a binding hoisted out of the loop; the same loop without a capture
list around the conditional declaration; and an indexed read, an `if`/`else`, a growing captured
`darray` or two million plain iterations in any combination. It is the pair -- conditional
initializer, captured loop -- that leaks. That is a code generation defect in the compiler, not in
this checker.

### What changed

`proof_expand_file` reads the file it is expanding one byte per iteration through exactly that
shape:

```
byte: u8 = 10 if at_end else contents[index]
```

so a source file of *n* bytes leaked *n* times. The binding is now hoisted out of the loop as
`mutable` and assigned with two guarded assignments, which the reduction above shows does not
leak. The comment there names the defect so the line is not "simplified" back.

### Coverage

`scripts/test.sh` now generates a megabyte of source into a temporary directory and requires a
`proved` verdict with a real goal discharged, zero semantic errors and zero replay gaps. It
generates rather than commits the file, because what is under test is the size, not the content.

### What it bought

Generated inputs at 600 KB, 800 KB, 1 MB and 4 MB all produce a verdict where 600 KB and up used
to crash. On `examples/kernel_replay_standalone.elisa` nothing moves: 1210/2251, replay gaps 0 --
this changes no reasoning, only whether the tool survives its input.

Not covered: the two nine-megabyte examples now run instead of crashing, but neither was run to a
verdict, so the ceiling above four megabytes is untested. The defect is worked around at one call
site, not fixed: the same shape appears elsewhere in this codebase, and every one of those loops
still leaks on every iteration -- they are simply bounded by proof state rather than by input
size. The compiler defect itself is not fixed here and belongs in the compiler.

## Writing an element does not change how long a collection is

### What was wrong

Forgetting the loop entry gives every binding an iteration may rewrite a fresh symbol. That is
what stops a value from before the loop standing in for an arbitrary iteration, and it is what an
earlier entry here fixed. It also threw away more than it had to. `xs[index] <- 0` puts the root
`xs` in the written set, so every fact mentioning `xs` was purged -- including the binder's own
range, `index < xs.count`, which the loop had just established.

The result was that the most ordinary loop there is stopped verifying:

```
def fill_in_place(xs: mutable darray[i64]&) -> void:
    changes xs
    for index in 0..<xs.count |index, xs|:
        xs[index] <- 0
```

`index-upper-unproven`, on the write whose bound the loop header states outright. This is a
regression that entry introduced and this one repairs.

### What changed

An assignment whose target is an index -- `xs[i] <- v`, `h.items[i] <- v` -- replaces an element
that was already there, so the collection's extent is what it was at entry.
`proof_collect_extent_written_roots` separates roots written that way from roots written any other
way: a whole assignment rebinds the collection, and a *field* assignment can replace a nested one,
so `h.items <- other` is a whole write of `h`. A root is extent-preserved only if it is written
solely through an index, is not aliased anywhere in the body, and is not in the frame's aliased
set -- a method call like `push`, a reference taken, or an argument passed by reference all
disqualify it, because any of those can resize.

For those roots, `proof_restore_extent_facts` re-establishes, after the resymbolization, each
entry fact that `proof_expr_extent_stable` accepts: every name it mentions is either untouched by
the body or an extent-preserved root read exactly as `name.count`. `xs` on its own and `xs[i]` are
not stable under an element write and are refused; only the bare identifier's count is, so
`h.items.count` is not claimed either. Facts are restored by expression, so their existing traces
stand and certificates still replay.

### Fixtures

`examples/loop_element_extent.elisa` requires the bound to prove for a `for` loop filling in
place, for one whose writes sit under a branch, for a `while` whose index comes from the loop
condition -- itself a fact over `xs.count` -- and for a recorded `xs.count == limit` rather than
just the binder range. `examples/rejected_loop_element_extent.elisa` pins the six ways the extent
can move: a `push` in the body, a call that takes the collection by reference, a whole assignment,
a whole assignment reached only under a branch among element writes, and a reference taken. None
of them may discharge an index bound, and the fixture requires that no `index-upper` goal in it is
proven at all.

### What it bought

Nothing measurable on `examples/kernel_replay_standalone.elisa` at first: 1210/2251, replay gaps
0, identical goal sites, because the loops there that write elements of what they walk also pass
those collections to calls elsewhere in the same function. Relaxing that constraint, below, takes
one of them: `index-upper-unproven` 222 to 221 and proven 1210 to 1211. What the rule really buys
is the shape above, which is the one an ordinary program is written in, and which this checker had
stopped proving.

The frame-wide aliased set was the binding constraint on this rule at first, and it was coarser
than it needed to be. It is in the disqualifier because a reference to the name may be held in
another binding that something in the body mutates through. Doing that needs the body either to
name the holder, which puts the holder in the body's own aliased set, or to hand control to a
callee. `proof_body_has_call` decides the second, and a body with no calls, no references and no
whole writes cannot reach anything it does not itself name, so the frame's set says nothing about
it and its element roots keep their extent. That is
`aliased_elsewhere_but_not_in_the_body` in the fixture, against
`aliased_elsewhere_and_a_call_here` in the rejected half, which is the same frame with a call
inside the loop. It moves `index-upper-unproven` on the kernel corpus from 222 to 221.

Not covered: a bound still does not travel across an equality by any route the corpus can use.
The rule for that is in the next entry, but the parallel arrays behind most of the corpus's
remaining index refusals have no equality to chain through -- the code under proof states no
contract relating the two collections' lengths.

## A bound could not travel across an equality

### What was wrong

`ys.count == xs.count` and `index < xs.count` do not give `index < ys.count`. Not in a loop, not
outside one:

```
def direct(xs: darray[i64]&, ys: mutable darray[i64]&, index: usize) -> void:
    requires ys.count == xs.count
    requires index < xs.count
    changes ys
    ys[index] <- 0
```

`index-upper-unproven`. Two collections a contract says are the same length is the most common
shape there is for indexing one from the other's bound, and the checker could not do it at all.

The comparison chain composes two recorded comparisons through a shared middle term, which is
exactly the reasoning needed here, but `proof_chain_step` read only `<`, `<=`, `>` and `>=` out of
a fact. An equality was not a step, so no chain closed.

### What changed

`proof_chain_step` accepts `==`. An equality is both non-strict steps at once -- `b == c` is
`b <= c` and `c <= b` -- so it reads as a step from either end of the chain and in either
direction, and it is always non-strict: an equality alone can never discharge a strict goal, and
`proof_chain_discharges` already refuses that composition. `proof_kernel_replay_chain_step`
carries the identical rule, which is what lets the certificates replay rather than be trusted.

The soundness guard is the one the rest of the chain already carries. `==` is the primitive
integer equality only for a witnessed scalar; on a struct it is a user `__eq__` under no order law
whatsoever. The two operands of the fact used as a step are the chain's anchor and its middle
term, and the caller requires a scalar witness for both -- the anchor before the search and the
middle before concluding -- so a struct equality can never become a step.

### Fixtures

`examples/comparison_chain_equality.elisa` requires the paired-collection write to prove with the
equality either way round, a non-strict order composed with an equality to give a non-strict
conclusion, and a whole loop of the paired shape; every certificate has to replay and
`trusted_assumptions` has to stay empty, which is what makes the kernel's own equality step
load-bearing rather than decorative. `examples/rejected_comparison_chain_equality.elisa` pins the
five ways it could be wrong: a struct equality used as an order step, an equality composed with a
non-strict order offered against a strict goal, two equalities offered against a strict goal, a
`!=` used as a step, and an equality that names one end of the chain instead of joining both.

### What it bought

The shape above, and its loop form, now prove and replay. On
`examples/kernel_replay_standalone.elisa` nothing is gained and nothing is lost: proven stays at
1210, all 1210 certificates replay with 0 gaps, and obligations rise 2251 to 2255 -- the four are
this change's own kernel code being checked, which is also why `function-summary-unverified` moves
333 to 337. The corpus does not benefit because the equality it would need is not there to use:
the parallel arrays that dominate its remaining index refusals are filled by callees that state no
contract relating their lengths.

Not covered: the chain still needs the two comparisons to share a syntactically equal middle term,
so `index < xs.count` with `ys.count == xs.count + 0` is not a chain. Nothing here relates two
collections that no contract relates, which is the corpus's actual problem.

## A region-polymorphic function could not state a contract about its own parameter

### What was wrong

Every logical contract mentioning a region-owned binding was refused with
`region-contract-unsupported`. That includes the one contract such a function actually needs:

```
def bounded[@r](nodes: darray[Node]& @r, index: usize) -> usize:
    requires index < nodes.count
```

So region-polymorphic code could be written but never specified, and every indexed access inside
it stayed unproven for want of a precondition it was not permitted to declare. On the kernel
corpus the region rules refuse 236 sites across 9 and 16 owner functions respectively, and
`proof_kernel_replay_resource_events[@r, @e, @s]` alone accounts for 142 of them.

The predicate behind the refusal is purely syntactic: an expression contains a region value if any
identifier in it names a binding with a region. `nodes.count` does, so it was refused. But
`nodes.count` is the collection's element count -- a machine integer copied out of it. Reading it
ties nothing to the collection's lifetime.

### What changed

`ProofResourceState` gains `binding_extent`, set from the *declared type* when a parameter or a
local is a collection: `darray[T]`, `view[T]` or `array[T, N]` under any number of reference and
storage markers, decided by `proof_resource_type_is_collection`. A type alias is not resolved, so
an aliased collection keeps the conservative answer. `proof_resource_expr_is_collection_extent`
then admits exactly `name.count` where `name` is such a binding, and both region-value predicates
return false for it before anything else.

The marker is driven by the declared type rather than the field's spelling, which is what the
adversarial fixture turns on: a `struct Holder` whose own field is called `count`, held by
reference in a region, is still refused.

### Fixtures

`examples/region_extent_contract.elisa` requires a bounds precondition and a postcondition over a
region-owned parameter's extent, an `ensure` over it, and a contract relating the extents of two
parameters with different lifetimes; all of it must prove with no findings and every certificate
must replay. `examples/rejected_region_extent_contract.elisa` pins four refusals: the struct whose
field is named `count`, an element of the collection, the binding itself, and a field of an
element.

### What it bought

On `examples/kernel_replay_standalone.elisa`: obligations 2255 to 2245 and failures 1057 to 1047,
with `region-call-opaque` 120 to 110. Proven is unchanged at 1211, replay gaps stay 0 and all 1211
certificates replay.

### A defect this exposed, and its fix

A region-polymorphic function that *indexes* its region-owned parameter and is otherwise fully
verified emitted a `resource-safety` certificate the independent kernel could not replay. The file
reported `proved_with_replay_gaps`, which is honest -- the tool says the replayer did not confirm
it -- but it was a producer/kernel mirror that was missing. Fifteen lines reproduced it, on this
commit's binary and on the previous one:

```
def c_indexes[@r](nodes: darray[Node]& @r, index: usize) -> usize:
    return 0 if index >= nodes.count
    return nodes[index].left
```

The same function without `@r` replays. Reading the events the producer emits for it settles what
was wrong, and it is not what the shape suggests. A return whose value is tied to an external
caller region is recorded as a `resource-region-return` marker carrying a *witness*: the
transition that supplies the region value. Replay checks that the witness is a use of a binding in
the region the marker names. The producer chose that witness by recency -- the last trace event,
if it happened to be a `resource-use`. `return nodes[index].left` records a use of `nodes` and
then one of `index`, so the witness was `index`, whose region is empty, and the kernel refused a
certificate that was in fact about `nodes`.

The producer now scans back through its own transitions for the most recent use whose binding is
in the returned region, bounded by `PROOF_RESOURCE_RETURN_WITNESS_SCAN`; past the cap the witness
stays unset and `region-return-witness-unsupported` refuses, which only ever loses a proof. The
scan carries the kernel's second condition too: replay requires the witness binding's mutability
to equal the return's, which is what stops a summary from handing the caller write access it never
held, so a shared binding is no longer offered as the witness for a `mutable T&` return. That case
also used to produce an unreplayable certificate and now produces a clean refusal.

Both are in the fixtures: `indexes_under_its_own_precondition` proves and replays, and
`shared_cannot_be_returned_mutable` refuses with `region-return-witness-unsupported`. The defect
predated the contract change and nothing in either suite reached it, because every
region-polymorphic function in the corpus and the examples still failed for another reason first.
Neither fix moves the corpus: 1211/2245, 0 gaps, all 1211 certificates replayed.

## A call statement was refused for naming a region

### What was wrong

`out.push(value)` was `region-expression-unsupported` whenever `out` carried a lifetime. The same
call with no lifetime parameter verified. Since a method call in statement position is how a
region-polymorphic function does most of what it does, that single gate accounted for 88 of the
116 `region-expression-unsupported` findings on the kernel's own source, all of them inside
functions with a lifetime parameter, and `proof_kernel_replay_resource_events[@r, @e, @s]` alone
carried those 88.

The gate asked the wrong question. An expression statement evaluates its expression and throws the
result away, so what it can drop is the *result*. The predicate it used returned true when the
*callee path* mentioned a region binding, which for a method on a region-owned receiver it always
does.

Nothing was being checked by the extra refusal. Dumping the transitions the producer emits for
`out.push(value)` with and without a lifetime shows the same `resource-use` of `out` in both, and
replay validates that use either way: the two event streams differ only in the lifetime recorded
on the bind. The receiver's liveness, its writability and its borrow overlap are all decided
there, by `proof_resource_check_expression`, which runs immediately before the gate.

### What changed

`proof_resource_expr_statement_discards_region_value` replaces the general predicate at the
statement gate only. For a call it asks whether the call's *result* carries a region, which is the
question the message was always about; for anything else it is the old region-value check, so a
bare region-owned expression or a `move` of one is refused exactly as before. The assignment gate,
which has to reason about what a binding receives, keeps the original predicate untouched.

### Fixtures

`examples/region_statement_call.elisa` requires a push into a region-owned collection, a push
through a field of a region-owned struct, and the same call with no lifetime at all, all verified
with no findings and every certificate replayed.
`examples/rejected_region_statement_call.elisa` is the boundary: a call returning `Cell& @r` whose
result is discarded is still refused, and that one finding is the only one the fixture may
produce.

### What it bought

On `examples/kernel_replay_standalone.elisa`: `region-expression-unsupported` falls from 116 to
38, obligations from 2245 to 2167 and failures from 1047 to 969. Proven is unchanged at 1211, all
1211 certificates replay, gaps stay 0 and `trusted_assumptions` stays empty.

Not covered: the 38 that remain are the other messages in that rule -- a region value flowing
through an assignment or an expression without a lifetime summary -- and they are a different
question from this one. `region-call-opaque` at 110 is untouched: a region-polymorphic call still
needs a converged lifetime summary and a mapping to a caller region.

## A helper without a lifetime could not be handed a region

### What was wrong

`proof_kernel_replay_node_at(nodes, root)` declares no lifetime parameter, and every
region-polymorphic caller in this codebase hands it a `nodes` that has one. That call was refused.
So was every call like it: `region-call-opaque` at 110 findings and
`borrow-call-summary-unsupported` at 95, with `proof_kernel_replay_resource_events[@r, @e, @s]`
carrying 50 and 36 of them.

The admission for exactly this shape already existed. A region-owned actual reaching a formal with
no lifetime is a capability the callee cannot name: with nothing to bind it to it can neither
allocate into that region nor return anything from it, and the lend rule already requires the
callee to return no reference and no region, with the borrow itself liveness-checked on both
sides. The problem was where the admission sat. The lend was attempted *only when the summary path
did not map the arguments*, and for these calls the summary maps fine and then fails to be
encoded -- the summary path places an actual from the callee's own trace, and a region-owned
actual has no formal lifetime to be placed against. The two admissions never composed, so a callee
that had a summary was worse off than one that did not.

### What changed

When the summary path maps a call and `proof_resource_record_call` then refuses it, the confined
lend is tried before the obligation is recorded. `record_call` returns before it mutates anything
on that path, so nothing half-written is left behind. What admits the call is the lend rule's own
guarantee, which never depended on whether the callee also had a summary.

A second change rides with it, from the same probe. A function whose *declared return type* is a
scalar primitive returns a copy: it cannot carry a lifetime however the expression producing it
was written. `return cell.value` out of a mutable region-owned parameter was being recorded as a
region return, which then demanded a witness whose mutability matched a return that is not a
reference at all, and refused. That marker is no longer emitted for a declared scalar return.

### Fixtures

`examples/region_lifetime_free_callee.elisa` requires a region-polymorphic caller to reach a
lifetime-free reader, a lifetime-free callee that writes through a mutable region-owned reference,
and a lifetime-free `push`, all verified with every certificate replayed.
`examples/rejected_region_lifetime_free_callee.elisa` pins the boundary: a lifetime-free callee
that *returns a reference* can keep what it is lent and is refused, and two overlapping mutable
actuals are refused whatever path admits the call.

`examples/rejected_unnamed_lifetime_lend.elisa` changed with this, and the change is the point.
It existed to pin that the summary path refuses a region-owned actual at a lifetime-free formal,
and that is no longer a boundary -- it was a limitation of the encoding, not a safety property.
Its case moved into `examples/unnamed_lifetime_lend.elisa`, where the summary-bearing callee is
now admitted beside the summary-less one, and the rejected half now holds a callee that returns a
reference, which is the boundary that actually exists. Before making that move I checked the
property the old fixture was standing in for: a caller that records a fact about a region-owned
binding, lends it mutably to a lifetime-free callee that overwrites it, and then claims the old
value is refused, with and without a lifetime parameter on the caller.

### What it bought

On `examples/kernel_replay_standalone.elisa`: `borrow-call-summary-unsupported` falls from 95 to
0 and `region-call-opaque` from 110 to 29. Obligations fall from 2167 to 1998 and failures from
969 to 793, and proven rises from 1211 to 1218. All 1218 certificates replay, gaps stay 0 and
`trusted_assumptions` stays empty.

Not covered: the 29 `region-call-opaque` that remain are the other two messages in that rule --
a call with no converged lifetime summary at all, and one requiring an exact verified region
summary. `borrow-call-opaque` at 59 is untouched.

## A short-circuit guard did not bound the operand it guards

### What was wrong

```
def guarded(xs: darray[i64]&, index: usize) -> bool:
    return index < xs.count and xs[index] > 0
```

`index-upper-unproven`. The same guard as an `if`, and the same guard as an early return, both
discharged the bound; only the spelling that needs no statement did not. That spelling is how a
bounds check is written when the answer is one expression, and it is how every accessor over a
parallel state array in the kernel's own resource replay is written:
`slot < state.binding_region_live.count and state.binding_region_live[slot]`, nine such functions,
each unverified on its own account and each dragging its callers into `dependency-unverified`
behind it.

### What changed

`proof_check_index_safety_value` reads the operator of a `Binary` node. For `and` it checks the
right operand against the facts plus the left; for `or`, plus the negation of the left. That is the
evaluation rule stated as a fact: the right operand of `and` runs only when the left is true, of
`or` only when it is false. The condition is recorded through `proof_add_branch_condition_facts`,
the same path an `if` uses, so its provenance is a `branch-condition` and its certificates replay
without a new rule in the kernel.

The guard has to be a stable term for the reason a branch condition does. A call in it is a second
call by the time the fact is used, so a guard carrying one -- or a `move`, or an unsupported form
-- records nothing and the right operand is checked against the facts that already stood.

### Fixtures

`examples/short_circuit_guard.elisa` requires the bound from an `and` guard, from an `or` guard,
from the `if` and early-return spellings that already worked, and from a conjunction that guards
two reads through a recorded count equality.
`examples/rejected_short_circuit_guard.elisa` pins the five ways a guard can fail to be one: `<=`
where `<` is needed, a guard over a different name, a guard on the *left* of `or` where the right
operand runs exactly when it fails, a guard written after the read, and a guard naming a call. No
`index-upper` goal in that fixture may be proven at all.

### What it bought

On `examples/kernel_replay_standalone.elisa`: proven rises from 1218 to 1282 and failures fall
from 793 to 712, with `index-upper-unproven` 221 to 157 and `function-summary-unverified` 337 to
320. Six functions move from `body-unverified` to `verified`, taking the root-cause set from 15 to
9. All 1282 certificates replay, gaps stay 0 and `trusted_assumptions` stays empty.

Not covered: the same guard does not yet bound anything but an index -- a `requires` on a call in
the right operand is still checked against the outer facts -- and the rule reads only the
immediate left operand, so a guard two conjuncts away reaches the read only because
`proof_add_branch_condition_facts` splits a conjunction into its components.

## The kernel's own recursive helpers declared no termination measure

### What was wrong

`recursive-summary-unsupported`, 21 findings across four functions, all of them in the kernel's
own replay module. The message is "recursive executable summaries require matching checked
lexicographic termination measures", and the machinery it names already exists: a call inside a
recursive component may consume the callee's summary once both declarations carry measures of the
same arity that the checker has itself verified, or once the structural walker has certified both.

The four functions carried neither. `proof_kernel_replay_unsigned_width_in_expression`,
`proof_kernel_replay_unsigned_expression_safe`,
`proof_kernel_replay_resource_index_expression_valid` and
`proof_kernel_replay_resource_place` all guard `depth >= 127` (or `>= 128`) and recurse with
`depth + 1`, which is exactly the shape their siblings -- `proof_kernel_replay_substitute`,
`proof_kernel_replay_collect_name_equalities` -- already declare a measure for. Nothing in the
checker was missing. The code under proof simply did not state what it does.

### What changed

Each of the four gained `requires depth <= 127` (128 for the one whose own guard is 128) and
`decreases 127 - depth`, matching the established pattern in the same file. That is a change to
the code being proved, not to the checker: the contracts state a property the functions already
satisfied, and the checker then discharges the recursive calls against them.

### What it bought

On `examples/kernel_replay_standalone.elisa`: `recursive-summary-unsupported` falls from 21 to 1
and `function-summary-unverified` from 320 to 304. Proven rises from 1282 to 1377 and failures
fall from 712 to 677, against obligations that rise from 1981 to 2041 -- the new contracts are
themselves obligations. Verified functions go from 99 to 103, and the recursive components that
cannot export a contract from 7 to 5. All 1377 certificates replay, gaps stay 0 and
`trusted_assumptions` stays empty.

### One measure the compiler refused

`proof_kernel_replay_bounded_model_visit` recurses on an index toward `names.count`, so its
measure is `names.count - index`. Adding it took `recursive-summary-unsupported` to 0 and
`elisac-stage1` accepted it, but `elisac-stage0` -- which `dogfood.sh` uses to rebuild the runtime
and every kernel harness, to keep an installed stage1 from becoming an implicit bootstrap
dependency -- rejected it outright: "cannot prove the `decreases` measure strictly decreases across
the mutually-recursive cycle", and separately could not establish `0 <= names.count` at the call.
The measure is reverted. It bought nothing measurable in any case -- proven was unchanged and the
refusal it removed reappeared as an unproven precondition at the self-call -- and a source file the
bootstrap compiler will not accept is not a trade worth making. The remaining finding is that one
function.

### Not covered

The unproven preconditions that remain at recursive calls are the unsigned-increment limitation
recorded elsewhere in this file: `index + 1 <= names.count` does not follow from
`index < names.count` for an unsigned type without a constant upper bound. That is a checker gap,
not a missing contract, and it is what stops the last recursive component from closing.

## An interval that followed from two facts never reached the overflow guard

### What was wrong

`index + 1` may not enter an arithmetic proof unless the engine can show it does not overflow, and
the guard asks for a constant interval on the base. The interval pass collected only the bounds a
fact states about a name *directly*, so

```
requires index < count
requires count <= 1000
requires index >= 0
ensure result <= count
return index + 1
```

was refused. `index <= 999` follows from the first two premises, and the engine builds exactly the
constraint graph that derives it -- but it built it *after* running the guard, and only to answer
the goal.

Reduced further, the engine handles a constant offset that is already in the premise
(`a + 1 <= b` proves `a + 1 <= b`) and weakens strictness (`a < b` proves `a <= b`), and fails the
moment an offset has to move (`a < b` does not prove `a + 1 <= b`). The failure is the guard, not
the difference reasoning.

### What changed

`proof_close_bounds_through_differences` propagates intervals along the constraints before the
guard runs: `x - y <= c` with `y <= U` gives `x <= U + c`, and with `x >= L` gives `y >= L - c`.
Each step is an ordinary interval inference that can only narrow an interval already implied, so
nothing is admitted that the facts did not already carry. The pass is capped at four rounds, which
keeps it linear; a bound needing more rounds is simply not derived, which only loses a proof. The
constraint collection moves above the guard for the same reason.
`proof_kernel_replay_close_bounds_through_differences` is the identical rule in the kernel, which
is what lets the certificates replay.

### Fixtures

`examples/bound_propagation.elisa` requires the increment under a bounded limit, the same through
a two-constraint chain, and the lower direction; every certificate must replay and
`trusted_assumptions` must stay empty. `examples/rejected_bound_propagation.elisa` pins four
refusals: a lower bound on the far name carries nothing upward, a non-strict premise does not
shift, a bound on an unrelated name reaches nothing, and the unsigned increment with no constant
bound anywhere stays refused.

### What it bought, and what it did not

The shape above, which is every bounded loop's increment. On
`examples/kernel_replay_standalone.elisa` it is worth one goal: proven 1377 to 1378 against
obligations 2041 to 2042, with the histogram otherwise unchanged, 0 gaps and all 1378 certificates
replayed. The kernel's own loops count with `usize` against `collection.count`, and no constant
bounds them, so propagation has nothing to carry.

That last point looked like a limit of the numeric domain. It was not, and the next entry closes
it: the range argument for an increment does not have to be numeric at all.

## An unsigned increment needed no interval, only a peer

### What was wrong

`index + 1 <= count` over `usize`, from `index < count`, was refused however the facts were
arranged. The reason recorded in the previous entry was the numeric domain:
`proof_unsigned_width_max` caps a 64-bit unsigned value at the signed maximum, because that is the
widest interval this proof AST holds, so no interval argument can ever admit `index + 1` for a
`usize`.

That reason is correct and the conclusion drawn from it was wrong. The engine already contained a
counterexample to its own framing: a guarded unsigned *subtraction* is admitted from
`right <= left`, with the comment "range-safe even when its operands are wider than the kernel's
i64 interval representation". The argument there is relational. The same argument works for
addition and nobody had written it.

`a < Y` with `a` and `Y` of the same unsigned width gives `a + 1 <= Y`, and `Y` is at most the
type's maximum by typing alone. So `a + 1` is in range, with no magnitude mentioned anywhere.

### What changed

`proof_unsigned_increment_has_strict_peer` decides exactly that, and the `+` branch of
`proof_unsigned_expression_safe_with_bounds` consults it before falling through to the interval
test, mirroring the `-` branch beside it. `proof_affine_unsigned_peer_safe` is the same rule for
the difference tier, which reads the strict relation off the constraint it has already built.
Both have kernel mirrors, which is what lets the certificates replay;
`proof_kernel_replay_difference_comparison` gained the `children` parameter it needed to read a
width.

The peer must be a bare name. A peer that mentioned the base could justify itself -- `a < a + 1`
is precisely the claim whose range is being decided -- and a name cannot.

### The suite caught a real break on the way

The first attempt also propagated derived intervals into this guard, on the same reasoning as the
goal tier. `examples/rejected_unsigned_fact_explosion.elisa` then proved `x == 0` from `x == 255`.
Its premises -- `x == 255`, `y == x + 1`, `y == 0` -- all hold for a `u8` at those values, because
`y == x + 1` is a *modular* equality. Read as an integer difference constraint it gives `x <= -1`,
which with `x >= 0` is an inconsistent interval, and an inconsistent interval proves anything.
Propagation is therefore confined to the goal tier, which runs only after every affine term in the
goal has been certified non-wrapping; the guard that decides *whether* a term wraps may not be
justified by constraints that assume it does not. The comment at that call site says so.

### Fixtures

`examples/bound_propagation.elisa` gains the unsigned increment under a strict peer, with the peer
on either side of the comparison. `examples/rejected_bound_propagation.elisa` replaces its former
"this is the documented limit" case with the three ways the peer rule can be misapplied: a step of
two, which no strict peer justifies; a non-strict peer, which leaves `index == count` where the
claim is false; and a peer bounding a different name.

### What it bought

On `examples/kernel_replay_standalone.elisa`: proven rises from 1378 to 1385 against obligations
rising 2042 to 2052, which is this change's own code being checked. Verified functions go from 104
to 106. All 1385 certificates replay, gaps stay 0 and `trusted_assumptions` stays empty.

The peer is a bare name or a field of one. Neither can spell the base's own increment, which is
what the restriction is for, and admitting the field form is what lets `index < values.count` bound
`index + 1` at all. Reaching the *goal* `index + 1 <= values.count` needs the shift rule in the
next entry.

## A strict fact would not shift by one where its bound lived in a field

### What was wrong

`a < R` gives `a + 1 <= R` over the integers, for any term `R`. The difference engine draws that
conclusion whenever it can name both sides, and `ProofAffine.base` is one bare identifier, so it
cannot name `box.limit` at all. The increment every bounded walk performs was therefore refused
wherever the bound lives in a field -- which, for a collection, is every loop in this codebase.

The obvious repair is to widen the affine atom from a name to a place. That rekeys `ProofBound`,
`ProofDifference` and `ProofAffine` and every comparison over them, in the producer and in the
kernel: about two hundred sites that must agree exactly or the certificates stop replaying. The
comparison chain was added earlier to work around the same limit without paying that, and the same
approach works here.

### What changed

`proof_strict_shift_goal` matches the shifted side structurally against the strict fact's own
right-hand side. It needs no atom: `a + 1 <= R` is discharged by a fact `a < R` where `R` is the
same term, whatever shape `R` has. The goal must be non-strict -- `a < R` does not give
`a + 1 < R` -- and the shift is by one. It sits behind the overflow guard, because the conclusion
is only sound where `a + 1` does not wrap, and for an unsigned term that is exactly what the peer
rule in the previous entry decides *from the same fact*. `proof_kernel_replay_strict_shift` is the
mirror.

### Fixtures

`examples/strict_shift.elisa` requires the shift to a field place, to a bare name, and from a fact
written the other way round. `examples/rejected_strict_shift.elisa` pins the four ways it does not
apply: a non-strict premise, a strict conclusion, a step of two, and a fact bounding a different
term.

`examples/rejected_bound_propagation.elisa` lost two cases to this, and that is the right outcome
rather than a regression. `lower_bound_does_not_bound_above` and `bound_on_an_unrelated_name` were
in the rejected half because the only route to them was an interval and no interval was derivable.
Both claims are true, and the shift proves them from `index < count` without bounding `index` at
all, so they moved to the accepted half under names that say what they now show. What stays refused
there is what is actually false: a step of two, a non-strict peer, and a peer bounding another
name.

### What it bought

On `examples/kernel_replay_standalone.elisa`: proven 1385 to 1388 against obligations 2052 to 2061,
which is this change's own code. Verified functions 106 to 108. All 1388 certificates replay, gaps
stay 0 and `trusted_assumptions` stays empty.

`index + 1 <= values.count` over `usize` needed one more thing: the guard in front of the shift
asks whether `values.count` is a peer of the same unsigned width, and width markers are keyed by
bare name, so a field place had none.

`proof_peer_unsigned_width` answers that question and only that question. A collection's element
count is a `usize`, so it reports the platform width for `name.count`, which is safe in the
direction the peer rule uses it: the rule needs `peer <= TYPE_MAX(base)`, and a peer reported
*wider* than it is can only make the test fail. It deliberately does not reach
`proof_unsigned_width_in_expression`. Putting it there instead was tried first and measured: it
makes every arithmetic term containing `.count` subject to the unsigned wrap guard, and the corpus
went from 1388 proven to 1349 -- thirty-nine proofs lost to buy one shape. The narrow version costs
nothing and buys the same shape. `shift_to_a_collection_extent` in the fixture is that shape, and
`another_collection_extent` in the rejected half is a fact about a *different* collection, which
gives nothing.

The affine rekey remains the general repair; this tier, the comparison chain and this width query
are three rules working around it.

## Measured: what is left on the kernel's own source

The finding counts are dominated by cascade. Of 191 functions in
`examples/kernel_replay_standalone.elisa`, 109 are `verified`, 69 are
`dependency-unverified` -- unverified only because something they call is -- and one exports a
widened-state contract. The whole of the rest is 14 declarations: 9 with an unverified body and 5
in a recursive component that cannot export a contract. They carry 88 findings between them, and
every one of the 320 `function-summary-unverified` findings is downstream of those 14.

Classifying all 88 by what each would actually take:

| Count | Shape | What it needs |
| --- | --- | --- |
| 31 | `borrow-call-opaque` on `xs.extend(ys)` and `visiting.resize(nodes.count)` | a resource model for one builtin |
| 26 | `children[node.children_start + index]` | a sum of two variables, and a contract on the range validator |
| 14 | `right_names[index]` under `for index in 0..<left_names.count` | a contract relating two parallel arrays |
| 7 | `loop-invariant-missing` | invariants on `while` loops in the subject code |
| 4 | `call-requires-unproven` | the unsigned increment at a self-call |
| 4 | `current.root` as an index | a field place as an index term |
| 1 | `recursive-summary-unsupported` | the measure `elisac-stage0` refused |
| 1 | `loop-condition-opaque` | a call in a `while` condition |

Three of these are worth stating precisely, because the names understate how narrow they are.

**The 31 are one method.** `push`, `resize` and `truncate` all verify; only `extend` does not, and
the message says why: "a call argument carries a resource, but no converged callee resource
summary". `xs.push(v)` passes a scalar and needs no summary; `xs.extend(ys)` passes a collection,
and there is no builtin resource model to say that `extend` reads its argument and writes only its
receiver. That is the confined-lend shape the checker already admits for user functions. 27 of the
31 are in `proof_kernel_replay_resource_copy`, which is nothing but a sequence of `extend` calls.

**The 26 are the sum the affine atom cannot hold.** `ProofAffine.base` is one identifier, so
`node.children_start + index` is not a term. The obligation is
`children_start + index < children.count`, and the facts that would discharge it are
`children_start + children_count <= children.count` and `index < children_count`. The first does
not exist: `proof_kernel_replay_child_range_valid` decides exactly that property and returns a
bare `bool` with no `ensure`, so calling it establishes nothing. So this cluster needs both a
contract on that helper and a rule for `X + Y < C` from `X + N <= C` and `Y < N` -- which, like
the strict shift and the comparison chain, can match structurally instead of requiring the rekey.

**The 14 are a missing contract, not a missing rule.** `proof_kernel_replay_close_equalities` walks
`0..<left_names.count` and indexes `right_names`; the two arrays are pushed in tandem by
`proof_kernel_replay_collect_name_equalities`, which states no relation between their lengths. The
equality step in the comparison chain would discharge the bound from
`left_names.count == right_names.count`, and nothing produces that fact. The contract is on a
recursive function, so it also needs the recursive-summary path, which is available now that the
measures are in place.

Nothing in this table needs the affine rekey outright. The 26 are the only cluster where it is the
general repair rather than one option.

### Each of the three was then probed, and none is a one-line change

**The 31 need a builtin resource summary, which does not exist as a mechanism.** The refusal is
correct as the checker stands: an argument that carries a resource reaches a callee with no
summary, and a callee with no summary could retain it. `push` and `resize` are silent only because
their arguments are scalars, not because anything models them. Admitting `extend` means saying,
somewhere the kernel can replay, that its argument is lent shared and not retained -- the same
statement the confined-lend path makes for a user function from its declared parameter modes, but
there is no declaration to read modes from. A name-based allow-list is not enough on its own: a
user function named `extend` is found in the function table and would take the normal path, but an
`extend` the table does not contain would be modelled on its name alone, which is an assumption
rather than a check.

**The 14 cannot be written in this language.** The contract wanted is on
`proof_kernel_replay_collect_name_equalities`, which returns `void`:

```
requires left_names.count == right_names.count
ensure left_names.count == right_names.count
```

`elisac-stage1` declines the function outright -- "backend could not produce a linkable unit;
declined 1: proof_kernel_replay_collect_name_equalities (return statement)". Reduced, the rule is
narrower and harsher than it first looks: a `void` function may not carry an `ensure` at all, with
or without an early return. Two eight-line functions, one with an early `return` and one without,
are both declined with "contract statement". `requires` and `decreases` on a `void` function are
fine, which is why the termination measures earlier in this file went in without trouble. So this
cluster needs the helper restructured to return a value before it can be specified at all, which
is a change to the kernel's own shape rather than to its contracts.

**The 26 need the fact and the rule, and the fact is the same problem.**
`proof_kernel_replay_child_range_valid` also returns a bare `bool`, so its postcondition would have
to be `ensure not result or start + count <= total` on a value-returning function -- allowed, unlike
the `void` case -- but proving it needs `start + count <= total` from `count <= total - start`,
which is the two-variable sum again. The contract and the rule that would use it are blocked on the
same missing piece.

## Coverage still required

| Code | Required audit coverage |
| --- | --- |
| `src/main.elisa` | Source import, diagnostics, every CLI admission gate, serialization, fingerprints, target repair |
| `src/proof/import.elisa` | Compiler-compatible include expansion, failures, cycles, path identity |
| `src/proof/model.elisa` | Report invariants, source provenance, certificate and side-table ownership |
| `src/proof/check.elisa` | Typed symbolic execution, state changes, contracts, calls, frames, loops, termination |
| `src/proof/expr.elisa` | Substitution, binding and capture, equality, numeric semantics, unsupported forms |
| `src/proof/linear.elisa` | Arithmetic soundness, bounds, overflow, case splits, quantified reasoning |
| `src/proof/kernel_core.elisa` | Primitive bounds, arithmetic, arena operations and formalized contracts |
| `src/proof/kernel.elisa` | Meaning-preserving lowering and complete type information |
| `src/proof/kernel_replay.elisa` | All public admission APIs and inference rules, malformed arenas, numeric and resource semantics |
| `src/proof/replay.elisa` | Source/arena agreement, provenance, summary dependencies, legacy replay paths |
| `src/proof/resources.elisa` | Ownership, aliasing, region lifetime, frames, indexing and state joins |
| `src/proof/tactics.elisa` | Every transition, substitutions, branches and source binding |
| `src/proof/tactic_json.elisa` | Exact parsing, schema validation, tree replay and source binding |
| `scripts/build.sh`, `scripts/test.sh`, `scripts/dogfood.sh` | Compiler/runtime selection, exit-status handling, actual test coverage and reproducibility |
| Existing examples and design documentation | Expected verdicts, adversarial coverage, supported-fragment claims and trust assumptions |

Recent commits provide targeted evidence for quantifier kind preservation, exact source tactic
binding, rejection of lossy JSON integers, floating-point exclusions, and unsigned alias and
refinement widths. They do not establish type preservation through every symbolic transformation.

Completion requires coverage of the full table and resolution of every confirmed open defect.
