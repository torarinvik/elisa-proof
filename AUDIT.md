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
postcondition. `examples/rejected_uncaptured_binding.elisa` is the adversarial half and pins the two
ways this could go wrong: a binding the list *does* name whose value the loop overwrites must not
keep its old value, and a fact the loop body establishes must not escape a loop that may run zero
times.

Not covered. The block's own exit state is still discarded rather than merged, so a loop with an
invariant proves that invariant inside its private state and exports nothing from it. Importing that
state is a larger step than this one: it needs the loop's post-state to be sound for the
zero-iteration path, which the capture-list argument does not have to reason about at all.

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
