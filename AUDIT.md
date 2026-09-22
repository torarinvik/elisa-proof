# Full implementation audit — in progress

Passing the current suites is regression evidence, not completion of the full audit.
The objective covers all existing implementation code, scripts, proof fixtures, and their
assumptions about the compiler. No module below is yet certified as fully audited.

## 2026-09-19 checkpoint: constants refactor must preserve the verification frontier

The committed constants cleanups (`03aa2ea`, `8d18da4`, and `d622b03`) preserve the proof
matrix and replay counts. A broader cleanup in `src/proof/kernel_replay/unsigned_bounds.elisa`
was intentionally not retained: replacing its inline bounds and recursive depth literals with
module constants caused the bounded source audit to stop verifying
`proof_kernel_replay_difference_query` and, transitively, `proof_kernel_replay_arena_shape_valid`.
The generated reports still had zero replay gaps, but the required verified declaration set
shrunk, so accepting the refactor would have weakened the trust boundary. The change was reverted
and the working tree is clean. This is evidence that constants in recursive proof code must be
introduced with a verification-frontier regression check, not only a native build check.

## 2026-09-14 checkpoint: Elisa validity and admission exhaustion

`proof_source_validate_statement_propositions` silently returned at its nesting bound.
It now records a failed obligation and a `contract-proposition-type` finding before
returning. Empty statement lists remain harmless. The new
`examples/rejected_proposition_nesting.elisa` regression requires both exit status 1
and the explicit exhaustion finding. This closes a missing fail-closed boundary;
it is not evidence that a false theorem previously passed the whole verifier.

The complete `scripts/test.sh` matrix passed with both pinned Stage0
(`1d1ddf1c5260e1e02e64466dafc02bb6e792cfa4`) and an audit Stage1 candidate built
from the compiler worktree. This checks compilation and tested behavior, not full
language conformance: compilation still emits effect-grant warnings. Proof source
files remain under 600 lines (largest: 593). The reviewed sources contain no
dereference-style `*values` expression; unary dereference is not Elisa syntax.

Related compiler repairs are committed in `6524bf3a`: region provenance through
aggregate/value expressions, conservative treatment of unknown projections,
match/catch local mutability, argument coercion, native AoS ABI alignment, and
LLVM verification before optimization/emission. The verifier message is disposed
on both success and failure. The audit candidate passed 318 diagnostic fixtures,
match-expression smoke tests, Stage0/Stage1 conditional-call runtime parity at O2,
and packed-AoS row-width tests. Native 64-bit ABI coverage is not 32-bit coverage.
This checkpoint does not update the proof assistant's pinned compiler frontend or
install the audit compiler as the user's default product.

The full-source run against `build/snapshot/elisa-proof/src/main.elisa` did NOT
complete: the watchdog stopped it after 93.77 seconds at 1,507,568 KB RSS
(limit 1,500,000 KB). There is no complete JSON report or replay-gap count for
that run, and no claim of self-verification. Dogfood was not rerun for this checkpoint.

## 2026-09-14 follow-up: aggregate joins and nested container growth

Further Stage0 review found that assigning a fresh aggregate with a nested region-bearing
container on only one branch could lose its provenance before return. The Go compiler now
propagates interior taint from fresh aggregate producers; a positive escape fixture and an
unchanged-aggregate negative control cover the join. The fix and regression were committed in
the Stage0 source repository at `bd2353db` (included in the clean installed Stage0 revision
`24c3efc28b30f590088224d441b776e94c64be29`). The complete Go test suite passed at that revision.

The self-hosted checker had a related gap for mutating a non-local container inside a nested
region. It now rejects growth that would allocate the container's backing in the short-lived
arena, including scalar-element containers, while allowing a receiver with an explicit or
inferred longer-lived owner. Positive and negative fixtures cover both branch-tainted returns
and nested growth. Stage0 and a fresh Stage1 built from the clean Stage0 each passed all 322
diagnostic fixtures; both stages reject the unsafe cases and accept the safe controls. The
self-hosted fix is committed as `9791a8e1`, and `ELISA_COMPILER_REV` now pins that exact commit.

These findings close the specifically identified branch-assignment and nested-growth cases,
not all region semantics. Explicit-region allocation semantics and other region combinations
remain audit targets. The full-source proof run is still incomplete as recorded above, so no
self-verification claim follows from these compiler checks.

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

## Repaired: unsigned field and element widths were lost before congruence replay

Reproducers: `examples/rejected_unsigned_field_width_congruence.elisa` and
`examples/rejected_unsigned_element_width_congruence.elisa`. A `u8` field or array element and a
same-valued `u16` field or element were assumed equal, and the checker certified that adding one
to both still gave equal results. At the `u8` endpoint, the first addition wraps to zero while the
`u16` addition yields 256. Before the repair, both reports said `proved`, with all certificates
replayed and no gaps: the producer and independent kernel agreed on the unsound result.

The source importer did emit scalar-type witnesses for these places, but their unsigned widths
were either deliberately excluded from the arithmetic-width resolver (struct fields) or never
encoded at all (container elements). The broad place marker must also serve synthetic `.count`
places; feeding every such width into the arithmetic guard had previously caused unrelated signed
terms to inherit `usize` bounds. That containment accidentally left real unsigned field and
element arithmetic to the signed-integer congruence rule.

The fix makes the existing exact field marker participate in arithmetic-width lookup, and extends
the existing scalar-element marker with an optional validated width for unsigned leaves of nested
containers. The source resolver and kernel independently match the exact place/container plus
element depth, then apply the existing overflow-safety guard before signed arithmetic or
congruence can run. This adds no duplicate fact per field or container, and synthetic `.count`
witnesses remain outside arithmetic-width lookup. These witnesses are retained and invalidated
with the root binding, and the element marker remains an inert type fact in bounded-model replay.
The old eight-subscript cutoff silently dropped the width marker for deeper nested arrays; the
producer and kernel now share a 64-level schema limit, with AST traversal still separately bounded.
`examples/rejected_unsigned_nested_element_width_congruence.elisa` checks a nine-level type.

The audit also found unsound width propagation: a call result inherited its argument's width, and
an `if` result could inherit the condition's width. The producer now refuses to infer a call's
result width from its children and derives an `if` result width only from both value branches; the
kernel mirrors those rules. The signed-return counterexample in
`examples/rejected_unsigned_place.elisa` and
`examples/rejected_unsigned_condition_width_inference.elisa` cover both boundaries.

Unsigned nonnegativity is a type invariant even when arithmetic wraps. The previous negative
fixture incorrectly required an unsigned subtraction result to remain unproven for `0 <= result`.
The producer and kernel now admit that invariant without treating the wrapped expression as a
mathematical integer for other goals. The fixture now expects the subtraction and nested
subtraction nonnegativity claims to prove, while still rejecting signed nonnegativity, strict
positivity, wrapped upper bounds, and using a wrapped sum as an index.

One replay gap also exposed an ordering issue: an unrelated unsafe premise blocked a ground
`0 <= 127` certificate. The kernel now evaluates only direct integer-literal comparisons before
premise-dependent wrap checks. It deliberately does not move compound constant arithmetic ahead
of those guards.
`examples/rejected_unsigned_field_overflow.elisa` and
`examples/rejected_unsigned_element_overflow.elisa` also ensure simple endpoint claims do not
become proofs. The positive `examples/unsigned_field_increment_bound.elisa` keeps the useful
same-width relational case: `x < y` proves `x + 1 <= y`.

Coverage now requires all overflow, width-congruence, nested-width, and conditional-width
counterexamples to remain unproven with complete replay; the positive field-bound and unsigned
nonnegativity examples must prove. The full `scripts/test.sh` matrix passed under the pinned
Stage1 compiler, including the standalone replay audit (1,111 certificates, zero gaps).
`scripts/dogfood.sh` also passed under Stage1, including the standalone report (1,555 obligations,
zero replay gaps) and native kernel/runtime harnesses. The optional Stage0 bootstrap portion was
skipped because Stage0 is unavailable on the sanitized PATH; no Stage0 binary was used.

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

### Still not covered

Field selection, indexing, slicing, and the aggregate constructors need a witness that the
receiver's selector is the language's own and that the selected type's equality is primitive.
That witness is not represented in the term language, so those formers stay excluded and the
adversarial fixture pins the refusal. Congruence through a call additionally needs a determinism
witness. Scalar witnesses are emitted for scalar locals as well as parameters, but the positive
congruence suite previously covered only parameter witnesses; a regression now exercises opaque
locals whose equality is introduced by a runtime guard.

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

## Repaired: the checker died of a stack overflow on half a megabyte of source

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

The crash was first avoided in the importer by hoisting the byte binding, but that only hid a
compiler defect and left every other Elisa program with the same hazard. The root cause was
subsequently reduced to the compiler's local-scope metadata: scoped declarations were removed
from `names`, `slots` and `types`, but not from the parallel mutability and arena metadata arrays.
When a later `mutable ...&` binding was looked up, the stale array entries shifted its mutability
bit. A plain `<-` was then lowered as a write through the zero reference instead of a rebind,
producing a null store in `arena_take_free_block` and a native `SIGSEGV` during lexer darray
growth.

The compiler now restores every index-parallel local array together, and the zero-initialized
declaration path records mutable reference bindings just like ordinary initializers. The fix is
committed in compiler revision `3b48e949`, with a stage0/stage1 regression in
`test/parity/mutable_ref_scope_smoke.sh`. The importer deliberately uses the original conditional
initializer again, so the proof build now exercises the repaired backend directly.

`proof_expand_file` reads the file it is expanding one byte per iteration through exactly that
shape:

```
byte: u8 = 10 if at_end else contents[index]
```

so a source file of *n* bytes used to leak *n* times. The repaired compiler now lowers this
conditional without per-iteration frame growth. The source-level conditional remains in place as
a regression against reintroducing the backend defect.

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

## A sum of two terms is bounded by what its guarded subtraction names

### What was wrong

`ProofAffine.base` is one bare identifier, so `start + index` is not a term any tier can name, and
`children[node.children_start + index]` is the most common indexed access in the kernel's own
replay module. The previous measurement called this the one cluster where widening the affine atom
is the general repair rather than one option. It is still the general repair. It is not the only
one.

### What changed

Both facts that bound such a sum are structural, so `proof_sum_bound_goal` searches for them
structurally, the same way the comparison chain and the strict shift reach terms the atom cannot
name. The rule is: `m <= C - a` together with `a <= C` gives `a + m <= C`, and a term under `m`
inherits the bound, so `b < m <= C - a` gives `a + b < C`. The guard on the subtraction is what
makes `C - a` meaningful for an unsigned type, and it is exactly what such code already writes
beside it.

The search returns the bounding term as well as the strictness, because the same answer settles
the range question: the sum is at most `C`, so it cannot wrap whenever `C` is a term of the same
unsigned width. That is the relational argument the peer rule uses for `a + 1`, and it is the only
kind a 64-bit unsigned value can have. Both the goal tier and the unsigned guard consult it.
`proof_kernel_replay_sum_bound` is the mirror.

### The premise this rule will not read

The obvious formulation is the other one: from `a + m <= C` and `b < m`, conclude `a + b < C`. It
was implemented first, and it is unsound. For a fixed-width type `a + m <= C` is a claim about a
sum that may already have wrapped: at `start = MAX, count = 1, total = 0` for `usize`, the premise
holds modulo 2^64 while the mathematical sum does not, and reading it as an integer bound proves
`start + 0 < 0`. The same objection is why bound propagation is confined to the goal tier, and it
is what `examples/rejected_unsigned_fact_explosion.elisa` has been pinning all along. The
subtraction form says the same thing with no sum in the premise, and the rejected fixture pins the
wrapped reading by name.

### Fixtures

`examples/sum_bound.elisa` requires the transposed subtraction, a term inheriting the bound
through a strict step, the same for a signed sum, and the operands commuted.
`examples/rejected_sum_bound.elisa` pins four refusals: the modular premise above, a subtraction
with no guard on it, a non-strict step offered against a strict goal, and a bound on a different
term.

### What it bought, and what it did not

On `examples/kernel_replay_standalone.elisa`: proven 1388 to 1394 and verified functions 109 to
110, against obligations 2061 to 2088, which is this change's own code in both engines. All 1394
certificates replay, gaps stay 0 and `trusted_assumptions` stays empty.

The 26 findings this cluster was measured at are not among them, and the reason is not the rule.
`proof_kernel_replay_child_range_valid` decides exactly the premise the rule needs and returns a
bare `bool`, so the fact does not exist. Giving it one runs into the shape of its own body: the
postcondition has to be `not result or count <= total - start`, and on the early-return path where
`start > total` that subtraction is unguarded, so the goal is refused before any tier sees it.
`ensure not result or start <= total` alone does verify, which is half of what the rule needs.
Closing the cluster therefore needs the validator restructured so the subtraction is guarded on
every path it appears on -- subject-code surgery at 26 call sites, not a checker change.

## An operand a short circuit never evaluates owes no range argument

### What was wrong

The unsigned range gate walks the whole expression: every fact, and the goal, must have every
unsigned subterm provably inside its type's range before any tier is allowed to look at it. The
walk did not model `or` and `and`, which short-circuit. It charged an operand for arithmetic that
the machine never performs.

The previous entry closed a sum rule and then reported that the 26 `children[start + index]`
findings stayed open, because the fact the rule needs does not exist:
`proof_kernel_replay_child_range_valid` returns a bare `bool`. It said the postcondition that
would create the fact, `ensure not result or count <= total - start`, is refused on the early
return where `start > total` leaves the subtraction unguarded. That diagnosis was one step short.
The goal on that path reads `not false or count <= total - start`. Its left operand is already
true, so the subtraction on the right is not evaluated there at all.

### What changed

`proof_unsigned_expression_safe_with_bounds` now folds a settled left operand. It still charges
the left operand in full. If the left is a boolean constant that decides the operator -- true for
`or`, false for `and` -- the right operand is unreachable and is not walked. Otherwise the walk
continues into it unchanged. `proof_constant_bool` reads the constant through the `not` that
contract substitution leaves behind, which is how `result` becomes `false` on a returning path.
`proof_kernel_replay_constant_bool` and the same fold in
`proof_kernel_replay_unsigned_expression_safe` are the mirror.

### Why a skipped operand cannot carry an unsound fact

The fold is the only place the gate stops walking, and the gate is what licenses the fact
collectors to read a term as integer arithmetic. `proof_collect_bounds`,
`proof_collect_unsigned_order_facts` and `proof_collect_difference_constraints` all split `and`
unconditionally, so a fact of the form `false and P` would hand them `P` while the gate passed the
whole. Every such fact is unreachable. A `requires` in that shape is a precondition no caller can
discharge; a branch or loop condition in that shape guards dead code; a callee `ensure` in that
shape says the callee does not return, which the callee had to prove to be verified at all. None
of them describes a state a program reaches. `or` is not affected either way: no collector
descends through it.

As a goal the fold decides nothing. `proof_goal_depth` splits `and` into both conjuncts and `or`
into either, so `false and P` still owes `false` and `true or P` was already discharged by its left
operand. The fold changes which goals are attempted, never which are proved.

### Fixtures

`examples/settled_operand.elisa` carries the shape the validator needs, the same shape written as
a conjunct, and a third function whose left operand stops settling the answer, so the right one is
still owed and still has to bring its guard. The previous commit's binary refuses the first two and
proves the third.

`examples/rejected_settled_operand.elisa` is the boundary. `false or X` and `true and X` still owe
`X`; an opaque left operand settles nothing and the gate still refuses the subtraction beneath it;
and a settled operand says nothing about the sibling conjunct standing beside it. All four are
refused, with no semantic errors and no replay gaps.

### What it bought

On `examples/kernel_replay_standalone.elisa`: proven 1394 to 1400 and verified functions 110 to
111, against obligations 2088 to 2094, which is this change's own code in both engines. All 1400
certificates replay, gaps stay 0 and `trusted_assumptions` stays empty.

This does not by itself close the 26-finding cluster. It removes the reason the previous entry
gave for leaving it open: the postcondition `ensure not result or count <= total - start` now
verifies on a body that returns `false` outright. What remains is the two-guard body, where a
negated early return does not make the subtraction range-safe for the statement after it, while
the same condition written as `requires start <= total` does. That asymmetry, not the disjunction,
is now the blocker.

## A guard reaches the statements after its own early return

### What was wrong

An unsigned subtraction is range-safe when a fact orders its operands, and the facts that can say
so are collected by `proof_collect_unsigned_order_facts`. Only plain scalar orders enter that
collector, deliberately: importing the arithmetic siblings of a conjunction would let the solver
justify a range question with the very modular arithmetic it is deciding.

The collector read positive comparisons and nothing else. An early return leaves its condition
negated, so `return false if start > total` produced the fact `not (start > total)` and the
collector discarded it. The next statement could not subtract. The same guard written as
`requires start <= total`, or as a positive `if start <= total:`, worked. The previous entry
recorded that asymmetry as the remaining blocker without locating it.

### What changed

The collector now admits a negated comparison whose operands are the same atoms a positive one
would need. It pushes the negation unchanged: `proof_collect_bounds` and
`proof_collect_difference_constraints` already complement a negated comparison, and both run over
the collected orders downstream. `proof_kernel_replay_collect_unsigned_orders` is the mirror, with
the same atom test the positive path uses.

The negation of a comparison between two atoms is a comparison between the same two atoms, so this
imports no arithmetic and the collector's invariant is unchanged. What it does not do is read
through anything else: `not (a == b)` is an inequality and orders nothing, and a negated guard on
one pair says nothing about another pair or the other direction.

### The contract that was waiting on it

`proof_kernel_replay_child_range_valid` is written in exactly the two-guard shape that could not
carry a contract. It now states one:

    ensure not result or start <= total and count <= total - start

Both conjuncts are needed by a caller indexing `children[start + index]`. The sum rule bounds
`start + index` by `total` from `count <= total - start` together with `start <= total`, and the
guard on the subtraction is what makes the first meaningful for an unsigned type.

### Fixtures

`examples/negated_guard_order.elisa` carries the two-guard shape with its contract, the same shape
where the guard sits inside a disjunction, and the sum consequence a caller needs. The previous
commit's binary refuses the first six goals of the three and proves the last.

`examples/rejected_negated_guard_order.elisa` is the boundary: a negation of the wrong order, an
inequality where an order is needed, a guard naming another pair, and a strict bound the guards
give only non-strictly. All four are refused, with no semantic errors and no replay gaps.

### What it bought, and what it did not

On `examples/kernel_replay_standalone.elisa`: proven 1400 to 1403 against obligations 2094 to
2097, which is the new contract and its own proof. Verified functions stay at 111. All 1403
certificates replay, gaps stay 0 and `trusted_assumptions` stays empty.

The 26 `children[start + index]` findings did not close, and the reason has moved again. The
contract exists now and the rule that consumes it works, but the call sites read
`children[node.children_start + index]`. `node.children_start` is a field access, and both
`ProofAffine.base` and the order-atom test accept one bare identifier. Every term in this cluster
is a place expression, so the cluster is now blocked on exactly one thing: keying an affine base
and an order atom by a place path rather than a name. That is the affine rekey the audit has been
naming, and it is now the only step between this rule and these findings.

## Four readings of a fact list that were already stated in it

### What was wrong

The previous entry left the 26 `children[start + index]` findings blocked on one thing: the call
sites read `children[node.children_start + index]`, and `ProofAffine.base` and the order atom test
each accept one bare identifier. Widening those to a place key means threading a second component
through every bound, difference and matrix lookup in both engines. Measuring the cluster first
showed that is not what it needs.

The subtraction guard is the whole of it. `children.count - node.children_start` is range-safe
when a fact orders the pair, `start <= children.count` is exactly what such code writes, and the
guard is decided by `proof_difference_comparison`, which needs both sides affine. A structural
match needs neither: a collected order is a comparison between two atoms and contains no
arithmetic at all, so reading one directly imports nothing the guard would then be deciding about
itself. Only the atom test had to widen, and only to a place.

Three further readings were missing beside it, each of something the fact list already stated.

### What changed

**A field of a bare name is an order atom.** It is a place, not arithmetic: reading it twice in
one fact set reads the same value, because a field write clears the facts, and a call keeps only
what `proof_expr_call_stable` certifies. The peer rule already named exactly this shape. Field
places are inert for every existing collector -- `proof_ident_name` answers `""` for one and
`proof_affine_expression` declines it -- so they reach only the new structural match.

**A conjunction is read as its conjuncts.** The structural rules matched a top-level comparison,
so `requires a <= b and c <= d` was invisible where the same two facts written apart were not.
`proof_conjunct_facts` is a reading of the list, not an addition to it.

**A proposition beside its own negation is inconsistent.** This is arithmetic-free, so it is split
out of `proof_facts_inconsistent` and runs before the fixed-width guard, and the disjunctive case
split moves ahead of that guard with it. That ordering is the point: a callee's postcondition
arrives as `not result or p`, the caller has already guarded on the result, and the branch that
assumes `not result` must be able to close without its own facts being range-safe -- which they
are not, because `p` is where the guard for the subtraction in `p` lives. Every premise a tier
actually consumes still passes the guard, in the branch that consumes it.

**A non-wrapping unsigned expression is nonnegative.** Its mathematical value is its machine value
and an unsigned machine value is at least zero. The certification is the same guard every other
rule is gated on, so the rule reads an answer already computed. It is the lower bound on an index
whose upper bound was already proved, and it is deliberately not a strict one.

Each has its kernel mirror.

### Fixtures

`examples/place_order.elisa` carries all four and the call-summary shape they combine into: a
callee written as a two-guard range check, and a caller that guards on it and then indexes.
The previous commit's binary refuses every one.

`examples/rejected_place_order.elisa` is the boundary: a place order in the wrong direction, one
naming another pair, a disjunct read as a conjunct, a negation of one proposition offered against
another, a nonnegative value read as positive, and a summary whose guard the caller never
established. All six are refused, with no semantic errors and no replay gaps.

### What it bought, and what it did not

On `examples/kernel_replay_standalone.elisa`: proven 1403 to 1423 and verified functions 111 to
115, against obligations 2097 to 2124. All 1423 certificates replay, gaps stay 0 and
`trusted_assumptions` stays empty.

The index clusters are unchanged at 157 and 48, and the two probes that still fail say why. The
upper bound now proves for a caller that guards on the range check and indexes `start + index`,
so the rule reaches the shape. It does not reach these call sites, and two things stand between:
the guard there is written `return <call> if not child_range_valid(...)`, whose returned
expression is itself a call, and a local bound to a place carries `limit == children.count` as an
equality the structural rules do not rewrite through. The lower bound needs neither: it needs an
unsigned width marker for a field place, and markers are keyed by bare name.

## An unsigned field is nonnegative, and the type of a field was unsayable

### What was wrong

The lower bound on an index is `0 <= e`, and for an unsigned `e` it is true whatever the value
holds. The checker could not say it for `node.children_start + index`, because unsigned width
markers are keyed by a bare name and a field has none. The obvious repair -- report a width for a
field from the general width function -- is the one already measured and rejected: doing that for
`.count` cost 39 proofs, because every arithmetic term containing a field then fell under the
unsigned wrap guard.

Two things were missing, and neither is a width in the arithmetic sense.

### What changed

**A width marker over a place.** `proof_unsigned_place_marker` records the same
`__elisa_unsigned_type_bound` marker with a place as its first argument.
`proof_unsigned_marker_info` reads only the bare-name form, so a place width is invisible to
`proof_unsigned_width_in_expression` by construction and no arithmetic term inherits a wrap
obligation from it. `proof_term_is_unsigned` is the only reader: it answers whether a term has an
unsigned type at all, and one unsigned atom settles a whole arithmetic term, because arithmetic
mixing an unsigned operand with another type does not typecheck. That answer alone discharges
`0 <= e` -- no bound, no interval, no range argument, since the claim is about the machine value.
The rule is deliberately not strict: nonnegative is not positive.

**A qualified struct spelling resolves to its leaf.** `proof_type_head_name` had no `Scope` arm,
so a binding declared `Module::Type` got no field witnesses at all -- no scalar marker, no place
marker, nothing. The leaf is not assumed unique: every reader searches the declarations by it and
refuses a count other than one, so an ambiguous leaf loses the witness rather than picking a
struct. This is the same convention the proof tables already use for a qualified call.

Both have kernel mirrors for reading the marker.

### Fixtures

`examples/unsigned_place.elisa` carries the guarded range over a field indexed as
`children[node.children_start + index]`, which now verifies end to end, a bare field
nonnegativity, a field of a qualified struct type, and the case worth stating plainly: an
unguarded unsigned difference is still nonnegative, because that is a claim about the machine
value. The fact it yields is usable only where the subtraction is separately guarded, since the
range guard rejects an unguarded one before any rule may read it.

`examples/rejected_unsigned_place.elisa` is the boundary: a signed field, a strict goal, a call
result whose argument's marker does not travel through it, an upper bound the type argument does
not give, and an ambiguous qualified leaf.

### What it bought, and what the remaining index cluster actually needs

On `examples/kernel_replay_standalone.elisa`: proven 1423 to 1435 against obligations 2124 to
2138. All 1435 certificates replay, gaps stay 0 and `trusted_assumptions` stays empty.

The 17 `children[node.children_start + index]` findings are now understood completely, and they
are not a checker gap. The probe that reproduces the call site exactly -- guard, loop, index, a
call inside the loop body, and a mutable collection -- verifies. The corpus sites differ in one
respect: a call stands between the guard and the loop, and it receives the collection mutably. The
fact `node.children_start <= children.count` therefore cannot survive it, because a callee may
resize the collection, and the checker is right to drop it. Closing these needs the callee to
promise it does not shrink the collection, which in turn needs recursive function summaries --
`recursive-summary-unsupported` is the finding that names it.

## An empty literal is empty, and what it costs to say more

### What was wrong

The largest remaining finding bucket is parallel arrays: a loop bounded by one array's count
indexing another, where nothing relates the two lengths. The relation has to come from a loop
invariant, and a loop invariant has to be established before it can be preserved. It could not be
established at all. A binding declared `values: mutable darray[usize] = []` reaches a goal as
`[].count` after substitution -- the checker already knows the value -- and there was no rule that
reads a literal's own length.

### What changed

`proof_constant_int` reads the length of an empty collection literal, and
`proof_kernel_replay_constant_int` mirrors it over the arena's `array` node. This is the one length
statement that needs no model of the language's builtins and no aliasing argument: the term *is*
the value, so nothing can alias it, mutate it, or make its count something else.

### Why only the empty one

A non-empty literal carries its length just as plainly, and reading it needs that length as an
`i64`. The conversion is outside the expression fragment this checker verifies itself in. Writing
one in `proof_constant_int` was measured: `proof_kernel_replay_constant_int` became
`recursive-component-unverified`, 16 functions lost verification, `function-summary-unverified`
went 344 to 430, and the corpus fell from 1435 proven to 1370. The empty case needs no conversion,
and after narrowing to it the corpus is unchanged at 1435 proven and 115 verified functions, with
gaps still 0.

That measurement is worth keeping for its own sake: a rule added to `proof_constant_int` is a rule
added to the root of the arithmetic cone, and an unsupported expression there is not a local cost.

### Fixtures

`examples/literal_extent.elisa` carries the empty literal and a loop whose length invariant is
established from it. `examples/rejected_literal_extent.elisa` is the boundary: a length after a
push, a parameter that has no literal, a struct field that happens to be spelled `count`, an
element bound that a length does not give, and the non-empty literal whose length is true but not
read.

### What the parallel-array cluster still needs

Establishment is now possible; preservation is not. `a.push(x)` must yield `a.count == old + 1`,
and `b.count` must survive a call that does not receive `b`. The first is a statement about a
language builtin's effect and would be a new boundary fact kind, in the same category as the type
markers: taken as given, traced to its source, and recorded here. The second is the existing
call-stability question, and the framing that avoids a new aliasing axiom is that a callee cannot
change a binding it is not given -- which `proof_expr_call_stable` already encodes for by-value
scalars and could encode for a local collection's extent. Both are needed together; neither is
useful alone. After them the subject code still has to state the invariants, which is where the
`loop-invariant-missing` findings sit.

## A collection a local owns is a binding no callee can name

### What was wrong

A by-value scalar already survives a call: `proof_expr_call_stable` keeps it because a callee
reaches caller state through arguments, a method receiver and globals, and
`proof_collect_aliased_names` records every binding that is referenced, received, or handed to a
callee whose signature is not imported. A collection did not get the same treatment. Its extent
survived only as `.count` of a *shared-borrowed parameter*, so a local collection lost its length
across any call at all -- including a call that could not name it.

That is what a loop with a length invariant and a call in its body needs, and it is the half of the
parallel-array cluster that is not about a builtin's effect.

### What changed

**A local that owns its collection keeps its extent.** `report.local_extent_names` holds the
locals declared with a container type that is not a reference; the entry is rewritten on every
declaration of the spelling, so a redeclaration to a reference type withdraws it rather than
inheriting the earlier claim. `proof_expr_call_stable` admits `place.count` when the root is one of
those, is still a live binding, and is absent from `aliased_names` -- the same three conditions the
by-value scalar case checks, applied to the extent instead of the value. A reference-typed local is
excluded because the object behind one may be reachable by another path.

**A literal collection is call-stable as a value.** `[]` is a value, not storage: nothing a callee
can reach makes it hold something else. Without this the binding's recorded value was discarded at
the first call and the length was gone even where the fact survived.

The receiver of a method call is recorded as referenced by its own use, so the collection a `push`
is called on is excluded by exactly the rule that keeps the others. This is a producer-side
retention rule; the kernel replays the recorded facts and needs no mirror.

### Fixtures

`examples/owned_extent.elisa` keeps an owned extent across a call that cannot reach it and across
another collection being grown. `examples/rejected_owned_extent.elisa` is the boundary: a lent
local, a local bound to a reference, the receiver of a builtin whose effect is not modelled, and
the completeness boundary where a shared argument still loses the extent because the record of
reachable bindings does not separate a shared argument from a mutable one.

### What it bought, and what the cluster still needs

On `examples/kernel_replay_standalone.elisa`: unchanged at obligations 2138 and proven 1435, gaps
0, `trusted_assumptions` empty. The capability is a prerequisite rather than a closer, and the
corpus does not exercise it yet because the other half is missing.

That other half is the effect of the builtin itself: `a.push(x)` must yield
`a.count == before + 1`, and `a.clear()` must yield `a.count == 0`. Unlike everything above, that
is not a consequence of what a callee can reach -- it is a statement about what the language's
builtin does, and it would be a new boundary fact kind, admitted by `replay.elisa` without
derivation the way `type-bound` is. It should be taken deliberately and recorded here when it is,
not folded into a rule about reachability. After it, the subject code still has to state the
invariants that relate the arrays, which is where the `loop-invariant-missing` findings sit.

## A capture list is not evidence of a write

### What was wrong

`elisac-stage1` compiles a captured block whose body assigns an outer binding the capture list
omits, and the program observes the assignment. That measured fact is why the write-back set takes
everything the body assigns or references, and it is recorded in an earlier entry. The set also
contained the capture list itself, and that is a different claim: it treats a name appearing in the
list as a name the block may write.

It is not one. A block writes an outer binding by assigning it or by handing it to something that
can, and both of those are already in the body's own sets. A capture the body only reads was being
forgotten, so a precondition the loop never touched was gone after it -- `requires depth <= 127`
beside a captured loop that reads `depth` and writes nothing.

### What changed

The write-back set is still the body's assignment roots together with its aliased set, in full. A
capture is added to it unless the body neither assigns nor references it *and* it is a witnessed
scalar. The scalar condition keeps the conservative treatment for an owning value, which a capture
could move out of; a scalar is copied and cannot be.

This is a producer-side retention rule and needs no kernel mirror.

### Fixtures

`examples/captured_scalar.elisa` keeps a precondition across a captured loop that only reads the
binding, including one whose body calls something that mutates an unrelated collection. The
previous commit's binary refuses both.

`examples/rejected_captured_scalar.elisa` is the boundary: a capture the body assigns, a capture
handed to a callee that writes through it, and an outer binding the body assigns without capturing
it at all -- the case the measured compiler fact is about.

### What it bought, and the residue

On `examples/kernel_replay_standalone.elisa`: proven 1435 to 1439 against obligations 2138 to 2141,
and `call-requires-unproven` 17 to 16. Verified functions stay at 115. Gaps stay 0 and
`trusted_assumptions` stays empty.

Thirteen of the remaining sixteen are one goal, `depth + 1 <= 127`, inside
`proof_kernel_replay_goal_depth`, and the fact list at those goals still lacks both the function's
own `requires depth <= 127` and the negation its `return false if depth >= 127` leaves. Four probes
reproduce the surrounding shape -- a captured loop, an uncaptured one, a body that passes a
collection mutably, and a self-recursive call inside the loop -- and every one of them verifies.
Whatever drops the precondition there is not any of those, and this entry does not claim to have
found it. What is established is that the capture list was one cause, that it was measurably a
cause, and that it is no longer one.

## A `pass` is unreadable, and one of them was havocking a whole function

### What was found

Thirteen of the sixteen remaining `call-requires-unproven` findings were the same goal,
`depth + 1 <= 127`, inside `proof_kernel_replay_goal_depth`, and the fact list at each lacked that
function's own `requires depth <= 127`. Four probes reproduced the surrounding shape -- a captured
loop, an uncaptured one, a body passing a collection mutably, a self-recursive call inside the loop
-- and all of them verified, so the previous entry recorded the cause as unfound.

It is `pass`. The frontend parses `pass` to `Ast::Stmt.Expr(Ast::Expr.Invalid)`, and
`proof_expr_supported` refuses `Expr.Invalid`, which fails the obligation, sets `flow.valid` false,
and havocs the state for every statement after it in the body. One `pass`, in the default arm of
one `match`, was discarding the precondition for the whole rest of the function.

### Why the checker is not being changed to accept it

`Ast::Stmt.Expr(Ast::Expr.Invalid)` is produced at five places in the frontend. Four are
empty-body placeholders. The fifth is a recovery node for a keyword-shaped prefix form written
without a block, and for every spelling except `region` it records no parse error -- the comment
there says downstream walkers treat the expression as non-executable. At this AST layer a `pass`
and a construct the frontend dropped without complaint are the same statement, so admitting one
admits the other, and the checker would be verifying a function whose body it had not read. The
refusal is the safe side of that choice and it stays. The fix belongs in the frontend, as a
distinct statement node for `pass`.

### What changed

The one `match` in the kernel with a `pass` default had three arms doing the same thing, so it is
now the single condition it always was:

    reflexive: bool = operator == "==" or operator == "<=" or operator == ">="
    if reflexive:
        return true if ...definitionally_equal(...)

Behaviour-identical, and the kernel now contains no `pass` at all.

### Fixtures

`examples/no_op_statement.elisa` shows the two shapes that keep the state: a match whose arms agree
written as one condition, and a match whose every arm returns.
`examples/rejected_no_op_statement.elisa` pins the refusal itself and its reach -- a `pass` arm is
refused, and the precondition that held before the match is gone at a call below it. That fixture
exists so a future change to this behaviour is a deliberate one.

### What it bought

On `examples/kernel_replay_standalone.elisa`: proven 1439 to 1486 against obligations 2141 to
2173, and `call-requires-unproven` 16 to 3. Obligations rose because the region after the `match`
was previously havocked and produced none. `expression-unsupported` is 11 to 10; the remaining ten
are other constructs, in `proof_kernel_replay_replace_exact`, `..._congruence_class` and
`..._resource_events`, and each is worth the same treatment: find what the frontend cannot hand the
checker, and write the subject code inside the fragment instead.

All 1486 certificates replay, gaps stay 0 and `trusted_assumptions` stays empty.

## A call needs a statement boundary, and dead code was making obligations

### What was wrong

The previous entry closed one of eleven `expression-unsupported` findings and said the other ten
deserved the same treatment: find what the frontend cannot hand the checker, and write the subject
code inside the fragment instead. Six of the ten were one construct, all in
`proof_kernel_replay_replace_exact`.

A call that mutates through a reference is modelled at a statement boundary: the checker applies
the callee's summary or havocs what the call could reach, then continues. That machinery has one
shape to work with -- the call is the statement's value, or a declaration's initializer. A call
buried inside a larger value expression has no such boundary, so `proof_statement_value_supported`
refuses it, and the refusal havocs every statement after it in the body.
`return (true, ElisaProofKernelCore::add_node(...))` is exactly that shape, six times over.

### What changed

Each of the five remaining sites binds the call first and returns the binding. It is the same
program in the order it already ran, and it puts the call back where the checker can model it.

The sixth was in a second `if node.kind == "quantifier":` block that could never run: the block
above it returns on both of its paths. It is deleted. Dead code in a replay kernel is worth
removing on its own, and this one was also manufacturing obligations -- which is why the totals
below fall rather than rise.

### Fixtures

`examples/nested_call_value.elisa` shows the two shapes the checker models: the call as a whole
statement value, and the call bound to a local first, with the state after the binding intact.
`examples/rejected_nested_call_value.elisa` pins the refusal and its reach.

### What it bought

On `examples/kernel_replay_standalone.elisa`: `expression-unsupported` 10 to 4, and failed
obligations 687 to 681. Obligations fall 2173 to 2159 and proven 1486 to 1478 because the deleted
block is no longer generating either. `proof_kernel_replay_replace_exact` now carries no
unsupported statement at all and is blocked only by an unverified dependency. Gaps stay 0,
`trusted_assumptions` stays empty, and the report is byte-identical across runs.

Four remain, in `proof_kernel_replay_congruence_class` and `proof_kernel_replay_resource_events`.
The reported positions there do not land on the offending statement, so finding them needs the same
probe-and-compare the last two entries used rather than reading the line.

## The kernel is now inside the fragment that checks it

### What was wrong

Four `expression-unsupported` findings remained, in
`proof_kernel_replay_congruence_class` and `proof_kernel_replay_resource_events`. The reported
positions did not land on the offending statement, so the last entry said finding them needed the
probe-and-compare the two before it used. It did.

One was the same shape the previous entry closed: a call inside a returned tuple. The other three
are its sibling. A conditional expression's arms are not statements either, so a call in one has no
boundary for the checker to apply a summary or a havoc at:

    inherited_region: sview = binding_region(state, target_slot) if borrow_is_present else external
    places.push(source_place if alias else empty_place())

### What changed

Each call is bound before the expression that used it. Both helpers were checked first:
`proof_kernel_replay_resource_empty_place` is a constructor over no state, and
`proof_kernel_replay_resource_binding_region` is a bounds-checked read returning `""` outside the
table. Evaluating either unconditionally yields the value the guarded arm would have produced, so
the rewrites are equivalent, not merely equivalent-looking.

### What it bought

On `examples/kernel_replay_standalone.elisa`: `expression-unsupported` 4 to **0**, failed
obligations 681 to 676, and `region-expression-unsupported` 38 to 37. Obligations fall 2159 to 2154
with proven unchanged at 1478, because the havocked regions were producing obligations no rule
could ever discharge.

Every statement in the kernel replay module is now inside the fragment the checker verifies. That
is worth stating plainly: until this commit the checker could not read parts of its own kernel, and
each unreadable statement discarded every fact after it in that function's body. The gap between
what the module says and what the checker was able to read is closed.

### The fixtures

`examples/nested_call_value.elisa` now carries the conditional case beside the tuple case, and
`examples/rejected_nested_call_value.elisa` pins its refusal. Together with the `no_op_statement`
pair they record the whole boundary: a call is modelled where it is a statement's value or a
declaration's initializer, and nowhere else.

## A collection builtin writes its receiver, and until now nobody saw it

### What was wrong

`borrow-call-opaque` was the largest untouched bucket at 59, and the message says the callee has no
converged resource summary, which reads like the recursive-component limitation. It is not. Every
one of them is a call to a *collection builtin* -- `push`, `extend`, `clear`, `resize`, `pop` -- on
a place whose root is a reference. A builtin is not a declared function, so
`proof_resource_function_index` finds nothing, no summary exists, and the call falls to the branch
that reports it opaque.

Reporting it opaque fails an obligation, which is the safe-looking half. The unsafe half is that
the write those methods perform was never recorded at all. `examples/rejected_collection_builtin.elisa`
carries the consequence: a `push` made while a shared borrow of the same collection was live
**verified** under the previous commit. Nothing conflicted with the borrow, because nothing was
written as far as the resource state knew.

### What changed

A call whose callee is one of those methods on a place is recorded as what it is: a write to the
receiver, through `proof_resource_check_write`, the same path an assignment takes. The arguments
were already checked in the loop above, which is where their reads are recorded. Being an ordinary
write, it now answers to the ordinary rules -- an immutable reference, an overlapping live borrow
and a non-writable binding are all refused exactly as they are for `place <- value`.

This is an assumption about the language's builtins and is recorded here as one: these methods
mutate the receiver's storage, read what they are given, and move nothing. The last clause is not
a guess -- Elisa spells a transfer `move`, and an argument without one is not consumed.

The admission is withdrawn in three cases, so the model never answers a question it does not model:
a region-carrying argument, which is an escape question; a `move` argument, which is a transfer
into the collection; and a leaf name that *any* declaration carries. That last guard needs its own
counter, because `proof_resource_function_index` answers the same sentinel for "no such function"
and "two functions share this leaf", and a user method must never be mistaken for a builtin.

### What it bought

On `examples/kernel_replay_standalone.elisa`: `borrow-call-opaque` 59 to 28, failed obligations 676
to 644, verified functions 115 to 116, proven 1478 to 1480 against obligations 2154 to 2124 -- the
obligation count falls because a reported-opaque call is itself a failing obligation. Gaps stay 0
and `trusted_assumptions` stays empty.

### A gap this uncovered and did not close

When a declaration does carry the leaf name, the admission is withdrawn and the call takes the
summary path, where the receiver is not among the arguments and the mapping fails. If no argument
independently carries a resource, that path records nothing and reports nothing -- so a
method-shaped call on a place can still perform an unrecorded write, exactly as every builtin call
did before this commit. It predates this change and this change does not reach it. Closing it means
deciding what a method-shaped call means when its receiver is not a parameter of the callee, which
is the same question the resource summary format leaves open.

## Every method-shaped call now answers for its receiver

### What was wrong

The previous entry closed the builtin case and recorded the door it left open: when a declaration
carries the leaf name, the call takes the summary path, where the receiver is not among the
arguments and the mapping fails, and if no argument independently carries a resource, nothing is
recorded and nothing is reported. That is the same invisible write, reached differently.

The general statement is stronger than the case that prompted it. **The receiver of a method-shaped
call is never among the callee's arguments**, so no argument mapping can describe what the call
does to it. Either the effect is modelled by name or it is not modelled at all, and until now the
second case was silent.

### What changed

A call written as a method on a place is refused unless its receiver effect is accounted for. Three
outcomes, and no fourth:

- one of the collection builtins this model names -- `push`, `extend`, `clear`, `resize`, `pop` and
  now `truncate`, which was missing -- records a write to the receiver;
- a primitive width conversion records nothing, because it has no storage to write;
- anything else fails an obligation saying the receiver may be written and no summary maps a
  receiver.

The third outcome is what closes the hole. It also gives an unmodelled *builtin* the same
treatment: `values.sort()` is now refused rather than passed over, which is the honest answer for a
method whose effect this model does not name.

### Fixtures

`examples/collection_builtin.elisa` gains `truncate` and a width conversion.
`examples/rejected_collection_builtin.elisa` gains `values.sort()`, an unmodelled builtin, refused.
The fixture that matters most is still the one from the previous entry: a push made while a shared
borrow is live, which verified two commits ago.

### What it bought

On `examples/kernel_replay_standalone.elisa`: failed obligations 644 to 636, with
`region-call-opaque` 29 to 20 as `truncate` stops being opaque, and `borrow-call-opaque` 28 to 29
as the new refusal fires once. Proven stays at 1480 and verified functions at 116; obligations fall
2124 to 2116, because a reported-opaque call is itself an obligation. Gaps stay 0 and
`trusted_assumptions` stays empty.

The number to read here is not the proof count. It is that a method-shaped call can no longer pass
through this pass without either a model of its receiver or a refusal.

## A call in a loop condition, and two loops the compiler will not let carry an invariant

### What was wrong

`function-summary-unverified` stood at 341, which is not a cluster of its own: it is the cascade
from thirteen unverified roots. Reading the roots by finding count rather than by name shows most
of them owe two or three obligations, not dozens. Three looked closable.

`proof_kernel_replay_congruence_find` loops on `steps <= proof_kernel_replay_congruence_term_limit()`.
A call in a loop condition is the same shape as a call in any other larger expression -- there is
no statement boundary to apply a summary or a havoc at -- but the consequence is worse here: the
condition is reported opaque, and an opaque condition leaves the loop with no post-state claim at
all, so nothing after it holds either.

### What changed

The limit is bound before the loop. It is the same program: the callee is a constant of its
arguments, which is what a limit function is.

### The two that did not change, and why

`proof_kernel_replay_resource_lookup` and `proof_kernel_replay_resource_region_active` are the same
downward scan:

    index: mutable usize = state.binding_names.count
    while index > 0:
        index <- index - 1
        return index if state.binding_names[index] == name

Each owes one index bound and one `loop-invariant-missing`, and `invariant index <= ...count` is
exactly the missing fact. Adding it does not compile: `elisac-stage1` declined both bodies with
`(contract statement)`. Both loops carry a `return` inside them, which is the only feature they
share that the accepted invariant examples in `examples/` do not. The invariants are reverted and
the two roots stay open; closing them needs either that restriction lifted or the loops rewritten
to leave the return outside, which is subject-code surgery on a lookup in the resource kernel and
is not worth doing blind.

### Fixtures

`examples/bound_loop_condition.elisa` and its rejected pair are the same loop written both ways.
The bound one keeps its condition and reaches `contract-verified-widened-state`; the other is
`body-unverified` and carries `loop-condition-opaque` beside it. Neither proves outright -- both
still want an invariant -- which is why the fixtures assert on the finding sets and the
verification reasons rather than on a clean proof.

### What it bought

On `examples/kernel_replay_standalone.elisa`: failed obligations 636 to 629,
`function-summary-unverified` 341 to 334, `loop-condition-opaque` 2 to 1, and the unverified roots
8 to 7. Two functions move from failing to `contract-verified-widened-state`. Proven stays at 1480
and obligations fall 2116 to 2109, because an opaque condition is itself a failing obligation.
Gaps stay 0 and `trusted_assumptions` stays empty.

## The 35 region-expression findings are captured loops, and removing them exposes a real gap

### What they are

`region-expression-unsupported` stood at 37 and had resisted every static reading: the reported
positions land on `continue`, `return` and declaration lines, none of which is an expression
statement, and three rounds of instrumentation were needed to name the shape. Two of the 37 are
genuine assignment findings. The other 35 are all one thing: `Ast::Expr.Block`.

`for x in xs |captures|:` parses as a block, and in statement position that is
`Stmt.Expr(Expr.Block(...))`. The boundary rule asks whether a discarded expression statement
*contains* a region value, and `proof_resource_expr_contains_region_value`'s block arm answers by
scanning the block's statements. So the question being asked of every captured loop was "does any
statement in this loop body mention a region-owned binding", and the answer was reported as a
region value thrown away.

A block statement discards its own value and nothing else. For a loop that value is absent. The
body is ordinary statements, and it is already walked by `proof_resource_check_expression` on the
line above the test. The fix is one arm:

    Ast::Expr.Block(_, value, _, _):
        return proof_resource_expr_contains_region_value(value, state)

Measured: `region-expression-unsupported` 37 to 2, failed obligations 629 to 594, proven 1480 to
1484.

### Why it is not in this commit

It takes the replay gap count from 0 to 1.

Four functions gain a resource certificate under the fix. Three replay. The fourth,
`proof_kernel_replay_structural_report_impl`, produces a `resource-v1` trace of 31 events that ends
on three unclosed `resource-scope` events, and `proof_kernel_replay_resource_report_impl` refuses a
boundary with a scope still open. Its captured loop carries `return false if ...` inside the body,
and the resource walk stops at the early return without closing the scopes the loop opened.

The refusal was masking that. Removing the refusal is right; the trace is wrong either way, and it
was wrong before this was measured. Landing the fix first would ship a replay gap, which is the one
number this project does not trade, so the fix is held and the defect is recorded here instead.

### What closing it requires

The resource pass must close every scope a captured block opened when the block exits early, the
same way the proof pass models a `break` or `continue` transfer against the nearest loop's
invariant. Until then these 35 obligations stay refused for the wrong reason, and the count is a
placeholder for one scope-balancing defect rather than thirty-five region problems.

## Both halves of the region cluster, and the gap between them

### The finding, and why it took instrumentation

The previous entry named the 35 `region-expression-unsupported` findings as captured loops and held
the fix because it took replay gaps from 0 to 1. Both halves are here now, and the second half is
the more interesting one.

`for x in xs |captures|:` parses as a block, so in statement position it is an expression statement
whose expression is a block. The boundary that refuses a discarded region-owned value asked whether
that block *contains* one, and the block arm of that predicate answers by scanning the block's
statements. The question asked of every captured loop was therefore whether any statement in its
body mentions a region-owned binding. A block statement discards its own value and nothing else,
and for a loop that value is absent; the body is ordinary statements, walked as such before this
boundary is reached.

Three rounds of instrumentation were needed to learn that, because the reported positions land on
`continue`, `return` and declaration lines and no static reading of the source explained them.
Sixteen expression kinds were eliminated one build at a time before `Block` was named.

### The gap it uncovered

Four functions gain a resource certificate under that fix and three replay. The fourth was reduced
to a nine-line reproduction by bisection, and the difference is one argument:

    Core::fits(node.children_start, node.children_count, children.count)

where `children` is a `mutable darray& @r` parameter. Binding `children.count` to a local first
removes the gap; so does dropping the region annotation. `proof_resource_expr_carries_resource`
answers for a place by walking to its root binding and asking whether that binding is a reference,
so `children.count` was read as carrying the collection. The call then recorded a transition naming
the collection as an actual, and the kernel refused it, because the callee's formal is a by-value
scalar and no region maps.

The element count of a collection is a scalar copy. Passing one hands the callee no capability over
the collection. `proof_resource_expr_contains_region_value` already reads `x.count` that way -- its
first line is exactly this test -- and `proof_resource_expr_carries_resource` now does too.

The refusal had been hiding this since before it was measured: the trace was wrong either way, and
only removing the block misreading made it reachable.

### Fixtures

`examples/block_statement_region.elisa` carries a captured loop over a region-owned binding and an
extent passed to a callee from a region-annotated function. The previous commit's binary refuses
the first. `examples/rejected_block_statement_region.elisa` keeps the boundary honest: a region
binding as a bare expression statement is still a value thrown away, and parenthesising it changes
nothing.

### What it bought

On `examples/kernel_replay_standalone.elisa`: `region-expression-unsupported` 37 to 2, failed
obligations 629 to 594, proven 1480 to 1484, against obligations 2109 to 2078. All 1484
certificates replay, gaps are 0, and `trusted_assumptions` stays empty.

## A loop invariant cannot be written here at all, so two loops are written not to need one

### Correcting the previous entry

Two entries ago the audit recorded that `invariant index <= ...count` on
`proof_kernel_replay_resource_lookup` and `proof_kernel_replay_resource_region_active` made
`elisac-stage1` decline both bodies, and guessed the cause was the `return` inside the loop, since
that was the only feature those loops did not share with the accepted invariant examples.

That guess was wrong, and the corrected fact is stronger. Compiling five minimal cases directly
shows `elisac-stage1` declines any function body carrying a loop `invariant` -- `while` or `for`,
with a capture list or without, with a `return` in the body or without. A function-level `requires`
compiles. So a loop invariant cannot appear in any compiled source of this project, and every
`loop-invariant-missing` finding in the kernel names a fact that cannot be stated where it is
needed.

One detail explains how the wrong guess survived a compile, and is worth recording so the next
reading does not repeat it. The backend declines the *body*; it reports that only when something
still references it:

    error: backend could not produce a linkable unit; declined 1: scan@4 (contract statement)
    note: emitted functions still reference declined bodies; the object was not written

A function nothing calls is dropped without a word and the command exits 0. So a probe that adds an
invariant to an unused function measures nothing. Only the loop clause is refused: a header
`requires` and `ensure` compile, and so does an `assert` statement in the body.

### What changed

Both loops are downward scans whose index bound is exactly what an invariant would have supplied.
Written forward over `0..<count`, the bound comes from the loop range instead:

    found: mutable usize = names.count
    for index in 0..<names.count:
        found <- index if names[index] == wanted
    return found

Keeping the last match returns the slot the downward scan returned -- the highest matching index,
which is the innermost binding under shadowing -- so the answer is unchanged. The existence check
does not depend on order at all. What both give up is the early exit; the tables they scan are a
function's bindings and a frame's active regions, which are tens of entries.

### Fixtures

`examples/forward_scan.elisa` carries both rewrites. `examples/rejected_forward_scan.elisa` carries
the shape that cannot be written, and keeps both of its findings: the invariant it has no way to
state, and the index bound that invariant would have given it. That fixture is the record of the
constraint, not a wish for the loop to verify.

### What it bought

On `examples/kernel_replay_standalone.elisa`: verified functions 116 to 120, unverified roots 7 to
5, `function-summary-unverified` 334 to 290, `loop-invariant-missing` 11 to 9, `index-upper` 158 to
156, and failed obligations 594 to 548 against obligations 2078 to 2040. Proven rises 1484 to 1492.

Two loops of five lines each cascaded into forty-four fewer summary findings, which is what the
root-count reading predicted: the summary bucket is not a cluster to attack directly but the shadow
of a small number of roots.

## An extent may be nested, and an element write beside it changes nothing

### What was wrong

A loop range is a fact about a length, and the rule that keeps such a fact across a loop entry
required the length's base to be a bare name. `state.region.count` is not: its base is a field. So
a loop written `for index in 0..<state.region.count` whose body wrote `state.live[index]` lost its
own range fact and could not index the collection it was iterating.

The root was in the written set, correctly -- the body does write under `state`, and the values
recorded in terms of `state` must be resymbolized. What does not follow is that the *lengths* under
it changed. An element write is an element write whichever collection it lands in, and a write to a
whole field puts the root in the disqualified set instead, where it already loses every count
beneath it.

### What changed

The base of a `.count` in the extent-stability test is now the place root rather than a bare name,
so every collection under an element-only-written root keeps its extent. Every existing guard is
untouched: a whole write, a reference taken, a call in the body, and a binding this frame aliased
elsewhere all disqualify the root exactly as before, which is what
`examples/rejected_loop_element_extent.elisa` has always pinned and still refuses in all six of its
cases.

### Fixtures

`examples/nested_extent.elisa` iterates one field's length while writing another field's elements,
with the guard written both before and inside the branch.
`examples/rejected_nested_extent.elisa` replaces a whole field inside the loop and loses the range
fact for the field it is iterating, which is the correct answer: that write can replace the
collection.

### What it bought

On `examples/kernel_replay_standalone.elisa`: verified functions 120 to 121, unverified roots 5 to
4, `index-upper` 156 to 154, and failed obligations 548 to 545. Proven rises 1492 to 1494 against
obligations 2040 to 2039. Gaps stay 0 and `trusted_assumptions` stays empty.

This is a small number for a shape that is everywhere in the resource kernel, and the reason is
worth stating: most of those loops also call something, and a call in the body disqualifies the
root before this rule is reached. The nested base was the second lock on that door, not the first.

## A field of a binding this frame owns

### What was wrong

A call reaches caller state through arguments, a method receiver and globals, and the checker keeps
a by-value scalar across one because a callee has no path to a binding it was not given. That
argument was never applied to a field. The rule returned false for any field but `.count`, and
admitted that one only for a parameter bound by a shared borrow, so a fact about
`node.children_start` was discarded at the first call in the body whatever the call was.

A callee that cannot reach `node` cannot reach `node.children_start` either.

### What changed

The set that recorded "a local that owns its collection" now records any binding that holds its
value rather than a reference to one -- parameters as well as locals, and no longer only container
types. A field of such a binding is call-stable when the binding is not aliased, is still live, and
the place carries a scalar-term witness, which are the same three conditions the by-value scalar
case checks. The shared-borrow `.count` path is unchanged beside it.

### What was tried and removed

A call term in a fact is never call-stable, which is what keeps a callee's summary --
`not f(...) or p` -- from surviving the next call in the body. A pure-call witness certifies that a
call denotes one value over witnessed arguments, and admitting a call term on that evidence is
sound. It is also inert: those witnesses are recorded for calls in a *goal*, and a summary's call
term lives in a *fact*, which never receives one. The arm was written, measured at zero, and
removed rather than left in a security-critical path as unreachable code. Closing that case needs
the witness recorded where the fact is built, which is a different change from this one.

### Fixtures

`examples/value_root_field.elisa` keeps two fields of a by-value parameter across a call that
grows an unrelated collection. `examples/rejected_value_root_field.elisa` refuses the same shape
for a mutable reference and for a shared one: the rule is about what this frame owns, not about the
borrow discipline.

### What it bought

On `examples/kernel_replay_standalone.elisa`: proven 1494 to 1495, `index-upper` 154 to 153, failed
obligations 545 to 544. Gaps stay 0 and `trusted_assumptions` stays empty. Every adversarial fixture
that pins call stability -- the call boundary, the owned extent, the captured scalar, the loop
element extent -- refuses exactly what it refused before.

One obligation is a small return for the reach of the rule, and the reason is the same one the
removed arm names: at most of these sites the fact that would have survived mentions the call whose
summary it is, and that term is still discarded.

## Where a callee's summary is lost, measured rather than argued

### The question

The previous entry recorded that a callee summary applied to an unbound call reads
`not f(...) or p`, that the call term is never call-stable, and that this is what discards the
summary at the next call in the body. It named the fix as recording the pure-call witness where the
fact is built rather than only where a goal is decided. That fix was written and measured.

### What was measured

Two changes together: the witness recorded beside the summary fact in `proof_apply_function`, and a
call arm in `proof_expr_call_stable` admitting a witnessed call term whose arguments are themselves
stable. Built, run on the corpus, and compared against the commit before it:

| | before | after |
| --- | --- | --- |
| proven | 1495 | 1495 |
| failed obligations | 544 | 544 |
| every finding bucket | unchanged | unchanged |

Zero. Both are reverted. Neither is left in the tree, for the same reason the previous inert arm was
removed: unreachable code in a security-critical path is a liability, and a rule with no fixture
that can exercise it is not a rule this project keeps.

### What the measurement established

The fact does reach the caller's state -- a probe with the guard and no intervening call carries
`not range_valid(...) or (...)` and proves its index bound. After an intervening call the fact is
gone and no witness for the call term is present in its place, so the site that built it is not the
one the witness was added to. `proof_apply_function` has ten call sites; the one that carries an
unbound call's summary into the real fact list is not the site at its end that this change
instrumented, and this entry does not claim to know which of the ten it is.

What is now established, and was not before, is that the missing piece is a *provenance* question
rather than a rule: the summary fact and its witness must be built together, wherever that is. The
by-value field rule committed beside this one is what makes that worth finding -- the field markers
in that probe now survive the call, so the summary is the only thing still lost.

### What survived

The measurement itself is the product here. A probe that isolates the shape, a corpus comparison
that shows zero, and a reverted diff are a better record than a plausible rule with no evidence, and
the next attempt starts from a narrower question than this one did.

## The summary-provenance question, narrowed twice more

### What the previous entry left open

It said the summary fact reaches the caller's state, is lost at the next call because its call term
carries no witness, and that `proof_apply_function` has ten call sites of which it did not know
which builds that fact. Two of those are now answered and a third is not.

### The site is found

`proof_check_frame_calls_in_expression`'s call arm applies the summary into a probe list and then
does `facts.clear(); facts.extend(probe_facts) if applied`. That is the path a call in a branch
condition takes, and it is where `return x if not f(...)` gets its summary. The witness was added
there, and then moved after the type-bound and call-stable restores in case the arguments were not
yet witnessed when it first ran.

Neither position changes anything. The corpus is identical: proven 1495, failed 544, every bucket
unchanged. The witness is still not recorded.

### Why, narrowed to one condition

Four probes over the same shape:

| callee | argument shape | witness recorded |
| --- | --- | --- |
| no contract | scalars | yes |
| no contract | a struct field | yes |
| carries an `ensure` | scalars | **no** |

So place arguments are not the obstacle and the recording site is not the obstacle. A callee that
carries an `ensure` is not classified as a pure call, and a callee whose summary we want to keep
always carries one. The two mechanisms exclude each other by construction, which is why every
attempt so far has measured zero.

Where it is *not*: `proof_function_is_directly_pure` refuses a function with `requires`, `changes`
or `preserves`, and `ensure` is not among those; `proof_pure_body_direct` admits an `ensure`
contract statement whose expression has no call and no `old`. Both of those admit the probe's
callee. The exclusion is somewhere else in the purity fixed point and this entry does not claim to
have found it.

### Why nothing is committed

Two positions of one addition, both measured at zero, both reverted. What is committed is the
question, which has gone from "why is the summary lost" to "which step of the purity fixed point
excludes a callee that carries an `ensure`", and a probe file shape that answers it in seconds
rather than in a twenty-five minute corpus run.

## Correcting two claims about the summary-provenance question

The previous entry drew two conclusions from a four-row probe. A wider probe contradicts both, and
the record should say so plainly rather than leave them standing.

### `ensure` is not the discriminator

The claim was that a callee carrying an `ensure` is never classified as a pure call, and that this
excludes exactly the callees whose summaries matter. Measured over six callee shapes:

| callee | pure-call witness recorded |
| --- | --- |
| no contract | yes |
| `ensure true` | yes |
| `ensure not result or a <= b`, two-guard body | yes |
| `ensure not result or a <= b and ...`, three-guard body | yes |
| `requires a <= b` with `ensure result` | no |
| a callee that is itself `body-unverified` | no |

The third and fourth rows are the exact shape of `proof_kernel_replay_child_range_valid`, and they
are witnessed. The discriminator in the fifth row is the `requires`, which is what
`proof_function_is_directly_pure` refuses in its first line, alongside `changes` and `preserves`.
The earlier entry quoted that line and then reasoned past it. The sixth row is the ordinary
`verified` requirement.

So the mechanisms do *not* exclude each other by construction, and the callee this cluster needs is
eligible for a witness.

### The site is not settled either

The previous entry located the fact's construction at
`proof_check_frame_calls_in_expression`'s call arm, on the strength of that arm extending the real
facts from a probe list. If that were the site, adding the witness there would have recorded one for
a callee the table above says is eligible. It recorded nothing, in either of the two positions
tried. That is evidence against the identification, not for it.

What stands is narrower than either entry claimed: the fact reaches the caller's state, it is lost
at the next call, the callee is eligible for a pure-call witness, and the place that builds the fact
is still unidentified among `proof_apply_function`'s ten call sites.

### Why this is worth a commit of its own

Two entries asserted a cause on evidence that did not support it. The corpus numbers in them are
sound -- both changes measured zero and both were reverted -- but the explanations were not, and an
audit whose explanations drift is worth less than one that records only what it measured. The probe
files that produce the table above run in seconds; the next attempt should start by widening the
matrix rather than by reasoning from three rows.

## The summary-provenance question, answered: a shared borrow keeps its extent through a loop

### What the last three entries were chasing

Three entries asked why a callee's summary -- `not f(...) or p`, the fact that carries a range
guard -- does not survive to the loop that needs it. Each looked at the call boundary, added a
witness there, measured zero, and reverted. The corpus numbers were sound and the explanations
were not, which the last entry said plainly.

The cause is not at the call boundary. Six probes over one shape, each running in seconds:

| intervening statement | guard survives |
| --- | --- |
| none | yes |
| a call to a contract-less callee | yes |
| a call to a callee with an `ensure` | yes |
| a call taking an unrelated collection | yes |
| a call taking a *scalar* read off the guarded collection | yes |
| a call taking the guarded collection itself | **no** |

Only the last row fails, and what distinguishes it is not the call: it is that lending the
collection anywhere in the frame puts its name in `report.aliased_names`, and
`proof_forget_loop_entry` merges that whole set into the names it resymbolizes at loop entry. The
guard was purged by the *loop*, not by the call. Every earlier probe had a loop in it, which is why
the call boundary looked like the site.

### What changed

Two things, both narrow.

`proof_forget_loop_entry` now adds the frame's shared-borrow parameters to its extent-safe set. A
shared borrow cannot be written through for its lifetime, and the compiler's borrow rule means no
mutable path to the same object coexists with it, so no statement of the loop body -- element
write, whole assignment or call -- can change `name.count` for a parameter bound by one. This is
the claim `proof_expr_call_stable` already makes for the same parameters, applied to an iteration
instead of to a call. The set is already emptied for a program that declares a mutable global,
which is the one way a callee could reach the object by another path, and the spelling must still
denote that parameter, so a local that shadows it is excluded.

`proof_expr_extent_stable` gained a call arm, and the entry facts are threaded in as its witness
set. A call term denotes one value when a pure-call witness says the callee is verified, total and
pure over witnessed arguments; if every argument is extent-stable across an iteration, so is the
call. Without this the guard itself -- a call -- could never be restored even once its arguments
were known to be stable.

The call-stability rule gained the matching call arm at the same time, so a guard also survives an
intervening call once its extent is known: a scalar-term marker is worth what its subject term is
worth, and an ordinary call term is stable when it is witnessed and its arguments are stable.

### Fixtures

`examples/shared_extent_loop.elisa`: the collection is lent to a callee before the loop, after the
loop, and inside the loop body on every iteration. All three keep the guard.
`examples/rejected_shared_extent_loop.elisa`: a mutable borrow a callee empties on each iteration,
a mutable borrow lent before the loop, and a scalar argument of the guard that the loop rewrites.
All three lose it, which is the correct answer in each case.

### What it bought

On `examples/kernel_replay_standalone.elisa`, measured against the same corpus before and after:

| | before | after |
| --- | --- | --- |
| obligations | 2039 | 2039 |
| proven | 1495 | 1501 |
| findings | 554 | 548 |
| `index-upper-unproven` | 153 | 147 |
| replay gaps | 0 | 0 |
| verified functions | 121 | 121 |

Every other finding bucket is unchanged, `trusted_assumptions` stays empty, and no function that
verified before stopped verifying. Six index obligations is a small number for a question three
entries went after; what the change is worth is that the question is now answered rather than
narrowed, and the answer is a rule with a stated justification rather than a witness moved around
until something moved.

## A proven goal the kernel refused for want of an equality

### What was wrong

A local bound to a collection literal has that literal as its recorded value, so every fact the
body takes over `name.count` is recorded over `[...].count` instead. The replay driver finds each
certificate fact's origin by comparing it against the recorded trace with
`proof_replay_expr_equal`, and that comparison had no arm for a collection literal: it fell to the
wildcard and returned false. A fact could not match *its own trace*. Its origin came back unknown,
and the certificate carrying it could not be replayed.

The producer had proved the goal. The kernel refused it because two identical expressions did not
compare equal, not because anything was unjustified. So this was a completeness hole rather than an
unsound one -- the refusal is the safe direction -- but it is a gap, and gaps are what the whole
replay path exists to keep at zero.

The shape that hits it is ordinary:

```
def f(start: usize) -> usize:
    children: mutable darray[usize] = [1, 2, 3]
    return 0 if not range_valid(start, 1, children.count)
    return children[start]
```

Five certificates in a four-function file gapped. A local bound from a *call* instead of a literal
replayed cleanly, which is what isolated the cause: the call arm existed and the array arm did not.

### What changed

`proof_replay_expr_equal` gained arms for `Array`, `CharLit` and `StringLit`. The array arm is
elementwise and exact -- same length, same elements, compared with the same recursion the tuple arm
above it uses -- so it distinguishes `[1, 2, 3]` from `[4, 5, 6]` and from `[4, 5]`. Adding an arm
to this comparison can only make it more precise: every form it does not name still returns false.

### Fixtures

`examples/replay_literal_facts.elisa`: a guard over a literal-bound local, two literals of
different lengths in one frame, and two of the same length with different elements. Twelve
certificates, all replayed; the same file gaps five before the change.
`examples/rejected_replay_literal_facts.elisa`: the binding rebound to a different literal after
the guard, a guard for one literal with a different literal indexed, and an empty literal indexed
at all. All three stay unverified, and all nine certificates replay; the same file gaps two before
the change.

### What it did not buy

Nothing on the corpus: `examples/kernel_replay_standalone.elisa` has no local bound to a collection
literal under a guard, so its numbers are identical either way, gaps included. The measurement that
matters here is the fixture pair -- seven gaps closed, none opened -- and the reason to record it
is that a user writing three lines of ordinary code hit a gap the corpus never would.

## Nonnegativity does not need a wrap proof

### What was wrong

`0 <= x` was the most-refused obligation in the corpus after the index upper bounds: 38 of the 47
open `index-lower` findings were of that exact shape over a subtraction-free unsigned term. Two
separate mechanisms refused them.

The first is the rule itself. `proof_unsigned_nonnegative_goal` required
`proof_unsigned_expression_safe`, a proof that the term cannot wrap, before it would conclude the
term is nonnegative. That premise belongs to a subtraction and to nothing else. Every leaf of an
arithmetic term that one unsigned atom settles is itself unsigned -- arithmetic between an unsigned
operand and anything else does not typecheck -- so every leaf is nonnegative, and addition,
multiplication, division, remainder and the shifts all carry nonnegativity forward. `start + index`
is nonnegative whether or not it wrapped: its machine value is an unsigned value, and its
mathematical value is a sum of nonnegative numbers. Only subtraction has a mathematical value that
can be negative while its unsigned machine value is not, which is exactly the case the guard exists
for.

The second is placement. `proof_goal_depth` refuses a goal, and refuses every *premise*, that is
not wrap-safe, before any rule runs. That guard is right for the tiers below it, which read terms
as mathematical values. But a body that guards an index writes the guard over the same sum the
index uses, so the premise the goal needs is the premise the guard rejects, and the nonnegativity
rule was unreachable in exactly the bodies that needed it. A four-line probe shows it: with the
guard written as `return 0 if start + index >= values.count`, the lower bound on `start + index`
was refused, and with the same guard written in the difference form the engine does support it was
refused just the same, because a *premise* now named the subtraction.

Third, and smaller: a width witness whose subject is a place -- `node.children_start` rather than a
bare name -- was invisible to the retention rule, because the marker reader it goes through is
deliberately bare-name-only so that a term containing a field never falls under the wrap guard.
Retention is a different question from width, and the place form has to be recognized there: the
witness depends on its subject's root binding, exactly as the scalar-type witness beside it does.
So the width witness was discarded at the first call while the scalar witness survived, and a place
stopped being unsigned for the rest of the body.

### What changed

`proof_expr_subtraction_free` names the forms that carry nonnegativity: a nonnegative literal, a
name, a place, a loop binder, and the six arithmetic operators other than subtraction. Anything it
does not name counts as containing a subtraction.

`proof_unsigned_nonnegative_goal` concludes without the wrap premise for such a term, and
`proof_unsigned_nonnegative_shape` addresses the same rule by the whole goal so it can be tried
before the wrap guards rather than behind them. `proof_unsigned_place_marker_info` reads the place
form of the width marker, and `proof_type_marker_root_name` uses it, so retention follows the
place's root. Each has a kernel mirror: `proof_kernel_replay_subtraction_free` and
`proof_kernel_replay_unsigned_nonnegative_shape`, placed at the matching point before the kernel's
own premise and goal guards.

### Fixtures

`examples/unsigned_nonnegative_sum.elisa`: the bare claim over two unbounded unsigned terms, the
same over a product and a shift, the claim under a guard, a struct field as the leaf, and a place
whose width witness has to survive a call. The baseline refuses three of the six.
`examples/rejected_unsigned_nonnegative_sum.elisa`: a signed sum, an unguarded unsigned difference,
a difference nested under an addition, a strict `0 < x`, a bound `x < 10` over a sum that may wrap,
and that same sum used as an index. All six stay refused, which is the point: the relaxation admits
one claim about one shape and nothing else about the same term.

### What it bought

On `examples/kernel_replay_standalone.elisa`:

| | before | after |
| --- | --- | --- |
| obligations | 2039 | 2047 |
| proven | 1501 | 1522 |
| findings | 548 | 535 |
| `index-lower-unproven` | 47 | 28 |
| replay gaps | 0 | 0 |
| verified functions | 121 | 121 |

Obligations rise by eight because a body that gets past its index obligations reaches statements
whose obligations were never posed before; `function-summary-unverified` and
`recursive-summary-unsupported` account for the whole of that. `index-upper-unproven` is unchanged
at 147, `trusted_assumptions` stays empty, and no function that verified before stopped verifying.

## A guard reaches the code after it negated, and nothing could read it

### What was wrong

`return 0 if start > values.count` is how a guard is written in this language, and the statements
after it see `not (start > values.count)`. Every rule built on the order query read only the
positive spelling. The affine tiers do normalize a negation, but they name one bare identifier, so
an order stated between a place and a name -- `start <= values.count`, the premise every range
check turns on -- was stated and unreadable.

The measurement is a three-function probe. The same range check, written three ways:

| spelling | verified |
| --- | --- |
| `return values[start + index] if start <= values.count and index < values.count - start` | yes |
| `return 0 if not (start <= values.count)` … | yes |
| `return 0 if start > values.count` … | **no** |

The second row passes because a double negation is folded away before the facts are recorded. The
third is the ordinary form, and it was the one that failed.

### What changed

`proof_readable_order` returns the order a fact states, seeing through one negation, and
`proof_has_order_fact` and `proof_sum_witness_for` read their facts through it. Reading
`not (x > n)` as `x <= n` is the totality of the primitive order, so both operands must carry a
primitive scalar witness; a positive fact needs none, since it is used as itself with no inference
over its operator. The subtraction-safety tier already carried the bare-name type markers alongside
its collected orders so that gate could be answered there; it now carries the place-form markers
too, or the witness could not be established for `values.count`.

`proof_kernel_replay_readable_order` mirrors it, and the kernel's own subtraction-safety tier
carries the markers the same way. Both halves were needed: with only the producer half the fixture
proved and gapped, which is the kernel doing its job.

Complementarity is available even for a struct, and the fixture says so rather than assuming
otherwise: the compiler derives all four ordering operators from a single
`__cmp__(self, other) -> i64` compared against zero, so `not (p > q)` and `p <= q` are the same
predicate over the same call. The witness requirement is therefore stricter than the language
demands, which is the safe direction and costs nothing measured. What a negation does not give is
transitivity, and two negated struct steps still compose to nothing.

### Fixtures

`examples/negated_guard_range.elisa`: the difference-form range check written with early returns,
the same check written as an `if` condition so the two spellings must agree, and a guard over a
struct field on both sides. The baseline proves one of the three.
`examples/rejected_negated_guard_range.elisa`: two negated struct orders chained, the modular form
`start + index >= values.count` whose negation bounds nothing about a sum that may have wrapped,
and a negated equality, which is not an order at all. All four stay refused.

### What it bought

On `examples/kernel_replay_standalone.elisa`: proven 1522 to 1524, obligations 2047 to 2053,
verified functions 121 to 122, gaps 0, `trusted_assumptions` empty, nothing lost. The one function
that newly verifies is the helper this change adds, and `index-upper-unproven` is unchanged at 147.

That is a corpus effect of approximately zero, and it is worth saying why this was kept when two
earlier zero-measuring changes were reverted. Those were hypotheses about a corpus cluster: the
measurement was the test of the hypothesis, and zero meant the hypothesis was wrong. This is not a
hypothesis about the corpus. It is a capability the fixture demonstrates directly -- the commonest
guard form in the language, unreadable before and readable after -- and the corpus reads zero only
because the kernel happens to write its own range checks the other way.

## A lend that ends with its call is not an alias afterwards

### What was wrong

`proof_collect_aliased_names` records a binding as aliased the moment anything in the frame lends
it, and never withdraws that. Loop entry then merges the whole frame's aliased set into the names it
resymbolizes, on the argument that a reference held in another binding may still reach it. So a
collection lent once, anywhere in the body, lost its extent at every loop afterwards -- and with it
the loop's own range fact, which is the premise every index into that collection needs.

The argument is right only when the lend can outlive the call it was passed to.

### Where the boundary actually is

Three probes compiled against `elisac-stage1`, not an argument about the language:

| callee | lend escapes |
| --- | --- |
| second parameter `mutable darray[darray[usize]&]&`, `sink.push(values)` | **yes**, accepted |
| by-value return `darray[darray[usize]&]` holding it | **yes**, accepted |
| plain struct field assignment | no, refused by the region checker |

So "returns no reference" is not enough, and neither is "has exactly one reference parameter". What
decides it is whether any place the callee can store into, that its caller still sees, has a type
able to hold a reference: its other parameters' storage, and its return.

### What changed

`proof_type_is_reference_free` answers that over declared types -- primitives, `sview`, a const
enum, a tuple, a `darray`/`view`/`set`/`array` element, and a struct all of whose fields answer the
same -- and is conservative everywhere else: an unresolvable name, an ambiguous alias, a form it does
not recognize, and a type too deep all count as able to hold a reference. The function table records
it per parameter, over the type with an outer reference stripped, because what matters is the
storage the parameter names rather than the reference to it.

`proof_call_lend_is_confined` reads that, and refuses outright a callee that declares a lifetime
parameter, returns a reference, or returns a region -- the three ways a callee names something
longer-lived than its own call. The rule is withdrawn from a program that declares a mutable global,
since that is a place a callee reaches without being handed anything.

The result goes into a *second* set, `report.escaping_names`, and only loop entry reads it.
`aliased_names` is unchanged and every call-site rule still reads that one, because a confined lend
is still a write during its own call. Getting this wrong is not theoretical: an earlier attempt
narrowed the call-site rules too, and the fixture immediately showed a binding keeping the value it
had before the call that appended to it.

### Fixtures

`examples/confined_lend_extent.elisa`: a lend before a loop, a shared lend, and two bindings lent to
the same callee. The baseline loses four index bounds across them; all three functions verify now.
`examples/rejected_confined_lend_extent.elisa`: the two escapes above, a lend inside the loop body,
and a fact taken before a confined lend that must not survive the call it was taken before. All four
stay refused.

### What it bought

On `examples/kernel_replay_standalone.elisa`: nothing at all. Obligations 2053, proven 1524,
findings 539, gaps 0, verified 122 -- every number identical before and after, and no bucket moved.

The reason is worth recording, because it names the next piece of work rather than excusing this
one. Loop entry is only half of where the aliased set is read. The other half is call stability: a
fact over the binding still dies at the next call *inside* the loop body, because
`proof_clear_facts_after_call` reads `aliased_names`, and it must, since the lending call itself is
one of the calls it has to account for. Narrowing that safely means telling each clearing site which
expression's call it follows, so the lends of *that* statement can be blocked while the rest are not.
Until that is done the kernel's loops, whose bodies all call something, keep losing the fact at the
call rather than at the loop head -- which is exactly what the corpus is reporting by not moving.

## The other half of the aliasing question, built and measured at zero

The previous entry named the missing half and said what it would take: tell each fact-clearing site
which expression's call it follows, so the lends of *that* statement can be blocked while the rest
are not. That was built and reverted. This records the measurement and, more usefully, where the
probes say the remaining obstacle actually is, because it is not where the previous entry guessed.

### What was built

`proof_statement_lend_roots` returns the roots one expression lends.
`proof_clear_facts_after_call` and `proof_forget_values_after_call` take that set and block
`escaping_names` together with it, instead of the whole frame's aliased set. All twenty-seven call
sites pass the expression whose call they follow; the five that cannot name one -- a catch's error
path, an unsupported expression, a compound assignment, and the two branch joins -- pass the full
aliased set, which makes the union the old behaviour exactly.

### What it measured

Nothing, anywhere. On `examples/kernel_replay_standalone.elisa`: obligations 2053, proven 1524,
findings 539, gaps 0, verified 122, every bucket identical. On six hand-written probes covering a
loop over a local collection, over a by-value parameter, and over a shared borrow, with and without
a lend in the body: every function that verified with the change verified without it.

That last measurement is the one that matters, and it corrects an attribution made while the work
was in progress. A probe that improved was compared against a build predating the previous commit,
so the improvement belonged to that commit and not to this one. Rebuilding at the committed state
and re-running the same probes is what settled it.

### Where the obstacle is instead

Probes narrow it to one shape, and it is not the aliasing set at all:

| collection | lend in the loop body | verified |
| --- | --- | --- |
| shared-borrow parameter | yes | yes |
| by-value parameter | yes | yes |
| local, filled by `fill(&names)` | yes | **no** |
| local, from a call returning it | yes | **no** |
| local | no | yes |

The loop-range fact survives an in-body call for a parameter and not for a local, and relaxing the
call-stability rule for a `.count` place makes only the lent-local row pass. So a local collection's
extent is not call-stable for a reason that is *not* the frame's aliased set, and the two local rows
fail for different reasons. Chasing it further by construction rather than by instrumenting the
clearing decision is what ran this attempt into the ground; the next attempt should print the
retained/dropped split for one statement rather than infer it from six programs.

### Why nothing is committed

The change is sound and complete in itself, and it does not move a single obligation. Two earlier
entries record changes reverted for exactly that, and the reasoning holds here: what is worth
keeping is the measurement and the table above, not machinery that is inert.

## The other half, found by instrumenting instead of guessing

### What the previous entry got wrong

It said the missing half was the fact *clearing* after a call, built that, and measured zero. The
entry before it had recorded the same suspicion. Both were wrong about the site, and no amount of
further probing would have found it, because the function they narrowed is not the one that decides.

Instrumenting the decision took one build. Emitting a finding for every dropped comparison fact, at
each of `proof_clear_facts_after_call`, `proof_clear_facts_keep_type_bounds` and
`proof_resymbolize_binding`, produced *nothing* on a program whose range fact plainly disappears.
The fact was never dropped. It was cleared wholesale and not restored:

    facts.clear()
    facts.extend(probe_facts) if applied
    proof_restore_type_bound_facts(pre_call_facts, facts, ...)
    proof_restore_call_stable_facts(pre_call_facts, facts, ...) if not applied

An opaque call clears the state and restores what the callee could not have reached.
`proof_restore_call_stable_facts` is the decision, and it asked the frame's whole aliased set.

A second round of instrumentation, reporting which operand and which clause failed, split the
remaining failures into two unrelated causes: `root aliased`, meaning the collection was lent once
somewhere in the frame, and `no place root`, meaning the collection's recorded value is an opaque
call so `name.count` is not a place at all. Only the first is this entry's.

### What changed

`proof_restore_call_stable_facts` takes the lends of the call it follows and blocks
`escaping_names` together with them, exactly as loop entry blocks `escaping_names`. Its two callers
that know the call -- the summary-applied path and the opaque-call path in
`proof_check_frame_calls_in_expression` -- pass `proof_statement_lend_roots(expression, functions)`.
The four branch-join callers cannot name one call and pass the whole aliased set, which leaves the
union unchanged there.

### Fixtures

`examples/confined_lend_across_calls.elisa`: a loop whose body calls something on every iteration,
with the call lending a parameter, lending a local, and taking an element by value. All three keep
the range fact; all three fail before the change.
`examples/rejected_confined_lend_across_calls.elisa`: a lend that escapes through a
reference-holding parameter, a body that lends the very collection it is iterating, and a fact taken
before a lending call. All three stay refused -- the middle one is the point that confinement is
about outliving a call, never about the call itself.

### What it bought

On `examples/kernel_replay_standalone.elisa`: nothing. Obligations 2053, proven 1524, findings 539,
gaps 0, verified 122, unchanged in every bucket.

The second cause the instrumentation found is why, and it is now a specific defect rather than a
suspicion. A local bound to a call result -- `node: X = located.node`, `values: mutable darray = []`
followed by a fill -- has that call as its recorded value, so every fact the body takes over
`values.count` is recorded over `<call>.count`, whose place root is empty. The extent rules are all
written over places. Binding such a local to its own symbol, the way `proof_bind_unsigned_symbol`
already does for an unsigned scalar, is what would make those facts places again, and the kernel is
built out of exactly that shape.

## An aggregate local kept its initializer, so the places under it were not places

### What was wrong

A local's recorded value is its initializer, substituted. For a scalar that is what makes equality
reasoning work. For a container, a tuple or a struct whose initializer is a *call*, it is a defect:
the value is `<call>`, so every later `values.count` is recorded over `<call>.count` and every
`located.node` over `<call>.node`. Those have no place root, and the extent, alias and stability
rules are all written over places. An index into such a local was not merely unproven -- it was
reported `index-bounds-opaque` and given no obligation at all.

The previous entry found this by instrumenting the restore decision, which reported `no place root`
for exactly these terms. It is the shape the kernel is built out of: `located: (known, node) =
node_at(...)` and `values: mutable darray = []` followed by a fill appear in nearly every function.

### What changed

A local whose declared type is not a primitive scalar and whose initializer contains a call is
bound to its own symbol, the way `proof_bind_unsigned_symbol` already binds an unsigned scalar. The
equality with the call was never usable for an aggregate: nothing folds it, and an opaque callee's
result is not a value this state models. What the symbol buys is that the places under it are
places.

### Fixtures

`examples/aggregate_local_symbol.elisa`: a container local from a call, a struct local from a call,
and a loop over a container local from a call. All three verify; all three are `index-bounds-opaque`
before the change, with no obligation issued.
`examples/rejected_aggregate_local_symbol.elisa`: an unguarded index on such a local, a guard over a
different collection, an `ensure` that would need the callee's result value, and a local rebound
after its guard. All four stay refused -- the symbol makes places readable and says nothing about
the value.

Two existing fixtures changed shape rather than verdict. `branch_conjunct_placeholder` and its
rejected twin produced their placeholder by declaring a local from a call, which is now a place, so
the condition they were built around became admissible. They produce it by a rebinding instead --
an assignment still leaves the call as the value -- and the accepted one gains a companion function
recording that the declaration form is now readable.

### What it bought, and why two numbers go down

On `examples/kernel_replay_standalone.elisa`:

| | before | after |
| --- | --- | --- |
| obligations | 2053 | 2027 |
| proven | 1524 | 1512 |
| findings | 539 | 525 |
| `index-upper-unproven` | 147 | 133 |
| replay gaps | 0 | 0 |
| verified functions | 122 | 122 |

Obligations and proven both fall, which needs saying plainly rather than reporting the finding count
alone. Twenty-six index obligations disappear, in matched lower/upper pairs, at five functions. They
are duplicates: every one of them is at a `(function, line, rule)` that still carries at least one
goal afterwards, checked exhaustively rather than by sampling -- `difference_comparison` line 965
goes from eight pairs to two, `tactic_step_impl` line 2294 from four to one, and no site drops to
zero. The same index was being posed once per substituted form of its collection; with the
collection a stable symbol, the forms coincide.

Coverage moves the other way, which two probes show directly: an index into a container local from
a call goes from `index-bounds-opaque` with no goal to a real lower/upper pair, and an unguarded one
is still reported. Fourteen fewer failing findings for the same code, none of them silenced.

## A collection this frame only pushed to counted as escaping it

### What was wrong

`index-upper-unproven` was the largest remaining cluster, and grouping it by collection put the
blame on parallel arrays: eleven of its failures were loops over `lent.count` in the kernel's
lend-call handler, which carries `lent_places`, `lent_known` and `lent_exclusive` side by side. The
obvious reading is that the engine cannot relate three collections' counts.

That reading was wrong, and merging the three arrays into one `ProofKernelReplayLentArgument`
record measured it: findings 525 -> 522, three of the eleven. What the remaining eight were losing
was not a relation between collections but the loop's *own* range fact, `index < lent.count`.

The cause is where a method call's receiver is recorded. A receiver is not among a call's arguments,
so no argument mapping can describe it; the frame records it by name as a place a call can reach.
`lent.push(...)`, appearing anywhere in a frame, therefore put `lent` in the escaping set for the
rest of that frame -- and loop entry forgets everything in that set. So a collection that is built
by pushes and then walked, the commonest shape there is, could not be indexed. Nothing had reached
it; nothing could.

### What changed

The escaping set drops the receiver of a *known collection builtin* -- `push`, `extend`, `clear`,
`resize`, `pop`, `truncate`, the six `proof_resource_collection_builtin` already names. This is the
confinement rule the previous entry established, reaching the same conclusion by a second route:
`xs.push(v)` writes `xs` during its own call and leaves nothing behind that a later call could
reach, exactly as a lend that cannot outlive its call does.

Three things are deliberately untouched.

* `aliased_names` is unchanged, so the push is still a write: a `count` fact taken before it does
  not survive it, and a push in a loop body still reaches the collection on every iteration.
* The exemption is gated on the same `confinable` flag as the lend rule, so it applies only at the
  frame-wide site that fills the escaping set -- never at a call site.
* A builtin is not a known function, so every *argument* of one is still recorded. That is what
  keeps `sink.push(values)` from laundering a lend: the lend escapes through the argument even
  though the receiver does not.

### Fixtures

`examples/collection_builtin_extent.elisa`: a list built by pushes in a loop and then walked, a list
shrunk by `pop` and then walked, and two lists each confined on its own account. All three verify;
all three are `index-upper-unproven` under a build of the previous commit.
`examples/rejected_collection_builtin_extent.elisa`: an explicit lend into a parameter whose element
type can hold a reference, a push inside the loop body, an `ensure` that would need a `count` fact
to survive a push, and a lend pushed *into* another collection. All four stay refused, with
identical findings before and after the change.

### What it bought

On `examples/kernel_replay_standalone.elisa`, in the two steps:

| | before | record | receiver |
| --- | --- | --- | --- |
| obligations | 2027 | 2023 | 2027 |
| proven | 1512 | 1511 | 1527 |
| findings | 525 | 522 | 510 |
| `index-upper-unproven` | 133 | 131 | 119 |
| replay gaps | 0 | 0 | 0 |
| trusted assumptions | 0 | 0 | 0 |
| verified functions | 122 | 122 | 122 |

The record refactor is a change to the checked *source*, not to the checker, and it is reported here
because it is the measurement that redirected the work: it bought three findings where the
explanation it was built on predicted eleven. The receiver rule bought the other twelve and nine
more. No function crosses into `verified` -- each still owes other obligations -- which is why the
goal counts, not the function count, are the reading.

## A counter could not keep its own value across its own update

### What was wrong

`elisac-stage1` declined any body carrying a loop `invariant`, so the annotation the checker asks
for could not appear in a program this project compiles, and the nine `loop-invariant-missing`
findings could not be answered. The compiler now erases the annotation instead (`Elisa-compiler`
`src/backend/codegen_stmt_expr.elisa`, with a differential case beside it), which made the invariant
path testable for the first time -- and it failed on the simplest counter there is:

    rounds: mutable usize = 0
    while rounds < limit:
        invariant rounds <= limit
        rounds <- rounds + 1

`invariant-not-preserved`. The preservation goal's fact list carried only type bounds -- neither the
loop condition nor the invariant. Narrowing it outside any loop isolated the cause exactly:
`rounds <- 1` and `rounds <- seed + 1` both prove, `rounds <- rounds + 1` and even `rounds <- rounds`
do not.

`proof_bind_unsigned_symbol` resymbolizes a rebound local under *its own name* and then refuses the
binding fact when the value mentions that symbol -- which a self-referential value always does. So
the new value was dropped, and the resymbolization cleared every fact about the old one. A counter
could not keep its own value across its own update, in a loop or out of one.

### What changed

Two steps, and both are needed for either to show.

* A rebind whose value is written over the binding's own symbol takes a **fresh symbol**. The
  source name is bound to the fresh one, so every substitution reaches the new value; the old
  symbol then denotes the old value and nothing else, so every fact already recorded stays true of
  the value it was taken over and none of them is cleared. The update is recorded as the ordinary
  `local-binding` equality the non-self-referential case already emits, so replay needs no new rule.
  The names come from a fixed pool of 64 rather than being built -- nothing here can construct an
  identifier -- and the pool is per function; exhausting it falls back to the old behaviour, which
  forgets rather than assumes.
* The equality is only useful if the difference engine imports it, and it would not. An affine term
  `x + 1` enters the constraint graph only when the bounds prove it cannot wrap, and a counter
  bounded by a symbolic limit has no numeric upper bound. The goal side already had the argument
  this needs -- `x < peer` with a peer of the same unsigned width puts `x + 1` in range, since the
  peer is at most that width's maximum -- but it asked the finished constraint graph, which a fact
  being imported *into* that graph does not have. The fact side now asks the same question of the
  facts directly. Mirrored in `proof_kernel_replay_affine_peer_safe_from_facts`; without the mirror
  every one of these proofs gapped at the kernel, which is how the mirror was found to be required.

### Fixtures

`examples/loop_counter_invariant.elisa`: a `while` loop whose invariant establishes and is
preserved, the same over a collection walk where the index obligation is discharged through the
counter's bound, a straight-line increment that keeps its value, and two counters in one frame. All
four verify; all four fail under a build of the previous commit.
`examples/rejected_loop_counter_invariant.elisa`: an increment with no strict peer (the wrap guard's
own case), a non-unit step, an invariant that is false on the iteration reaching the bound, a total
accumulated beside a counter, and a pre-update fact that would prove the claim if it were read as
current. All five stay refused, with replay gaps 0.

### What it bought, and what it cost

On `examples/kernel_replay_standalone.elisa`:

| | before | after |
| --- | --- | --- |
| obligations | 2027 | 2033 |
| proven | 1527 | 1527 |
| findings | 510 | 516 |
| replay gaps | 0 | 0 |
| trusted assumptions | 0 | 0 |

The corpus moves *backwards* by six findings, and saying so plainly matters more than the direction.
The six are named exactly: `proof_kernel_replay_affine_peer_safe_from_facts` is a new declaration in
the checked source and is itself unverified (1), and the two functions that now call it or carry its
new parameters pick up its shadow (`proof_kernel_replay_collect_differences` 4,
`proof_kernel_replay_difference_comparison` 1). Every one is `function-summary-unverified`, the
cluster already recorded as a shadow of unverified roots. No goal that was proven stopped being
proven.

Nothing else moves because the kernel's own nine loops still carry no invariant: writing one
requires the fixed compiler to be the *installed* `elisac-stage1`, and the snapshot at
`~/.elisac/stage1` is pinned at a revision that predates the fix. The capability is what this entry
records -- the four fixture functions go from unprovable to verified, and the counter shape that
blocked all nine loops is no longer the obstacle. Moving the snapshot, and then annotating those
loops, is the next step and is deliberately not taken here: the snapshot is shared with every other
project on this machine.

## Replay admission and provenance audit

The next pass found three independent correctness/performance hazards in the self-hosting path.
Type-bound cleanup searched the complete historical trace table for every copied fact; batch kernel
replay also reallocated a whole-arena validator for each certificate; and certificate JSON origin
lookups repeated the same trace search. These were replaced with per-function type-bound membership,
one report-wide shape/range admission pass, and a flat certificate-fact-to-trace index. These are
only caches: no cache entry is a proof fact or a trusted assumption.

The audit also caught two boundary mistakes. `effect-containment` had been classified as a unary
node by the generic arena walker, so its child call entries were not admitted by the ordinary
validator; it now validates the declared row and every call entry explicitly. More importantly,
fact-trace revalidation trusted the report-wide admission bit after a caller mutated a serialized
kernel node. Public fact-trace entry now always invokes strict per-root arena admission, so a hidden
payload or a replaced normalized argument fails closed even after an earlier successful replay.

The self-hosting corpus remains deterministic and gap-free after the changes: the large replay
fixture reports 2,066 obligations, 1,542 replayed certificates, and 0 replay gaps. The full proof
matrix passes, and the executable dogfood probes cover the mutated lemma/function summary,
floating-point, unsigned, alias, region, tactic, effect, arena, bootstrap, and loop-counter cases.

## Repaired: tactic `simp` replay accepted a stronger goal

The independent tactic-transition kernel originally checked `simp` by asking whether the old goal
could be found inside the new goal's proof-depth relation. That was too weak for a transition
certificate: a forged snapshot could change `p` into `p and true`, which contains the old goal as a
conjunct but is not a rewrite performed by the Elisa tactic. A later action would then continue
from a strengthened proposition that the source tactic never produced.

The replay kernel now mirrors the exact bottom-up simplifier: it recursively normalizes only unary
and binary terms, folds checked integer arithmetic and integer comparisons, folds Boolean equality
and connectives, and removes double negation. Non-binary formers remain opaque, and overflow or
invalid arithmetic remains unknown. The transition is accepted only when the independently
normalized old goal is structurally equal to the supplied new goal; if the new goal is marked
solved, ordinary proposition replay still has to close it from the post-state facts.

`examples/kernel_arena_runtime.elisa` directly submits the forged `p -> p and true` transition and
requires rejection. The full stage1 matrix, stage1 dogfood, and stage0 bootstrap harness all pass,
including the existing positive simplification and overflow cases, with zero replay gaps.

## Repaired: proof import accepted malformed include directives

The proof importer recognized the prefix of an include directive and returned the quoted path as
soon as it saw the closing quote. It therefore erased a line such as
`include "./included.elisa" trailing` and proved the remaining program. The compiler's include
reader matches the complete physical line and accepts only spaces, tabs, or CR after the quote;
both compiler stages reject the malformed line as source instead.

The importer now applies the same trailing-byte check. `examples/rejected_include_trailing.elisa`
is a permanent regression: before the repair the proof binary incorrectly returned `proved`, while
the compiler returned a parse error; after the repair the proof binary returns `failed` with no
certificate emitted. It is part of `scripts/dogfood.sh`, which also checks deterministic output and
independent certificate replay.

The same audit found two more import mismatches. The importer used to silently stop at a repeated
path, so a cycle could be erased and the remaining declarations proved even though the compiler
rejects cyclic includes. It also canonicalized only `./`, so `./included.elisa` and
`./sub/../included.elisa` were treated as different files. The importer now keeps an active
recursion stack separate from the include-once set, rejects active-path re-entry, and uses the
compiler's lexical path cleaning for `.`, `..`, and repeated separators. Relative roots are made
cwd-relative before the walk. `examples/rejected_include_cycle_a.elisa` guards the rejection, while
`examples/include_alias_diamond.elisa` guards one-time expansion through an alias.

Finally, expansion now flushes only an unterminated final physical line. The old `<=` sentinel
always appended a synthetic blank line to newline-terminated files, changing imported byte counts,
fingerprints, and downstream source locations.

## Repaired: NUL include paths were truncated at the proof import boundary

An include path containing an embedded NUL exposed a source mismatch across the proof importer's
C-string file API. The compiler kept the NUL in its path and rejected the filename as invalid,
while the importer appended a terminator and passed the path to `proof_read_file_checked`; the
operating-system call therefore saw only the valid prefix. A reproducer with
`./included.elisa\0ignored.elisa` made the proof CLI import `included.elisa` and report `proved`
while Stage0 rejected the exact source with `invalid argument`.

The importer now rejects any NUL in the root or resolved include path before recording, comparing,
or opening it. The dynamic dogfood regression verifies that Stage0 rejects the binary source and
the proof CLI reports an import error without importing the prefix declaration. A type-bound
certificate for the remaining parsed function may still replay, so the check asserts failure,
absence of the truncated declaration, and zero replay gaps rather than requiring zero certificates.

The same audit found that the compiler accepts `{$include path}` and `{$i path}` in addition to
`include "path"` and `#include "path"`. The proof importer now recognizes those aliases, their
case-insensitive keywords, and quoted or unquoted macro arguments. `examples/include_macro.elisa`
exercises the long alias with double quotes and the short uppercase alias with single quotes; it
proves and replays under the pinned Stage0. Both `scripts/dogfood.sh` and `scripts/test.sh` cover
the fixture. The full Stage0 dogfood run and the ordinary proof matrix pass after the repair.

## Repaired: root source was truncated at an embedded NUL before proof checking

Unlike included paths, root file contents are read into a length-aware byte array and then passed
to the compiler lexer through `frontend_parse`, whose convenience wrapper derives its length as a
C string. A source containing a valid proof, an embedded NUL, and malformed compiler-visible
trailing bytes therefore returned `proved` in the proof CLI while the compiler rejected the same
file. Reusing the original byte count for `frontend_tokenize_with_length` removes that truncation.

The full-length parse also exposed an error-boundary defect: the proof CLI continued into proof and
semantic analysis with an AST that already contained parser errors; the adversarial reproducer
could hang there. The CLI now emits parse-error findings and skips proof replay and semantic
analysis whenever parsing fails. Parse-error sources are not source-admissible for tactic or
repair outputs. The dynamic dogfood regression asks Stage0 and the proof CLI to reject the same
NUL-containing file, checks exact imported byte length and parse-error findings, and requires zero
declarations, proof obligations, proven results, or replay gaps.

## Repaired: non-UTF-8 Elisa names could corrupt JSON reports

The compiler lexer deliberately accepts certain single-byte Latin-1 letters in identifiers when
they are not part of a valid UTF-8 sequence. The report encoder previously copied every byte
above ASCII directly into a JSON string, so a compiler-accepted identifier containing `0xff`
produced invalid UTF-8 JSON. Other control bytes were replaced with `?`, which could also distort
the displayed proposition or diagnostic.

The encoder now preserves valid UTF-8 sequences, escapes malformed bytes as `\\u00XX`, and emits
JSON escapes for unhandled control bytes. The diagnostic-byte writer shares this same validation
path. A dynamic Stage0 dogfood regression checks a Latin-1 identifier alongside valid Greek UTF-8
and parses the resulting JSON; a separate Stage0 diagnostic probe checks an unresolved Latin-1
identifier is preserved as `ÿ` in valid JSON. The full dogfood suite passed after the encoder
change.

## Repaired: batch arena admission could accept a disconnected cycle

The report-wide kernel admission pass checked node shapes and direct ranges, but did not enforce
the producer's append-only arena order. A cyclic component that was not reachable from the first
certificate root could therefore pass `proof_kernel_replay_arena_all_report`, even though the
strict single-root validator rejected the same cycle. A batch validator also has to stay bounded
on the large self-hosting report; a graph worklist that retained one allocation per disconnected
component exhausted memory while auditing `kernel_replay_standalone`. The local pass also omitted
the direct payload edge of `resource-use`, `resource-write`, and `resource-move`, leaving one
class of malformed resource node under-validated.

The arena format is now explicitly admitted in canonical postorder: every direct or child-list
edge must point to an earlier node. This rejects self-cycles, forward edges, and every directed
cycle in the existing local shape/range pass without a graph-sized traversal or per-component
allocation. Exact depth remains checked by strict per-root replay for every certificate before
its logical rule executes. `examples/kernel_arena_runtime.elisa` directly checks that the public
batch report rejects a self-cycle and an out-of-range resource edge, while the full stage1 matrix,
stage1 dogfood, and stage0 bootstrap harnesses pass with zero replay gaps.

The same edge inventory had one remaining omission in the strict validator: `resource-call-result`
stores the completed `resource-call` event in its `left` field, but the arena walker treated the
node as a leaf. A malformed result could therefore pass standalone arena admission until the
resource replay tried to dereference it. The result node is now traversed and checked in the
iterative validator as well as the batch postorder pass; the arena harness supplies an out-of-range
result edge regression.

The batch edge inventory also omitted `resource-disjoint`'s premise child slice. Its three direct
expression roots were checked, but a malformed `children_start`/`children_count` pair could still
make `proof_kernel_replay_arena_all_report` return true. The batch pass now checks that slice and
the arena harness supplies a shape-valid disjoint node with an out-of-range premise range.

## Repaired: cached arena admission skipped semantic child validation

The report replay pass caches `proof_kernel_replay_arena_all_report` before replaying many
certificates. Its postorder walk checked node payloads, child ranges, and backward-edge order, but
did not carry forward the per-node semantic validity bits used by strict admission. A malformed
`call` whose child slice contained an ordinary expression instead of a `call_arg` could therefore
be marked admitted by the batch path and reach an `*_after_arena` replay entry point.

Batch admission now computes and stores the same child-validity relation while walking the
postorder arena. The fast path therefore rejects malformed child kinds before the cache becomes
trusted. `examples/kernel_arena_runtime.elisa` includes a direct regression for the cached call
case. The complete stage1 dogfood suite, executable arena harness, and all stage0 bootstrap
harnesses pass with zero replay gaps after the repair.

## Repaired: source-bound tactic state relied only on erased kernel metadata

Source-bound tactic replay compared the reparsed goal and facts with their recorded attempt only
after lowering them into the source-neutral kernel arena. That arena intentionally erases some
source metadata, including a quantifier binder's declared type. The source-side facts range was
also not checked in the shared matcher before indexing the report's captured facts.

The shared kernel matcher now checks the captured-fact range before indexing and is the deliberate
relation used by the CLI after the source state has been serialized and reparsed in a fresh AST
store. A separate same-store matcher adds exact `proof_expr_equal` checks for callers that can
legally dereference the original AST; its regression rejects a quantifier whose binder type was
changed from `i64` to `bool`. The source-neutral kernel remains intentionally metadata-light, and
the cross-store CLI boundary remains serialization-plus-kernel based because imported AST handles
are not valid to dereference from the tactic store.

The tactic runtime covers both a forged fact-range offset and the same-store typed-quantifier
identity check. The complete stage1 dogfood suite, including nested source-bound branches and
stage0 bootstrap harnesses, passes with zero replay gaps after the repair.

## Repaired: portable quantifier tactics were accepted without kernel closure

The source-level tactic decision procedure could prove a finite contract quantifier, but the
independent tactic certificate path sent the encoded quantifier block through the ordinary goal
replay tiers. Those tiers intentionally do not interpret quantifier ranges, so the producer could
report `decide` as accepted while `kernel_replayed` and `certificate_replayed` were false.

Kernel goal replay now dispatches a validated quantifier root to the finite quantifier rule before
the arithmetic and bounded-model tiers. The portable quantifier regression requires both the
producer decision and the complete source-neutral certificate to succeed, preventing this class of
producer/kernel disagreement from being hidden behind a successful tactic action. Stage1 tests,
the full dogfood suite, and stage0 bootstrap harnesses pass after the repair.

## Repaired: tactic JSON silently wrapped overflowing source lines

The tactic interchange parsed a JSON `line` as a signed integer and converted every nonnegative
value directly to `u32`. A value above the representable source-location range therefore wrapped
to a different line while the rest of the script continued to execute. That can corrupt diagnostic
identity and annotation binding even when the proof proposition is unchanged.

Line parsing now returns an explicit `(known, value)` result and rejects values above the shared
`u32` maximum for both expression positions and contract-quantifier annotations. The existing
safe-integer gate still protects JSON numbers from binary64 rounding, and the two malformed
fixtures cover both line-bearing paths. The stage1 test matrix, full dogfood suite, and stage0
bootstrap harnesses pass with the overflow rejected before any tactic action runs.

## Repaired: a moved resource could remain a return witness

Resource replay records each valid `resource-use` as a possible witness for a returned region
capability. The witness list was append-only, so a forged trace could use an earlier witness after
the same reference binding had been moved. The return marker checked the binding name, region,
reference mode, and mutability, but not its current moved state; this allowed a capability to be
derived from a value that no longer existed at that program point.

Return-witness validation now requires the witnessed binding to be live and unmoved. The executable
arena harness includes a trace that uses, moves, and then returns the same reference through the old
witness; the independent resource kernel rejects it, while the full stage1 dogfood and stage0
bootstrap coverage remain gap-free.

## Repaired: quantifier replay reset its termination ranking

The finite quantifier rule called ordinary goal replay with `depth = 0` for every instantiated
body. Nested quantifiers could therefore reset the kernel's explicit term-depth bound, and stage1
accepted a mutually recursive replay cycle that stage0 could not establish as terminating.

The quantifier, collection, and dictionary helpers now carry the caller's ranking and increase it
before replaying each instantiated body. A direct runtime regression proves a small nested
quantifier and refuses a deliberately over-deep nest. The same harness compiles and runs under both
stage1 and stage0, so the termination guarantee is checked by both compiler generations.

## Repaired: overloaded operators crossed proof-state boundaries

The checker previously treated every unary and binary AST operator as if it were a primitive,
state-preserving operation. Elisa also dispatches operators such as `==` and `+` to user protocol
methods for non-primitive operands. A method can mutate its receiver, so carrying facts from before
the operator into the following branch or postcondition could certify a false theorem. A concrete
`Counter.__eq__` regression incremented its receiver and still let the caller prove that the value
remained zero.

Expression admission now requires every operator and index operation that crosses a proof-state
boundary to have an explicit source-backed witness: built-in scalar operations are admitted only
when the imported declarations do not override them, while user-defined and opaque element
operations remain unsupported. Unwitnessed operators are reported as unsupported and all facts are
forgotten at that boundary. Witness insertion also records a provenance trace, so a fact restored
into a later state cannot become an untraced replay premise. The method body remains checked by the
existing resource and scalar rules. `examples/rejected_operator_effect.elisa` pins the regression;
the stage1 build, independent replay, and full test matrix must all reject it without replay gaps.

## Repaired: a certificate could be rebound to another goal attempt

Replay matched a certificate against any successful attempt with the same root metadata, but did
not require that attempt's `certificate_index` to equal the certificate's position in the report.
Because the index also identifies certificates during recursive summary replay, a mutated report
could redirect a goal to another certificate that happened to share its metadata.

Replay now requires the exact indexed attempt to own the certificate. The adversarial executable
replaces one attempt record with an out-of-range certificate index and checks that replay refuses
it, then restores the record and checks that all certificates replay again. Per-goal and theorem
output use the same binding predicate rather than trusting the report's raw index.

## Repaired: a goal's displayed AST could differ from its replayed root

The certificate AST was checked against the source-neutral kernel root, but the duplicated AST on
the goal attempt was not. Reporting code could therefore pair a replayed certificate with a
different displayed goal if a report was mutated after checking.

Attempt admission now independently checks that its AST mirror agrees with the same kernel root
(or, for resource, structural, and effect certificates, both mirrors must be the canonical `true`
sentinel). The shared output predicate is used by focused-goal, report, and theorem-catalog output.
The adversarial runtime replaces only an ordinary attempt goal, then jointly replaces both inert
mirrors; replay and output admission must reject each mutation, then accept the restored report.

## Repaired: a summary trace could be reclassified as a trusted boundary

Both trace validators dispatched trusted facts by `trace.kind` before checking that the rest of
the record had the shape of a boundary fact. A caller could replace a `ProofFactTrace` in the
mutable report array with the same record relabeled as `precondition`; the source and kernel
validators would then bypass the summary's declaration, argument bindings, and required-goal
certificates. Direct field mutation is forbidden by Elisa, but replacing the array element with a
new record is permitted and is covered by the public revalidation threat model.

Trusted-boundary admission now requires empty dependency, premise, and summary payloads, a zero
ensure index, and in-range empty summary slices. `examples/lemma_summary_replay_runtime.elisa`
replaces a valid lemma-summary record with a boundary-labeled copy and requires rejection, then
restores the original and requires replay success. The full pinned-Stage0 dogfood run passes,
including this native mutation harness and the final tactic/source-binding checks, with zero
replay gaps.

The Stage1 Gen2 test matrix and dogfood report/runtime/tactic suites pass after these repairs with
zero replay gaps. Stage0 bootstrap was deliberately skipped: the available Stage0 did not pass the
repository's provenance guard, so no Stage0 parity claim is made for this run.

## Repaired: imported source could claim the proof system's internal identifiers

The proof kernel encodes compiler-derived type witnesses and fresh rebinding symbols as ordinary
identifier names in its current source-neutral AST. Elisa itself permits declarations such as
`__elisa_unsigned_type_bound`, so a source program could define that predicate and use its call in
a contract. The producer then treated the user predicate as an unsigned-type witness and marked
`value >= 0` proven for an `i64`; independent replay refused the certificate, leaving a replay gap
and an internally inconsistent `verified` declaration result. The same naming convention is used
by the checker's fixed fresh-symbol pool.

The importer scans the compiler's collected globals, function parameters, local binders, and
references before generating any proof state. It rejects exact collisions with the proof kernel's
serialized type-witness names and fixed fresh-rebinding pool, with no proof attempts or certificates
emitted. A full-source dogfood run then exposed that reserving the entire `__elisa_` prefix also
rejected legitimate compiler-library globals such as `__elisa_region_cache`, preventing the proof
assistant from importing the compiler it is intended to verify. The guard now reserves only names
the proof system actually emits; an unrelated `__elisa_` source name is covered by a positive
regression while forged witness and rebind names remain rejected. This preserves the collision
boundary without treating a compiler naming convention as proof-system ownership.

## Stage0 compiler parity and lifetime checks

At the earlier audited Stage0 pin `26a77303`, the compiler's binding-free top-level `or` pattern
analysis was brought in line with Stage1 for string, integer, enum, and const-enum patterns;
alternatives use isolated scopes, and binding alternatives fail closed. That revision also closed
scoped-store lifetime gaps, summarized struct-field forwarding once before its fixpoint, and passed
the compiler fast/full suites plus the complete proof dogfood/runtime and `scripts/test.sh` matrices
with zero replay gaps.

The currently selected Stage0 pin is `601f7bcd3de62877723ab7f5c5f9a502fb6ef9ae`. Its installed
binary reports that exact Go VCS revision with a clean build; it successfully bootstrapped the
latest Stage1 product and accepts the deep-expression regression input. The full Stage0 proof
matrix has not been rerun at this refreshed pin, so the historical pass above is not attributed to
it. Neither result completes the broader coverage table below.

## Repaired: recursive semantic analysis could crash proof import

A 768-term left-associated arithmetic expression is parsed iteratively, but recursive semantic
expression walks exceeded the native stack. The crash report localized the fault to
`Semantic.walk_expression_inner` at the stack guard. An earlier guard covered only the separate
operator-compatibility walk; the proof importer's selected `check_full` mode bypassed that pass and
still crashed. The pinned Stage0 compiler accepts the source in permissive mode, so it remains a
useful importer robustness regression rather than a malformed-source test.

The compiler now shares a named 128-level expression-analysis bound across both recursive walks.
Every exhausted path emits the hard `ExpressionAnalysisDepthExceeded` diagnostic instead of
silently skipping an unvisited subtree or recursing until stack exhaustion. The proof repo is pinned
to compiler commit `4cf3d6a8`, based on upstream main tip `fd2cb3cf`, and includes the original
operator guard (`59c4d3f2`), all-walk fix (`cfd99261`), NUL-path rejection (`002922fb`), conservative
compound-assignment handling (`486d406b`), and exhaustive Unicode scalar-value parity. The dynamic
proof dogfood compiles its input with the provenance-checked Stage0 oracle, then requires the proof
CLI to return a valid failed/unsupported JSON report, one semantic error, zero replay gaps, and
independent kernel replay without crashing. It passes under the final Stage1/proof build.

## Repaired: Stage1 include paths containing NUL no longer truncate

Differential testing against the freshly rebuilt Stage1 CLI found that an include path containing
an embedded NUL was silently truncated at the C-string boundary: Stage0 rejected the source, but
Stage1 opened the valid prefix and compiled it. `expand_includes` now detects NUL bytes in its
owned path buffer before path normalization or any C-string filesystem call, and fails closed with
the normal include-read diagnostic. The regression in the compiler's direct-CLI include suite
requires both stages to reject the source and Stage1 to emit no object. Compiler commit
`002922fb` contains this fix and its regression.

The Stage1 product used for the verification run recorded in this section was rebuilt from compiler commit
`4cf3d6a82106cb11414d9fe9980ebf085fd6710d`, based on the latest upstream main tip
`fd2cb3cff470319500db362e5fce2833cbe300de`, plus the recursion-limit, NUL-path, conservative
compound-assignment, and full Unicode scalar-classification fixes. The installed snapshot under
`~/.elisac/stage1` remains older and is not used for this run.

## Repaired: unknown compound-assignment targets stay conservative

The per-file frontend/stdlib audit found a false `augmented assignment requires numeric operands`
on `structs.cond_bind_names += name`: the target field's declaration lives in a sibling module,
while the right-hand `sview` is visible in the isolated file. The check now emits a numeric error
only when the target is known and non-overloadable; an unknown target no longer turns a firm RHS
type into an unsupported claim about the operator. A dedicated unresolved-field control covers
this boundary. Compiler commit `486d406b` passes the operator smoke suite, including the 768-term
depth refusal and a zero-false-positive scan of all 800 frontend/stdlib Elisa files.

## Repaired: concurrent proof builds cannot overwrite shared outputs

Two proof builds previously wrote the same object and executable paths directly. `scripts/build.sh`
now takes a per-project build lock, compiles to process-specific temporary files, and atomically
publishes the object and executable only after successful linking; a failed build preserves the
last good executable. Both `scripts/dogfood.sh` and `scripts/test.sh` completed sequentially against
the pinned Stage1 product after this change.

## Repaired: Unicode scalar-value identifiers import consistently

Stage0's lexer classifies decoded runes with Go's Unicode 17.0 `IsLetter`/`IsDigit` tables, while
Stage1 previously handled only selected multibyte ranges. This made valid source names such as
`cjk_漢` fail lexing, so proof import failed closed without declarations or obligations. Stage1 now
decodes valid two-, three-, and four-byte UTF-8 and uses generated, plane-dispatched range predicates
from those same Go Unicode tables. The generator and generated predicates live in the compiler lexer
tree. An exhaustive token-level differential checked every non-ASCII Unicode scalar from U+0080
through U+10FFFF, excluding surrogate code points, in both identifier-start and continuation
positions: 1,111,936 scalar values, with every Stage1 token stream matching the pinned Stage0 oracle.

The Stage1 compiler also builds identifiers containing Deseret (`𐐀`), CJK Extension B (`𠀀`),
mathematical alphanumeric letters/digits (`𝜆`, `𝟝`), and an Adlam digit continuation (`𞥐`). Dynamic
proof dogfood requires each corresponding declaration to be verified, not merely parsed. No known
Unicode scalar-value classification parity gap remains between this pinned Stage0 and Stage1.

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

## Current compiler pin and optimized replay verification (2026-09-15)

The proof project now pins compiler commit `1399160a1cafc981f9e7ccdafcbb4a90e5699454` in
`ELISA_COMPILER_REV`. The Stage1 product was built from its parent compiler-source revision
`05289f0430b359b4a28b761590a6a623f8497aec`; the tip commit adds only a smoke-test link fix and
does not change `src/` or `elisacore_std/`. Its compiler base includes shared typed scalar lowering
for EDIR and LLVM (`19f86a3b`, `c605b3fa`) and the subsequent native DWARF source-line mapping
change (`ce9e0292`), with the required Stage0-parity and soundness fixes rebased on top. The Stage1
product was rebuilt from the provenance-checked Stage0 binary (`601f7bcd`) and checked for source
freshness. A separate test-only commit fixes the native-object smoke helper's missing runtime link
input.

The supported installer has updated the normal `~/.elisac/elisac-stage1` launcher and runtime to
snapshot revision `1399160a`, matching this proof pin. The previous installed `1cbce422` snapshot
is preserved at `~/.elisac/stage1.backup-before-05289-20260915` for rollback.

`scripts/test_optimized_replay.sh` builds the proof system at O2 and O3, runs the verified,
sum-bound, and dogfood-kernel examples, and checks that every proven goal has independently
replayed status; it passes at both levels. The full `scripts/test.sh` matrix passed against the
immediately preceding combined compiler revision; after the DWARF-only follow-up, the default O0
build and verified example also pass, along with the O2/O3 replay regression.

The compiler's broader standalone native-object smoke remains inconclusive on this host: newly
linked native executables stalled in macOS `_dyld_start`, including executables produced by both
Stage0 and Stage1. The same differential timeout on both stages points to the host loader rather
than a Stage1-only code-generation regression. The smoke helper link failure itself was corrected,
but its complete runtime sweep should be repeated when native executable startup is healthy.

## Current verification checkpoint (2026-09-19)

The proof tree is clean at commits `3fdff6f` and `4706a7a`. The proof checker now releases the
compiler `Semantic::SymbolTable` before running its source-independent proof schedules. The CLI
also preserves the compiler's diagnostic normalization policy when copying diagnostics out of that
short-lived table: concrete violations suppress weaker unproven messages, non-exhaustive matches
suppress derived missing-return messages, and duplicate ensure findings are collapsed by source
identity. This is a memory-lifetime and diagnostic-fidelity fix, not a change that treats a
compiler diagnostic as a proof certificate.

The installed Stage1 snapshot at `~/.elisac/stage1` records `dcf5ce47`, matching the full
`ELISA_COMPILER_REV` pin `dcf5ce4781c073b4669f7c85441bf82e5322a3c9`. The installed Stage0 product
matches `ELISA_STAGE0_REV` `226451af4b5039f55adc6c543bdec1d8274b3289` and passes its provenance guard.
The build guard rejects a Stage1 product whose embedded snapshot revision differs from the pinned
front end; the active compiler checkout is intentionally not used while it has uncommitted work.

Evidence after the fixes:

- the complete `scripts/test.sh` matrix passes under the pinned Stage1;
- the complete `scripts/dogfood.sh` corpus passes, including independent kernel replay, Stage0
  bootstrap harnesses, tactic certificates, forged/stale certificate rejection, and deterministic
  repeat checks;
- the targeted region/diagnostic regression passes under both Stage1 and Stage0;
- no Elisa source file exceeds 600 lines, with the largest at exactly 600;
- the full `src/main.elisa` audit remains open. A 20-minute bounded run reached about 3.6 GB RSS
  during whole-program function-summary verification and emitted no report. The earlier 1.5 GB
  watchdog termination and this controlled high-memory timeout establish a scalability defect in
  the monolithic self-audit; they do not justify raising proof verdicts, skipping compiler
  semantics, or calling the full self-audit complete.

The current proof binary was also rebuilt at `-O2`; its verified example and region/replay
regression passed. A separate ten-minute `src/main.elisa` run at `-O2` still emitted no report,
peaking at about 4.16 GB RSS. The same behavior at O0 and O2 localizes the open issue to the
proof/import workload and retained whole-program summary state, rather than the native optimizer.

## Importer memory follow-up (2026-09-19)

The proof importer now uses the compiler's caller-owned `Semantic::check_full_into` API in both
semantic preparation paths. The symbol table is initialized in the caller and threaded through
the Elisa assignment form, so the compiler does not return a giant semantic table by value before
the proof phase begins. This is a real lifetime/ownership improvement and is accepted by both the
pinned Stage1 and Stage0 compilers.

The targeted region and diagnostic regressions pass under both stages. The complete optimized
test matrix and `scripts/dogfood.sh` also pass, including independent kernel replay, forged and
stale certificate rejection, deterministic repeat checks, and Stage0 bootstrap/runtime harnesses.

The full `src/main.elisa` audit remains incomplete after this change. A 180-second bounded run
reached about 0.96 GB RSS without producing a report; a 900-second bounded run reached
4,362,000 KB RSS and was stopped by the time guard without producing a report. The in-place API
removes one known table-return/copy path, but it does not yet solve the monolithic self-audit
scalability problem. No incomplete run is treated as proof, and no verdict or semantic check is
weakened to make the audit finish.

An optimized comparison does not change that conclusion: the in-place O2 binary was stopped by a
300-second time guard at 4,891,664 KB RSS with no report. Optimization changes the constant factor
but does not remove the whole-program memory/time growth.

## Dogfood regression checkpoint after importer fail-closed tightening (2026-09-19)

The complete `scripts/dogfood.sh` run passes after the aggregate include-expansion bound and the
NUL-path importer regressions. An invalid include path now produces an `import-error` with zero
semantic diagnostics, zero imported source bytes, zero declarations, and zero replay gaps; the
dogfood assertions previously expected a semantic diagnostic and a partially imported declaration
set, which was weaker than the fail-closed importer behavior. Those expectations were corrected in
proof commits `76b868c` and `aa3999c`. The same run still passes the root-NUL, deep-expression,
Unicode/JSON, replay, tactic, forged-certificate, repair, and Stage0 bootstrap suites.

The proof build remains provenance-pinned to Stage1 snapshot `dcf5ce47`. Two additional semantic
lookup optimizations are committed in the compiler worktree (`2e679b5e` and `40aae61d`) and have
been checked with Stage0-built differential products, but they are not silently used by this proof
tree while the installed snapshot and `ELISA_COMPILER_REV` remain at `dcf5ce47`. A dirty live
compiler checkout is never treated as proof-build input; moving the pin requires a fresh snapshot,
provenance check, and a new complete matrix run.

An isolated clean Stage1 product built from `40aae61d` was also benchmarked against the unchanged
proof source. Its ten-minute bounded full-source audit reached a peak of 4,689,408 KiB and emitted
no report before the time guard stopped it. This is not a regression in correctness, but it shows
that the semantic lookup indexes improve local compiler hot paths without removing the retained
whole-program proof schedule's scalability wall. The temporary benchmark worktree was removed and
the pinned compiler was left unchanged.

## Latest compiler snapshot and protocol-bound lookup checkpoint (2026-09-19)

The proof tree now pins compiler revision `c4c3c94528e5b78e8ae4613e787ba75d8dfffe5d`, and the
installed `~/.elisac/stage1` snapshot was rebuilt from a clean checkout of that exact revision.
The compiler change is committed as `c4c3c945`: protocol-parameter lowering now uses a
collision-safe fixed-bucket index for parser-known struct names instead of scanning every struct
for every parameter. The indexed path preserves the important rule that an owner-matching
concrete struct prevents protocol sugar; the first implementation accidentally inverted that
result, the Stage1 runtime rebuild caught it, and the correction was made before the commit was
published. Same-named structs from other modules remain eligible for the later owner check.

Evidence for the new snapshot:

- the Stage0-seeded clean Stage1 product rebuilt its runtime object successfully;
- protocol-parameter smoke passed under both Stage0 and Stage1;
- the full differential corpus reported `142 agreed, 0 diverged, 0 xfail, 3 skipped` (the skips
  were rejected by Stage0 itself);
- the complete proof test matrix passed, including O2/O3 optimized replay checks;
- the complete `scripts/dogfood.sh` harness passed with deterministic reports, independent replay,
  certificate/tactic rejection checks, runtime checks, and Stage0 bootstrap harnesses.

This advances the pinned frontend and improves a measured parser hot path, but it does not close
the open monolithic full-source self-audit scalability issue recorded above.

## Protocol declaration projection checkpoint (2026-09-19)

The pinned compiler was advanced to `62113e7c4508812b1bf818c24d8eedc88188c4f8`, rebuilt from a
clean checkout, and installed as the current Stage1 snapshot. This compiler change adds a
declaration-only projection of the parser annotation stream and makes unknown-type protocol
constraint checks consult that projection. Generic-interface implementation checks continue to
use the complete annotation table, so the optimization does not discard implementation metadata.

The initial candidate was exercised under Stage0 bootstrap before installation. It passed the
complete compiler differential corpus (`142 agreed, 0 diverged, 0 xfail, 3 skipped`), the full
proof test matrix including O2/O3 replay, and the complete dogfood suite ending with independent
replay and `formalized layers are replay-complete`. The live compiler checkout still contains
unrelated uncommitted work; only the three semantic files for this change were committed.

The full `src/main.elisa` self-audit remains open and bounded by the retained whole-program
summary workload; this lookup optimization is not presented as a completed self-proof.

## Function-name span projection checkpoint (2026-09-19)

The pinned compiler was advanced to `60a9a2aa8c04652400ef633b42cce497b2521c49`, rebuilt from a
clean Stage0-seeded checkout, and installed as the current Stage1 snapshot. The compiler change
adds a sparse projection for `__lsp_func_name` annotations. Symbol collection now searches only
function-name markers when attaching declaration spans, while preserving the exact owner/name/
offset match and the existing empty-position fallback.

The candidate passed Stage0 bootstrap, the full differential corpus (`142 agreed, 0 diverged,
0 xfail, 3 skipped`), the proof test matrix including O2/O3 replay, and the dogfood log reached
`dogfood audit passed: formalized layers are replay-complete`. The dogfood wrapper's final shell
status variable was not reused because zsh reserves that name; the logged dogfood run itself
completed successfully.

The bounded full-source self-audit is still incomplete; the latest profile moved its dominant
semantic sample away from protocol lookup and toward function-name span lookup, allocator churn,
and parser effect installation. No incomplete audit is treated as proof.

## Parser effect-installation index checkpoint (2026-09-19)

The pinned compiler was advanced to `94c96e9b4ad62060d33414d5debc4f6801b46496`, rebuilt from a
clean Stage0-seeded checkout, and installed as the current Stage1 snapshot. Effect-installation
metadata is now stored in sparse parallel parser tables. Effect and handler names, identity IDs,
and captures are resolved through the installation rows rather than scanning the complete parser
annotation stream on every effect-polymorphic lookup. The installation order and first-match
behavior remain unchanged.

The candidate passed Stage0 bootstrap, the full differential corpus (`143 agreed, 0 diverged,
0 xfail, 3 skipped`), the proof test matrix including O2/O3 replay, and the complete dogfood
suite ending with `dogfood audit passed: formalized layers are replay-complete`. This is a parser
performance/scope-preserving change; the monolithic full-source self-audit remains bounded and
incomplete, so it is not treated as a self-proof.

## Readonly function projection checkpoint (2026-09-19)

The pinned compiler was advanced to `763d9f22348bc90979d51796b8f30599a5a52520`, rebuilt from
a clean Stage0-seeded checkout, and installed as the current Stage1 snapshot. Readonly-function
declarations now use a sparse symbol-table projection rather than scanning all declarations for
each readonly-reference query. The projection records the declaration name and owning module;
the final implementation preserves the caller-owned symbol table through `lmut` region
transport. An earlier by-value helper shape was rejected because it would have made the
projection update local to the helper, so it was corrected before this snapshot was accepted.

The candidate passed the full compiler differential corpus (`143 agreed, 0 diverged, 0 xfail,
3 skipped`), the proof test matrix including O2/O3 optimized replay, and the complete dogfood
suite ending with `dogfood audit passed: formalized layers are replay-complete`. The live compiler
checkout retains one unrelated installer-script edit; it was not included in this change. The
monolithic full-source self-audit remains open and bounded, so this checkpoint is not presented
as a completed self-proof.

## Bounded full-source rerun after readonly projection (2026-09-19)

With the proof build pinned to the validated `763d9f22` Stage1 snapshot, the guarded
`src/main.elisa` audit was rerun with a 180-second time limit and a 1,500,000 KiB RSS limit. It
stopped at the time limit after 180.04 seconds, with a peak RSS of 859,440 KiB and no partial JSON
report. The run therefore remains incomplete; its exit is not a proof failure and no verdict was
promoted from the empty report. The lower observed RSS is useful performance evidence, but the
retained whole-program scheduling/scalability wall still needs a separate bounded decomposition
or profiling pass.

## Readonly contract lookup index checkpoint (2026-09-19)

The pinned compiler was advanced to `54472098e62f5b814527d4d70ce36bc973d73e71`, rebuilt from a
clean detached checkout seeded by Stage0, and installed as the current Stage1 snapshot. The
readonly-reference pass now builds a collision-safe hash-chain projection over its existing
parallel declaration rows. Resolver and mutable-reference contract queries still compare the
full callee name, module owner, parameter position, and contract type after bucket lookup, so
hash collisions cannot change a diagnostic or accepted program; the change only removes the
whole-program scan on cache misses.

The candidate passed Stage0 bootstrap, the full differential corpus (`143 agreed, 0 diverged,
0 xfail, 3 skipped`), the proof test matrix including O2/O3 optimized replay, and dogfood ending
with `dogfood audit passed: formalized layers are replay-complete`. A clean 544 product then
repeated the differential corpus before installation. The live compiler checkout retains one
unrelated installer-script edit, which was not committed. The monolithic full-source self-audit
remains open and bounded; this performance change is not presented as a completed self-proof.

## Bounded full-source rerun after contract lookup index (2026-09-19)

With the proof build pinned to `54472098`, the guarded `src/main.elisa` audit was rerun under the
same 180-second and 1,500,000 KiB limits. It again stopped at the time limit without a partial
JSON report, so it remains incomplete and produces no proof verdict. Peak RSS was 673,952 KiB,
down from 859,440 KiB at the preceding `763d9f22` baseline. This is measurable resource
improvement, but the retained whole-program scheduling wall still requires decomposition or a
longer bounded audit before the full self-audit can be considered complete.

## Audit watchdog completion validation (2026-09-19)

The full-source watchdog previously treated any non-null JSON value as a completed report,
without checking the prover's terminal exit status. It now requires a report object with known
verdicts, nonnegative integer counters, consistent replay coverage, and an exit status matching
the verdict. A proved report must have no outstanding obligations, semantic errors, or replay
gaps. This is transport validation; proof validity remains the kernel's responsibility.

Non-finite time limits are rejected, and an exit between polling and RSS sampling is handled as
an ordinary process exit. Seven regression tests cover malformed reports, partial JSON, abnormal
exits after valid JSON, inconsistent counters, replay gaps, timeouts, and invalid limits. The
tests are included in scripts/test.sh. Real watchdog runs preserve both the proved result for
examples/verified.elisa (8 obligations, 8 proven, zero replay gaps) and the failed result for
examples/rejected_underflow.elisa (6 obligations, 4 proven, zero replay gaps). The complete
implementation audit remains unfinished.

## Fresh Stage1 compiler snapshot (2026-09-19)

The proof build pin now resolves to compiler revision `7f84f61f4b019c1be9a4b6c083322e62ce91f848`.
That revision was seeded with the current Stage0 product, installed as a readonly Stage1 snapshot,
and recorded in `~/.elisac/stage1/SNAPSHOT`. The compiler audit merge includes the scoped `Self`
binding fix, unknown nominal-type checking, parser recovery ordering, and parity-harness fixes.

The fresh product passed the 12-case unknown-type parity smoke and the complete compiler/include
struct-layout smoke. The proof suite was green before this pin update; it must be rerun against
this exact snapshot before this checkpoint is considered a full dogfood result.

The Stage0 provenance guard then exposed a stale installed bootstrap binary: `~/.elisac/elisac-stage0`
was still built from `beac948a` while the clean Elisa-core checkout had advanced to `8441c249`.
Stage0 was rebuilt with `vcs.modified=false`, the provenance pin was advanced to the exact full
revision, and Stage1 was reseeded from that Stage0 before dogfood was retried.

## Full-source scalability checkpoint (2026-09-19)

Dogfood completed under the fresh Stage0/Stage1 pair, but the monolithic audit of `src/main.elisa`
did not produce a report. The standard 180-second watchdog run reached 869,072 KiB RSS and timed
out with no partial JSON. A second bounded run with a 600-second time limit reached the 1,500,000
KiB RSS limit after 193.74 seconds, again before report emission. The watchdog classified both runs
as incomplete (exit 3), never as proof success.

A short macOS `sample` capture during a 2,000,000 KiB / 60-second diagnostic run showed the hot
paths were allocator churn (`arena_take_free_block`, `arena_reclaim_allocation`, and
`ctx_aos_store_record`) around repeated semantic analyses, especially mutable-binding, enum-variant,
readonly-function, and type-row lookups. This is the current highest-impact scalability target;
the kernel remains independently replay-complete for the dogfood matrix, while the full self-audit
requires decomposition or memory reduction before it can claim completion.

## Readonly declaration-index correctness checkpoint (2026-09-19)

The compiler pin now advances to `c2922aa2714bfa0263a94b2f315c7372d0544b63`, which keeps the readonly declaration index separate
from the mutable-reference parameter index. The two tables have different lengths and meanings;
using the parameter index for declaration membership could read the wrong row or trap while
compiling the runtime. The corrected implementation hashes each table independently and still
checks the complete name and module-owner pair after bucket lookup.

The compiler was reseeded with the installed Stage0 product, and Stage1 successfully compiled the
canonical runtime support source. The compiler differential corpus reported `143 agreed, 1
diverged, 0 xfail, 3 skipped`; the one divergence is the pre-existing `tuple_function_tail`
parser worktree change and is outside this commit. The proof matrix and dogfood run both passed
against this exact compiler pin; the bounded full-source audit remains incomplete.

## Local-mutability scalability experiment rejected (2026-09-19)

A fresh profile of the bounded full-source audit identified `Semantic.local_binding_is_mutable`
as the largest semantic hot path. Two collision-safe lookup-index prototypes were implemented
and tested in isolated Stage1 worktrees. The larger index reached the 1,500,000 KiB watchdog RSS
limit after 174.83 seconds; the compact head-only version reached the same limit after 106.90
seconds. Both were reverted, because a sound optimization that worsens the resource bound is not
an improvement. The compiler was rebuilt from the reverted source and still passed the runtime
compile and differential corpus (`144 agreed, 0 diverged, 3 skipped`). The full-source audit
therefore remains open, with the original readonly declaration index retained as the only
accepted scalability change in this line of investigation.

## Stage1 self-host formatter crash localization (2026-09-19)

Stage0 successfully lowered the compiler driver source, while both the installed c2922 Stage1
product and a freshly Stage0-seeded Stage1 product terminated with `Trace/BPT` (exit 133) on the
same full self-host input. The reduction showed that Stage1 `ast`, `iface`, and `deps` emissions
complete, individual formatter modules complete, and the failure is reached by the large combined
`src/semantic/semantic.elisa` formatter input. `ELISA_DBG_DECLINE=1` produced no diagnostic, so
this is an internal formatter/backend trap rather than a declared unsupported result. The
constants-only compiler cleanup is independent and passes the Stage0 build plus the differential
corpus; the Stage1 self-host trap remains an open compiler bug and no proof is claimed from it.

The reduction was tightened against the freshly reseeded Stage1 product after the qualified-error
owner fixes. Each of `semantic_api_message.elisa`, `semantic_api_message_2.elisa`,
`semantic_api_message_effects.elisa`, `semantic_api_message_3.elisa`, and
`semantic_api_message_4.elisa` formats successfully under Stage0 but terminates with exit 133
under Stage1, including when each file is compiled directly. The minimal loop/helper construct
extracted from the diagnostic files passes under both products, so the trigger is not that loop
syntax alone. The rebuilt compiler again reports `144 agreed, 0 diverged, 0 xfail, 3 skipped` on
the differential corpus. This remains a reproducible Stage1 formatter defect, not a proof result.
Independent Stage1 probes containing 70-arm enum `when` expressions, 70-arm statement `match`
expressions, and interpolated strings all passed, narrowing the fault away from those constructs
in isolation.

## Kernel validation workspace reuse checkpoint (2026-09-19)

Source proposition admission now reuses one fail-closed replay validation workspace per function
instead of allocating a fresh graph-validation scratch workspace for every proposition. The
workspace is cleared and reinitialized by the kernel validator on every call; no validity bit or
admission result is carried across propositions. The proof suite, native admission harness, O2/O3
replay checks, and accepted/rejected proof matrix all pass after the change.

The bounded full-source audit remains incomplete, but the resource effect is material: the 180-second
watchdog peak fell from 1,089,344 KiB to 362,496 KiB. A 300-second run reached only 624,816 KiB and
still timed out without a report, so this is not promoted to a self-proof. A one-minute sample of
the reduced-memory binary moved the dominant CPU path into parser protocol-parameter lowering,
especially `Parser.protocol_parameter_bound`; that is the next compiler scalability target.

## Compiler generic-bound marker constants (2026-09-19)

The Stage1 parser's high-bit encoding for generic-bound metadata is now named
`Parser::GENERIC_PARAM_BOUND_FLAG` instead of repeating the raw `2147483648` value across parser
modules. The committed compiler revision is `57e78b70`; the installed Stage1 snapshot and
`ELISA_COMPILER_REV` are aligned to that revision. Stage1 was reseeded from the current Stage0,
then the compiler checks passed: 514/514 native differential checks, 356/356 LLVM verifier checks,
and the match-arm regression smoke. The proof build passed its 7 Python tests, optimized replay at
O2/O3, and accepted/rejected proof matrix. The full-source proof audit remains open.

## Protocol-bound parser annotation index (2026-09-19)

`Parser.protocol_parameter_bound` now uses sparse source-order indices for protocol declarations
and wildcard `using` annotations instead of repeatedly scanning unrelated annotation metadata.
The complete annotation table remains authoritative and the lookup retains its source-order scan
fallback, so the index is an optimization rather than a trust boundary. Compiler revision
`c38c22bb` is installed and pinned in `ELISA_COMPILER_REV`. Compiler validation passed 514/514
native differential checks, 356/356 LLVM verifier checks, and the match-arm regression. The proof
build passed its 7 Python tests, optimized replay at O2/O3, and accepted/rejected matrix. The
full-source audit remains open.

## Readonly contract cache locality (2026-09-19)

The compiler's `Semantic.mutable_ref_param_type` cache now searches newest entries first. Cache
entries remain fully checked by callee, owner, and argument position, so the change cannot create a
false cache hit; it only improves locality for repeated calls during recursive declaration walks.
Compiler revision `71fe42e3` is installed and pinned in `ELISA_COMPILER_REV`. The mutability and
mutable-reference regression smokes pass, followed by the proof suite, O2/O3 replay, and proof
matrix. A bounded 60-second full-source audit remained incomplete but reached 701,344 KiB peak RSS,
down from the preceding 1,090,160 KiB sample; this is a performance checkpoint, not a completed
self-proof.

## Private-access semantic index reuse (2026-09-19)

The compiler's private-member checker now uses its existing collision-safe symbol and module-member
hash chains for `pma_has_global_value`, `pma_module_owns`, and unqualified-owner traversal. Each
candidate still undergoes the original exact string and ownership checks; the index only narrows
the rows visited. Compiler revision `85633e21` is installed and pinned in `ELISA_COMPILER_REV`.
Private-visibility, private-field, and mutable-reference smokes pass, as do the proof suite, O2/O3
replay, and proof matrix. The authoritative 180-second full-source audit still timed out without a
report at 1,583,984 KiB peak RSS, so the full self-audit remains incomplete.

## Unsafe capability traversal through nested expressions (2026-09-19)

The unsafe report previously missed calls in expression-form match/catch arms, value blocks,
and recovery bodies. Stage1 now traverses those expression and statement subtrees, including arm
guards, while preserving trusted/static bookkeeping. Stage0's permission inference had the same
soundness gap: match guards and nested value-block/recovery bodies were omitted from the
function effect closure. The Stage0 fix is committed as `90228b6f`; the Stage1 mirror is
`e26ddaf8`, installed and pinned in `ELISA_COMPILER_REV`. The focused Stage0 regression passes,
the unsafe report for `guarded_optional_match_value.elisa` now includes `validate:
Unsafe.RawExtern`, and cross-stage unsafe parity passes with 155 byte-identical reports and zero
divergences. The proof build passes its 7 tests, optimized replay at O2/O3, and accepted/rejected
proof matrix. The independent permission model reports no over-claims; its remaining misses are
conservative incompleteness and do not support a proof claim.

## Typed character constants and magic-number cleanup (2026-09-19)

The proof runtime now names its POSIX descriptors, syscall failure value, ASCII digit bounds,
JSON byte base, control-byte limit, and signed minimum instead of embedding those ABI/protocol
values at use sites. This exposed a Stage1 backend defect: `CharLit` was absent from integer
constant folding, so `const ZERO: u8 = '0'.u8()` remained unresolved and any reader declined.
Stage1 now folds character literals as integer code units; compiler revision `15c54315` is
installed and pinned in `ELISA_COMPILER_REV`, with a dedicated `global_char_const` regression.
Compiler validation passed 514/514 native checks and 357 valid LLVM modules. The proof build passed
7 tests, optimized O2/O3 replay, and the accepted/rejected proof matrix.

The latest 60-second full-source audit remains incomplete: the proof process was watchdog-stopped
before emitting JSON at 60.1 seconds, with a 1,092,560 KiB peak RSS. This is recorded as an audit
limitation, not as a proof result.

## Stage1 interpolated-f-string formatter trap (2026-09-19)

The compiler audit reproduced a Stage1-only `Trace/BPT` on valid interpolated f-strings such as
`f"{x}"`; Stage0 formatted the same source as `__fstr(x)`. The same trap affected three of the
split semantic diagnostic modules (`semantic_api_message`, `_3`, and `_4`), which had hidden the
bug in the full self-hosting input. Stage1's formatter handled only literal synthetic f-strings
and sent interpolated synthetic `__fstr` nodes through ordinary call/source-token recovery.

Stage1 now formats every synthetic f-string directly, handling identifiers and literal chunks
without consulting their synthetic source positions. The compiler regression fixture
`test/repro/fmt_interpolated_fstring.elisa` is byte-identical between Stage0 and Stage1, all five
previously tested semantic API modules now format successfully under Stage1, and the formatter
parity gate improved from the ratchet baseline of 173 to 175 byte-identical fixtures. Compiler
revision `a7bd3b31` is installed and pinned in `ELISA_COMPILER_REV`. The proof suite, optimized
replay, and accepted/rejected matrix pass against this pin. The full-source proof audit remains
incomplete.
## Abstract-effect annotation row constants (2026-09-19)

The abstract-effect semantic checker now names every parser-generated annotation row
used by its validation logic. The values are unchanged; this removes raw row IDs from
the control flow and makes future parser-row changes auditable. The proof build is pinned
to compiler revision `e5a637c5`, which contains the change.

The preserves/changes checker received the same treatment for its whole-change,
preserves-root, and preserves-field annotation rows. Values and source-order pairing
are unchanged; the proof build is now pinned to `01cd427b`.

The effect-law fulfillment checker likewise names its forbids/includes, law-marker,
subject, frame-law, and non-reference rows. Values and law-edge ordering are unchanged;
the proof build is now pinned to `704dc60d`.

The full-source audit identified a scalability hotspot in abstract-effect installation
collection: every `can` block rescanned the complete annotation table to find its handler
and installed effect. The collector now builds source-order filtered installation rows
once and passes them through the recursive walk. Handler target and realization lookups
still use the complete table, so this changes lookup cost without changing resolution
semantics. The compiler change is `34cf4003`, and the proof build is pinned to it.

A live profile then found `Parser.record_generic_func_metadata` rescanning all prior
generic rows and annotations for every function. It now walks the current declaration's
tail rows, retaining the same ordinary-generic/bound-row distinction and stopping at the
current function marker for errorset metadata. Compiler `emit_fmt` parity remains 175/175;
the proof build is pinned to `380b0aec`.

The next profile found `Semantic.enum_variant_count` recursively traversing all later
declarations after its first matching enum, despite its prior `result == 0` guard. It now
returns at that same first match. The compiler passed 175/175 formatter parity and the
proof build is pinned to `621f5511`.

The full-source profile then identified `local_binding_is_mutable` doing two passes over
both its filtered annotation stream and compact side tables. These are now single passes
that retain exact-offset precedence and line-only fallback behavior. Compiler parity is
175/175 and the proof build is pinned to `ea56e16d`.

The next profile showed `concrete_effect_wrapper_line` scanning the same annotation table
twice for `__effect_param` and `__permission_param_decl`. It now performs one complete
pass and returns the same conjunction. Compiler parity is 175/175 and the proof build is
pinned to `94ab4e8c`.

That one-pass rewrite was rejected after a live profile: it removed two early-exit reverse
scans but replaced them with one full-table scan, rising to 906 samples in the hot path.
It was reverted in compiler `42bd57aa`; the proof build is pinned to that restored
early-exit implementation. This is a measured negative result, not a retained optimization.

The next profile isolated repeated module-provenance scans inside
`callable_error_family`. The try/fallible pass now builds source-order `__fn_module` rows
once and uses them for scope checks, while retaining the complete annotation table for
candidate error rows. Compiler `emit_fmt` parity remains 175/175; the proof build is
pinned to `638b4588`.

The same module-row table is now threaded through errorset-wrapper return checking and
its recursive declaration/body walk, so both call sites of `callable_error_family` avoid
rebuilding or rescanning provenance metadata. Compiler parity remains 175/175; the proof
build is pinned to `cdea329b`.

After that index removed `callable_error_family` from the top profile, the next hotspot was
the wrapper's two reverse marker scans. They are now one reverse pass with the same boolean
result and an early stop once both markers are found. Compiler parity remains 175/175; the
proof build is pinned to `e8734a40`.

The semantic consumers for permission-include rows and enum-parent rows now use named
constants instead of raw parser sentinel values. The enum hierarchy recursion limit is also
named explicitly. Values and behavior are unchanged. Compiler parity remains 175/175, and
the proof build is pinned to compiler revision `be983362`.

Replay resource-path composition and record-update typing now consume the kernel core's named
depth-limit constants instead of repeating `128` and `127` in contracts and guards. The
strict boundary is unchanged, and the proof suite, optimized replay, and accepted/rejected
matrix pass against the same compiler pin.

The proof frame annotation index now names all compiler metadata rows it consumes (whole
changes, changed roots/fields, preserved roots/fields, and the dotted-field fallback), rather
than embedding the sentinel numbers in matching logic. Row values and source-order behavior
are unchanged; the proof suite, optimized replay, and accepted/rejected matrix remain green.

The remaining resource-model depth guards and contracts now use the same kernel replay depth
constants throughout the file. This removes duplicated `127`/`128` bounds without changing
the fail-closed limit; all proof and replay regression gates remain green.

Proposition formation and proposition typing now name their recursive depth contracts and the
deliberately tighter call/argument entry guards. The constants preserve each prior boundary,
including the one-level headroom used by recursive calls; the complete proof regression suite
and optimized replay remain green.

The compiler's try/fallible semantic pass now builds a source-order hash-chain index for only
the callee owners appearing in `try` rows. The index retains each original annotation row, so
module provenance, first-family fallback, and no-provenance fallback semantics are unchanged;
the old full-table helpers remain available for compatibility paths. Stage0/Stage1 qualified
error-set parity passed 11/11 cases, the try-fallback-void smoke passed with zero false
positives, and the proof build is pinned to compiler revision `6c3eb2e4`.

The same indexed annotation projection is now threaded through errorset-wrapper return
checking, including its recursive statement/declaration walk and function-reference family
queries. The wrapper's semantics retain the original source-order fallback and module rows;
the proof build is pinned to `f1622a83`, with the qualified error-set parity gate still passing
11/11 cases.

The ungranted-effect checker now builds a per-file concrete-wrapper index once and threads it
through signature and recursive statement coverage checks. This replaces repeated annotation
scans while preserving the prior overload rule that any matching concrete wrapper keeps the
local grant requirement. Stage0/Stage1 unsafe parity passed 156 byte-identical cases with zero
divergences; the proof build is pinned to `8253d214`.

The concrete-wrapper index was tightened to classify effect-parameter and permission-parameter
lines in one annotation pass before attaching function names. This removes the remaining
per-symbol annotation rescans while retaining the same line and overload semantics. Formatted,
unsafe, qualified-error, and try-fallback parity gates all passed; the proof build is pinned to
`d9effdc5`.

The callable-error annotation index now prefilters candidate owners through a hash set while
retaining exact name comparison after the hash match, so collisions cannot change semantics.
Qualified-error and try-fallback parity remain green; the proof build is pinned to `7c4407b6`.

After that pin, a bounded full-source run remained incomplete at the 120-second cutoff, but peak
RSS fell to 1,413,488 KB. Sampling moved the dominant semantic work to private-member access
(`pma_scope_owner` and `pma_selective_imports`); no proof result is claimed from this incomplete
run. The next audit target is therefore the private-access annotation lookup, which must be
indexed without changing module-boundary or shadowing semantics.

The private-access audit then found a stage1 soundness gap: qualified access through a private
`const module` was accepted outside its parent module. The access pass now indexes paired private
member/module annotations and trusts that parser record for qualified visibility, while retaining
exact path and lexical-boundary checks. Const-module visibility, private-state stress (7/7), and
the full differential suite (143 agreed, 0 divergent) pass; the proof build is pinned to
`8534daae`.

The post-fix bounded full-source audit remained incomplete at 120 seconds, with peak RSS
1,560,160 KB. Profiling no longer showed private-member access as the dominant compiler-side
cost; the largest sampled path was trusted kernel replay, especially typed proposition replay and
value-binding lookup. This is the next proof-system optimization target, and this incomplete run
does not count as a proof result.

The replay-bound constants cleanup was tested and reverted. Although the normal proof tests stayed
green, the self-hosted standalone audit lost verification for two required replay declarations;
restoring the original literals returned the full coverage gate. Commits `b0b1bed` and
`2de298b` preserve that experiment and explicit rollback, so the trusted baseline remains
reproducible rather than silently accepting a coverage regression.

The replay audit then centralized shared depth, signed-integer, machine-width, and shift-limit
constants across the trusted kernel. Commits `ccdaea5`, `c7ca581`, `efdc3be`, `b911360`,
`6af867c`, `b89e330`, and `48ffc59` preserve those changes. The full stage1 matrix, standalone
coverage gate, and O2/O3 replay checks remained green after each cluster. A bounded full-source
audit on the current baseline was still incomplete at the 120-second cutoff, but its peak RSS
was 572,816 KB and it emitted no partial report; this establishes no full-source proof result.

Structural replay now rejects an empty `structural-safety` trace explicitly, with the native
kernel adversarial suite covering that case. Arena-shape admission already required a non-empty
edge list, so the guard is defense in depth; the complete proof matrix and optimized replay
remain green. This hardening is recorded in `3472f65`.

The proof traversal-depth cleanup names the remaining import, source-operator, unconditional-call,
and runtime-witness bounds instead of embedding policy numbers in trusted checks. The current
stage1 build compiled these changes; the full stage1 proof matrix, O2/O3 replay checks, and
accepted/rejected matrix passed. The watchdog harness also passed all seven transport and
malformed-report tests on rerun.

The stage0 oracle was rebuilt from the clean canonical Elisa-core checkout at revision
`90228b6f` and its embedded VCS revision was verified before use. `ELISA_STAGE0_REV` now pins
that verified revision. The complete dogfood suite passed, including all stage0 bootstrap
harnesses, independent replay checks, tactic certificates, forged-certificate rejection, and
the final replay-complete audit summary. No stale or unverifiable stage0 binary is accepted by
the provenance guard.

The remaining proposition-typing headroom constants are now derived from the shared replay depth
limit rather than carrying independent `122`--`126` literals. This preserves the exact recursive
entry margins while making a future bound change atomic. The stage1 build, complete proof matrix,
and O2/O3 optimized replay checks pass with the derived values.

The compiler's callable-error target projection was then optimized with a collision-safe hash
chain, preserving exact owner-name comparisons while removing repeated linear target membership
scans. Compiler qualified-error parity remained 11/11 and try-fallback-void remained free of
false positives. The proof frontend was repinned to compiler commit `1c9c767f`; its complete
stage1 test matrix and O2/O3 replay checks passed. A fresh full-source audit profile no longer
showed `callable_error_index_build` among the hot paths, but still stopped at the 4,000,000 KB
RSS ceiling after 122.06 seconds without a report. The next compiler-side audit targets are
the newly dominant semantic walkers, especially catch classification and positional construction.

The compiler then reused the semantic `SymbolTable.catch_match_lines` index in catch subset
classification instead of rescanning all annotations for each match. Compiler qualified-error,
try-fallback, and catch-exhaustiveness parity stayed green, and the proof matrix plus optimized
replay remained green under stage1 `7e6dde06`. A 180-second full-source run still reached the
4,000,000 KB RSS ceiling at 142.48 seconds without a report; this optimization is therefore
validated for semantic preservation but does not close the whole-source resource boundary.

The compiler then replaced positional-constructor struct classification's repeated full symbol
table scan with the existing collision-safe symbol-name hash chain, retaining exact name and kind
checks. Qualified-error parity remained 11/11, try-fallback-void remained free of false positives,
and catch-exhaustiveness parity passed. The proof frontend is pinned to stage1 compiler commit
`41d1e229`; the proof rebuild, seven audit harnesses, complete proof matrix, O2/O3 optimized replay,
and accepted/rejected matrix all passed. This is a targeted compiler optimization only; the bounded
full-source audit remains incomplete and is not represented as a full proof result.

The exact pinned state was then run through the complete dogfood suite. All proof fixtures,
stage0 bootstrap harnesses, kernel runtime adversarial checks, tactic scripts, nested branch and
quantifier certificates, stale/forged certificate rejection, and the final replay-complete audit
summary passed under stage1 `41d1e229`.

The typestate sentinel audit then named the parser and semantic metadata constants separately.
The first stage1 provenance build intentionally caught a private cross-module name collision;
parser-specific names fixed it before installation. The corrected compiler self-hosted from stage0
at `22e30e1e`, the linear-typestate stage0/stage1 regression passed, and the proof build, seven
audit harnesses, complete matrix, optimized replay, and accepted/rejected matrix passed under the
new snapshot. The failed intermediate build was not installed or pinned.

The next compiler hotspot was `Semantic.enum_variant_count`, which repeatedly traversed the full
declaration tree during enum-index checking. The checker now reuses the declaration-order cache
from `enum_tag_declaration_index`, preserving first-positive-match behavior for nested duplicate
names and empty enums. Stage0/stage1 native differential testing passed all 514/514 checks, and
the proof build, seven audit harnesses, complete matrix, O2/O3 replay, and accepted/rejected
matrix passed under stage1 `94498709`. A bounded full-source run at a 2,000,000 KiB RSS ceiling
remained incomplete after 148.05 seconds without a JSON report; it is not a proof result.

The subsequent profile identified `Semantic.find_symbol` as another repeated full-symbol scan.
It now walks the existing collision-safe symbol hash chain while retaining insertion order and
exact-name checks. The full stage0/stage1 native differential gate passed 514/514 checks, and the
proof build, seven audit harnesses, complete matrix, O2/O3 replay, and accepted/rejected matrix
passed under stage1 `187a33ef`.

The next indexed lookup replaced `struct_is_declared`'s repeated declaration-tree scan with the
symbol hash chain and an exact `SymbolKind.Struct` check. The compiler self-hosted from stage0;
resolver smoke passed, including whole-program self-resolution across 525 frontend files with
zero unresolved references. The proof build, seven audit harnesses, complete matrix, O2/O3 replay,
and accepted/rejected matrix passed under stage1 `65842568`.

The following semantic scan was `named_struct_target`, which walked every registered struct field
row for each primitive-to-struct compatibility check. It now uses the symbol index with an exact
`SymbolKind.Struct` check. Stage0/stage1 compiler diagnostics parity passed all 360/360 fixtures,
including the named-type positive and negative cases. The proof build, seven audit harnesses,
complete matrix, O2/O3 replay, and accepted/rejected matrix passed under stage1 `44a9cf62`.

The mutability audit then moved the exact local-binding side-table lookup ahead of the filtered
annotation fallback in `local_binding_is_mutable`. Partial-table recovery and loop-header handling
remain intact. Compiler diagnostics parity passed all 360/360 fixtures, and the proof build, seven
audit harnesses, complete matrix, O2/O3 replay, and accepted/rejected matrix passed under stage1
`5d81c620`.

The exact pinned state then passed the complete dogfood suite: proof fixtures, stage0 bootstrap
harnesses, kernel runtime adversarial checks, tactic scripts, nested branch and quantifier
certificates, stale/forged certificate rejection, and the final replay-complete audit summary.

The kernel-identity fingerprint path was hardened to fail closed for unknown node kinds. The
first implementation deliberately changed the wildcard to rejection, and the existing tactic
script regression immediately exposed that several legitimate resource, effect, structural,
and unsupported nodes are source-neutral atomic roots. Those recognized kinds are now enumerated
explicitly and retain their scalar identity encoding; only an unrecognized future kind invalidates
the identity. Kernel replay remains authoritative, while the fingerprint protocol can no longer
silently bless a malformed or future node kind. The stage1 build, seven audit harnesses, complete
proof matrix, optimized O2/O3 replay, accepted/rejected matrix, and full dogfood suite all pass.

The live full-source profile was sampled before the next optimization decision. It confirmed that
the dominant remaining cost is compiler semantic processing rather than trusted replay: arena
allocation was hottest, followed by `Semantic.mutable_ref_param_type`, local mutability, extern
parameter/protocol scans, and struct-field lookup. No semantic lookup was changed speculatively.
As a separate maintainability hardening, unsigned-width maxima and width identifiers were named in
the kernel core and reused by both producer and replay; the boolean-fold and unsigned-term/place
depth bounds were named at their owning layers. Values and fail-closed boundaries are unchanged.
The stage1 build, seven audit harnesses, complete proof matrix, O2/O3 replay, accepted/rejected
matrix, and complete dogfood suite—including stage0 bootstrap and adversarial replay checks—pass.

The compiler full-source profile's struct-field lookup hotspot was addressed in compiler commit
`a160013a`: `struct_field_row_for_type` now makes one pass while retaining the prior exact
precedence of current-module row, top-level row, then an unambiguous external row. A first attempt
to index the readonly mutable-reference query cache was rejected by stage0's value-block mutation
rules and fully removed; no unbuilt compiler source was retained. The optimized compiler
self-hosted from the canonical stage0. Native backend differential passed 514/514, diagnostic
line parity passed 364/364, and the field-type and module-field-mutability smokes passed. The proof
frontend is pinned to `a160013a`; after installing a matching stage1 snapshot, its build, seven
audit harnesses, complete proof matrix, O2/O3 replay, accepted/rejected matrix, and complete
dogfood suite passed.

The next cleanup names shared semantic recursion and difference-graph node limits, reuses the
kernel replay depth bound for resource-place walks, and encodes resource-event flags through their
existing constants instead of repeating raw bit values. The arithmetic postcondition for
`depth_valid` remains literal because the source checker does not yet unfold module constants in
postconditions; changing it to the constant made the kernel's own contract unprovable, so no
weaker proof was substituted. The proof frontend is pinned to `66b8ed02`; the stage1 build,
seven audit harnesses, complete proof matrix, O2/O3 replay, accepted/rejected matrix, and full
dogfood suite pass at that revision.

Full-source profiling then found repeated scans of compiler-owned operator implementation
annotations in scalar-witness construction. A report-local lookup cache now groups exact impl/scope
rows by source line after verifying annotation order; non-monotone input or an index expansion
larger than the source annotation table invalidates the cache and retains the original scan. The
operator-index record is in a separate model file included before the report definition, and both
standalone Elisa runtime harnesses include it explicitly. The complete proof matrix and dogfood
suite pass, including stage0 adversarial replay harnesses. Bounded full-source runs remain
incomplete: the pre-index 45-second run reached 1,326,576 KB RSS without a report; a post-index
60-second run reached 1,037,568 KB, while a longer 90-second run reached the 1,500,000 KB RSS
watchdog at 82 seconds. A new sample shows typed proposition replay and repeated type/value
binding lookup as the current hot path, so full self-verification is still an open goal.

Typed proposition replay now builds a compact table of only value/proposition binding positions,
so identifier typing no longer scans unrelated type, field, and declaration rows. Lookup still
compares exact source names and rejects conflicting duplicate evidence. A hash-table variant was
discarded because stage1 declined `sview_len` in the standalone AST-free kernel module; the compact
index preserves that module boundary without changing compiler code. The stage1 build, source
length check, full proof matrix (including O2/O3 replay), and complete dogfood suite passed. A
bounded full-source rerun remained incomplete at 60.08 seconds and 1,376,096 KB RSS under the
1,500,000 KB ceiling. This single run does not demonstrate a measurable full-audit speedup; typed
replay and full self-verification remain open performance work.

A follow-up trusted-kernel review restored an explicit fail-closed category check at the compact
lookup boundary: every indexed row must still be a `value` or `proposition`, matching the former
full-scan predicate rather than relying solely on the private index builder. The check uses Elisa
pattern matching. Stage1 build, source-length check, full proof matrix, and complete dogfood suite
passed, including stage0 bootstrap replay harnesses.

The profiler's first function-trace run timed out before any function completed, but its active
stack at 180 seconds was in typed proposition replay, ending in
`proof_kernel_replay_find_function_parameter_by_index`. The replay lookup index now also retains
function-parameter row positions, while preserving exact owner/signature/index or name matching
and the original ambiguous-duplicate rejection. A native kernel fixture checks both rejection of
a duplicate parameter slot and acceptance of the unique signature under Stage0 and Stage1. The
full proof matrix (O0/O2/O3) and complete dogfood suite passed.

The profiler's 60-second sample-mode capture against the immutable `66b8ed02` source snapshot
produced 35,218 stack samples before the target timed out; capture quality is explicitly partial,
so it is diagnostic only. The hottest sampled leaves were `arena_realloc` (8,345 samples),
`arena_take_free_block` (3,017), `note_local_type` (1,974), `new_region_with_owner` (1,957), and
`annotation_type_id` (1,944); most early samples were compiler semantic checking. The live
compiler checkout changed during an initial profile attempt, so that capture was discarded and
the pinned installed Stage1 binary/runtime were used against the immutable source snapshot.
Repeated 60-second full-source audit runs remain incomplete: the run after the value-only index
used 1,376,096 KB RSS, and the run after the parameter index used 1,406,288 KB. These do not
establish a performance improvement; full-source self-verification and reduction of the semantic/
allocation cost remain open.

The compact typed-replay index now appends only the value/proposition and function-parameter
positions it actually stores, rather than sizing both arrays to the entire binding environment.
This preserves exact lookup order and duplicate rejection while removing guaranteed unused slots.
The existing full test matrix and dogfood suite passed. Full-source measurements remain noisy and
incomplete: a 180-second/3,000,000-KiB run stopped at the time limit with a 1,606,048-KiB peak;
another 180-second/2,000,000-KiB run hit its RSS limit at 102.62 seconds and 2,000,416 KiB.
Neither emitted a report.

A 10-second native sample during the subsequent pre-enum-index 180-second/3,000,000-KiB run showed
late proof work repeatedly scanning nested declarations in `proof_declaration_has_enum`. That query
now uses a separate compact per-import enum-name index, rather than retaining enum AST payloads in
the float-audit type index. Lookups check both the stored hash and exact enum name. An incomplete
index declines structural classification rather than inferring it from partial data. Stage1 build,
the O0/O2/O3 proof matrix, and complete dogfood—including Stage0 kernel bootstrap and adversarial
certificate tests—passed. A same-limit full-source rerun on this implementation stopped at
170.89 seconds after reaching the 3,000,000-KiB RSS watchdog (peak 3,001,776 KiB), before emitting
a report. Samples during that run showed repeated scans of `__tuple_label` annotations in
`proof_source_kernel_collect_tuple_fields`. Those annotations are now grouped in a collision-safe
per-import line index; each line's labels preserve their original order, and incomplete indexes
fail closed before any tuple field can enter the typing environment. The full matrix and dogfood
suite passed again. A same-limit 180-second rerun now stops on time instead of memory, with a
2,260,464-KiB peak; this is lower peak memory but still no full-source report. A five-minute
run later reached the 3,000,000-KiB RSS watchdog at 270.20 seconds (3,005,136-KiB peak). Late
samples showed `proof_builtin_operator_impl_exists` dominating repeated lookups. The report's
cached implementation rows now have a collision-safe pair hash index; exact concrete/protocol
strings remain authoritative, and extension rows retain their wildcard-protocol behavior. A
subsequent full-source attempt was interrupted after profiling showed the old query still active.
The cause was that included files restart annotation line numbers, invalidating a cache that
assumed globally ordered annotations. The builder now pairs implementation/scope rows by exact
line independent of order. The full O0/O2/O3 matrix and dogfood suite passed after this correction;
a fresh whole-source run is still needed. The next run reached the RSS watchdog at 175.46 seconds
(3,027,552-KiB peak); its sample showed the separate source-operator guard still repeating generic
annotation scans for every primitive spelling, so the report index did not cover that path. That
guard now scans source annotations once per check while preserving extension and exact-line impl
semantics. The full O0/O2/O3 matrix and complete dogfood suite passed after the change. The current
whole-source attempt still stopped at the 3,000,000-KiB RSS watchdog after 172.68 seconds (peak
3,000,336 KiB); samples no longer show repeated operator-annotation scans and instead show
`proof_check_function`/return-contract matching and arena allocation. Self-verification remains
incomplete; the next experiment is a larger bounded memory allowance to determine whether this is
only resource headroom or another repeated-work bottleneck.

## Source-operator guard reuse and larger self-audit (2026-09-20)

A fresh 300-second/6,000,000-KiB whole-source run on the current stage1-built binary stopped at
the time limit without emitting a report (peak 4,366,768 KiB). Sampling at 1:54 showed repeated
`proof_source_primitive_operator_overloaded` scans in return-contract checking. The arithmetic goal
walker now computes the exact primitive protocol policy once at its top-level entry and carries a
scalar bitmask through recursive checks, rather than rescanning source annotations at every nested
goal. The mask is derived by the prior authoritative extension and exact same-line implementation/
scope scan; named constants define every protocol bit. The source-bound tactic path retains the
same exact semantics. Stage1 build, the complete O0/O2/O3 proof matrix, and dogfood—including
stage0 adversarial replay harnesses—passed. A second 300-second/6,000,000-KiB whole-source run
still emitted no report (peak 4,655,328 KiB). Its 49-second sample showed typed proposition replay;
a later sample showed `proof_check_return_contracts` and arena allocation. These bounded runs do
not establish a completed self-proof or an overall full-source performance gain. Self-verification
remains open.

## Typed function-parameter lookup index (2026-09-20)

After source-operator policy reuse, a fresh whole-source profile showed typed replay repeatedly
searching every function-parameter binding for each call argument. The typing index now buckets
parameter positions by the existing signature identity. That value selects a bucket only: every
candidate still requires exact function owner, signature identity, and parameter index/name
matching, and duplicate matches remain ambiguous and rejected. Bucket chains are built only from
validated indexed rows, and index construction consumes the same bounded replay work budget.
The existing proposition-admission runtime fixture checks both rejection of duplicate parameter
indices and acceptance of a unique parameter signature; it passed under stage1 and in the stage0
bootstrap harness. The complete stage1 proof matrix, O2/O3 replay checks, and dogfood suite passed.

At 39 seconds, the full-source sample showed `proof_kernel_replay_build_typing_index` and typed
environment validation but no parameter-lookup function in its leading stacks; a 2:39 sample again
showed return-contract checking rather than parameter lookup. The 300-second/6,000,000-KiB
self-audit still emitted no report, but peak RSS was 3,869,504 KiB, compared with 4,655,328 KiB on
the immediately preceding bounded run. This is encouraging measured evidence, not proof that this
single index caused the entire RSS difference; the full-source proof remains incomplete.

## Compiler provenance and executable harness dependencies (2026-09-20)

The compiler's generic type-parameter field-access checker had collected names from every nested
branch function-wide, suppressing diagnostics after a branch-local shadow. Its replacement follows
the lexical scope of active locals, branch conditions, loop variables, pattern binders, and nested
expression blocks, and traverses every value-bearing expression form. Stage0/Stage1 differential
fixtures reject a post-branch or post-match generic field access, reject one nested in an array
literal, retain a valid branch-local struct field access, and reject field access through a
primitive reference. The compiler change is committed as `a51f3dd7`; its rebuilt Stage1 product
and installed snapshot both identify that revision.

`ELISA_COMPILER_REV` now pins the proof importer to `a51f3dd7`. The standalone tactic and lemma
summary replay harnesses now include `proof/model/enum_index.elisa` before `model.elisa`, matching
the production import graph. With the matching Stage1 product and source snapshot, the complete
proof test matrix passed, including O2/O3 independent replay. The full dogfood suite also reached
its final “formalized layers are replay-complete” result, including Stage0 kernel bootstrap tests.
The bounded complete-source self-audit remains a separate unfinished requirement; these gates do
not establish that the proof assistant verifies its entire implementation.

## Report-scoped operator policy reuse (2026-09-20)

The preceding source-operator mask was still rebuilt for every top-level certified goal and every
runtime assertion/guard. `ProofReport` now stores the exact mask once after copying the current
compiler annotations, and report reset clears it before another source is checked. Certificate
construction and runtime-fact admission use that report-scoped value; the standalone goal API
continues deriving a mask from its explicit annotations. Stage1 build, the complete proof matrix,
O2/O3 replay checks, and the stage0/stage1 dogfood suites passed. A fresh 300-second/6,000,000-KiB
whole-source run still emitted no report (peak 4,176,448 KiB). Samples no longer show annotation
matching among leading stacks; return matching, expression validation, and arena allocation/reclaim
dominate instead. This confirms the targeted repeated lookup is gone, not a whole-run speedup or a
completed self-proof.

## Fuse typing-environment validation with index construction (2026-09-20)

The installed Stage1 snapshot and compiler source were checked before profiling: both identify
`a51f3dd7`, its build manifest passed freshness and artifact-hash validation, and the profiler
doctor passed every check. A 120-second sample-mode whole-source audit timed out after collecting
72,935 samples (peak RSS 1,160,790,016 bytes); its largest proof-code leaf was
`proof_kernel_replay_build_typing_index`. Typed proposition admission had validated the complete
environment, then scanned it again to construct the compact lookup index. Index construction now
validates every row—including rows it does not index—during its existing scan, and the redundant
validation pass was removed. The malformed non-indexed field-row fixture remains in the hostile
environment tests and passed, as did the full Stage1 build, proof matrix with O2/O3 independent
replay, and complete dogfood suite including Stage0 bootstrap.

A same-limit sample after the change timed out after 90,116 samples, with 4,066,213,888 bytes peak
RSS. The active stack had advanced from proposition formation/index construction to return-contract
checking; the separate `proof_kernel_replay_typing_binding_valid` leaf fell from 5,008 samples to
1,930 while index construction rose from 9,852 to 17,949 samples. These are partial, phase-sensitive
samples, not a controlled throughput benchmark or proof of overall speedup. The whole-source audit
still did not produce a report. The next high-impact work remains reducing repeated proof checking
and allocation enough for self-verification to complete, without weakening any admission checks.

The same post-change profile identified declaration-alias resolution as a frequent leaf during
return/type checking. The checker now uses its existing bounded per-import type-audit index for
alias resolution in unsigned-width and scalar-type classification, including function returns,
parameters, locals, and return-local analysis. The hash is only a bucket selector; every candidate
is matched by exact alias name, duplicates remain ambiguous, and incomplete or malformed bucket
chains return the existing conservative unsupported result. No declarations or classifications are
cached across imports. Stage1 build, the full proof matrix with O2/O3 replay, and full dogfood
(including Stage0 bootstrap, integer/unsigned aliases, rejected floating aliases, and malformed
proposition environments) passed. This change has not yet had a post-change whole-source profile;
no measured speedup is claimed.

The post-change 120-second sample did time out, but its phase progressed into resource-event
checking after 85,543 samples (peak RSS 2,449,702,912 bytes). The active stack no longer contained
type-alias resolution; the `proof_find_type_alias` leaf count was 2,984 compared with 11,913 in
the immediately preceding partial sample, while the largest leaf shifted to
`proof_kernel_replay_build_typing_index` at 23,965. Because samples are phase-sensitive and only
one run was collected at each revision, this is evidence that the targeted lookup is less prominent
and the audit advances farther, not a controlled proof of causal throughput/RSS improvement. The
whole-source audit still did not emit a report; repeated index construction is the next profiling
target.

## Reusable typed-index scratch (2026-09-20)

Proposition formation now accepts caller-owned typing scratch for repeated source obligations.
The builder clears all logical entries, revalidates every global and local environment binding,
and rebuilds value/parameter positions and parameter bucket chains on every call. It returns only
success/failure; the temporary index view is formed and consumed inside the checker and is never
returned from the scratch builder. Quantifier-local environments continue using independent
indices so constructing a binder scope cannot mutate the outer environment's active index. A
runtime fixture reuses one workspace across valid, cyclic-arena, recovered, malformed-environment,
and recovered-again checks, guarding against stale scratch becoming admission authority.
The function-parameter index fixture also exercises this path: it rejects duplicate slots for one
signature, then reuses the same workspace with a unique parameter whose signature identity collides
in the bucket selector with an unrelated function. Exact owner/signature/index checks admit the
valid call without admitting the ambiguous one.

The proof frontend pin was advanced from `a51f3dd7` to `010fe325`, matching the installed Stage1
snapshot. The Stage1 build, complete proof matrix including O2/O3 replay, and full dogfood suite
passed; dogfood also compiled and ran the proposition-admission harness under Stage0. The current
profiler doctor passed against the matching Stage1 product and compiler manifest. A 120-second
sample of whole-source verification timed out after 59,741 samples (peak RSS 1,154,826,240 bytes);
its active stack ended at `proof_kernel_replay_build_typing_workspace`. The capture was partial and
the compiler revision changed since the previous sample, so this is diagnostic evidence only—not
a controlled allocation or speedup comparison. No whole-source proof report was emitted; further
optimization and completion of self-verification remain open.

The standalone index builder remains separately allocating. A Stage0 experiment that factored it
through a helper borrowing a locally created workspace was rejected because Stage0 could not infer
the local scratch region; the reusable production path borrows the caller-owned workspace and
returns no scratch-backed view. This bootstrap region-inference limitation remains a compiler
parity investigation, not a proof-system workaround to accept under Stage0.

## Skip unused compiler call-precondition setup (2026-09-20)

The refreshed self-audit diagnostic capture on compiler `010fe325` showed repeated work in
`check_call_precondition_unproven`. Inspection found that the checker computed `skip_func` for
callers whose relational facts it deliberately does not model, but only used that flag to suppress
the final call walk; it still built parameter, bound, and local-constant state for those callers.
Compiler commit `43f7ebed` moves the existing skip to the top of the function branch, before that
setup. This preserves the checker’s existing conservative warning policy and removes work only on
paths whose result was already discarded. A focused fixture checks a relational caller whose fact
matches the callee requirement and a clean caller that must still receive the unproven-precondition
warning. Stage0 and Stage1 produced the same single expected warning; the existing interval endpoint
smoke also passed.

`ELISA_COMPILER_REV` is now pinned to `43f7ebed`, and the committed compiler was rebuilt from the
fresh Stage0 bootstrap and installed as the new Stage1 snapshot. Against that exact Stage1 product,
the complete proof matrix passed, including O2/O3 optimized replay, and full dogfood passed with all
Stage0 kernel bootstrap harnesses. The default installed-snapshot build also succeeded, and the
kernel-core dogfood source proved with 25 replayed certificates and zero gaps. The monolithic
`src/main.elisa` self-audit remains incomplete; these gates do not certify the full assistant, and
no whole-source speedup is claimed from the structural early exit alone.

## Full-source audit and constant postcondition limit (2026-09-20)

A renewed full-source check with the installed Stage1 snapshot was stopped by the explicit memory
watchdog at 2,561,104 KB RSS after 101.71 seconds; no JSON report was emitted. Native macOS stack
samples from the live check show high activity in Elisa semantic-check routines and arena block
allocation, so this still points to compiler/front-end checking as the current whole-source audit
cost center. It is diagnostic evidence, not a completed proof or a controlled benchmark.

While honoring the constants cleanup request, replacing the literal replay-depth guard inside
`depth_valid` with `PROOF_KERNEL_REPLAY_DEPTH_BOUND` caused the kernel-core dogfood fixture to
return `unsupported` (22 replayed certificates). Restoring the literal returned the fixture to
`proved` (25 replayed certificates). The proof checker currently needs the literal in this
contract/body pair; do not replace it until constant unfolding in verified contracts is supported
and the fixture demonstrates equivalence. Other traversal sites continue to use the named replay
limit/bound.

## Instrumented full-source typing profile (2026-09-20)

The installed Elisa Profiler compiled `src/main.elisa` with function tracing using the proof
repository's pinned Stage1 compiler and ran `elisa-proof --json src/main.elisa` in sample mode.
The target hit the 120-second execution cap; the profile is partial and must not be treated as a
completed workload or a performance comparison. It captured 79,103 stack samples and peaked at
1,081,065,472 bytes RSS. Among leaf frames, samples concentrated in
`proof_kernel_replay_typing_binding_valid` (12,395),
`proof_kernel_replay_build_typing_workspace` (11,589), `arena_take_free_block` (10,176),
`arena_realloc` (4,495), `proof_kernel_replay_type_environment_binding_at` (4,191), and
`proof_source_kernel_collect_tuple_fields` (3,469). The dominant nested path builds and validates
the proposition typing workspace while walking source specification contexts. This directs the
next audit item at repeated global type-binding validation/index construction; no soundness-critical
validation has been removed or cached yet.

## Validated source-global typing cache (2026-09-20)

The source proposition-formation path now snapshots and validates declaration-wide typing
bindings once per source check, then reuses their value and function-parameter indexes across
propositions. The cache is held through a module-private opaque type; callers can prepare it only
through the public validating API. Each proposition still validates all local bindings and builds
the combined indexes against the existing typing-work budget. Generic replay APIs are unchanged
and continue validating their complete environment on every call, keeping caching confined to the
trusted source-checking path.

Regression coverage checks source-array mutation after snapshotting, malformed local bindings,
recovery after a failed local check, ambiguous generic environments, and failed cache preparation
not reusing stale authority. The standalone source report no longer traps while using the cache;
it returns its usual unsupported report with 220/220 certificates replayed, zero replay gaps,
and six semantic diagnostics. The complete proof test suite passed, including O2/O3 optimized
replay and accepted/rejected proof fixtures.

The bounded full-source audit was rerun with a 180-second limit and a 2,500,000 KiB RSS ceiling.
It was stopped at the watchdog before emitting a report; the output files are empty. This does
not establish a whole-source performance improvement, and the self-audit remains incomplete.

## Indexed alias checks for global operator witnesses (2026-09-20)

A paired, instrumented sample-mode run on the same pinned Stage1 binary (`43f7ebed`, SHA-256
`655aae4f5606b56abeab8d63d163abaad3420057371c16b319e581e68fe20a5a`) showed repeated
`proof_find_type_alias` scans under `proof_add_primitive_operator_witnesses` while global
constants were imported. The source-wide, collision-safe `ProofTypeAuditIndex` was already built
for this import, but that path did not receive it. The global-constant operator-witness path now
uses the index; exact alias names remain authoritative, and ambiguous, malformed, or incomplete
index state adds an untrusted-operator marker so uncertainty can only decline a proof. The shared
ambiguity sentinel is named `PROOF_TYPE_AUDIT_AMBIGUOUS_COUNT`.

In two single 120-second instrumented captures, `proof_find_type_alias` accounted for 14,496 of
81,793 recorded stack leaves before the change and 703 of 77,931 after it. Peak target RSS was
3,692,625,920 bytes before and 1,326,448,640 bytes after. Both captures timed out without a full
proof report; these phase-sensitive single captures are diagnostic evidence, not a controlled
throughput benchmark or a completed self-audit. The stack-record leaf count for the targeted scan
fell by about 95% in this pair, and observed peak RSS was lower, but no general speedup claim is
made.

The Stage1 build, focused global-constant fixtures (including rejection of an overloaded
primitive equality), full accepted/rejected proof matrix, O2/O3 optimized replay, and full dogfood
passed. Dogfood included the Stage0 bootstrap kernel harnesses and ended with
`audit passed: formalized layers are replay-complete`.

The full-source audit was then tried with a 240-second limit and 4,000,000 KiB RSS ceiling. It
timed out at 240.22 seconds after reaching a 3,260,336 KiB peak, without emitting a report. A
previous run at the same 2,500,000 KiB ceiling reached the watchdog after 157.56 seconds. These
runs show the audit progresses longer under the same memory ceiling and stayed below the larger
ceiling for four minutes, but neither is a completed verification; the full-source self-audit
remains open.

## Reuse validated global function-parameter buckets (2026-09-20)

Profiling the cached source-typing path showed that each proposition still rebuilt the hash
buckets for the same declaration-wide function-parameter rows. The opaque cache now snapshots
those bucket heads and collision chains at the same time it validates global bindings. When local
bindings add no function-parameter rows, replay uses the validated global index directly. If
caller-supplied locals do add such rows, the checker still validates and rebuilds the combined
index; this preserves the public cached API's general behavior rather than relying on source-only
assumptions.

Regression cases exercise both branches: a valid call using cached global function parameters,
and a valid call with function-parameter rows supplied locally. The full proof matrix, O2/O3
optimized replay, full dogfood, and Stage0 bootstrap kernel-admission harness passed.

In two 120-second instrumented captures against the same Stage1 product, the leaf
`proof_kernel_replay_build_typing_workspace_with_globals` fell from 4,123 recorded stacks before
this change to 3 after it (the function appeared in 5 full stacks after the change). Peak RSS fell
from 1,326,448,640 bytes to 687,439,872 bytes. Both captures timed out and their phase/sample
counts differ; these are diagnostic observations, not a controlled performance benchmark.

A subsequent 240-second full-source audit peaked at 609,808 KiB and timed out without a report. A
10-minute attempt also timed out without a report, peaking at 3,063,264 KiB. Neither proves the
whole source; the self-audit remains open despite the reduced repeated-index work.

## Named machine-sized replay bound (2026-09-20)

Removed the literal `128` from `depth_valid`'s postcondition and implementation and from its direct
dogfood caller. The source constant importer and its independent replay validator previously
accepted only immutable `i64` literal constants, so the `usize` replay-depth bound was not available
to executable-summary verification. Both paths now recognize an immutable literal `usize` constant;
replay still independently confirms exact declaration scope, source line, immutability, type, and
initializer value. The importer adds these machine-sized constants only when they occur in a
contract, avoiding unrelated entry facts across the large replay module. Existing `i64` constant
handling is unchanged. Unknown or over-depth expression forms do not trigger an import, which can
only leave a proof unsupported.

The core dogfood proves 25/25 obligations with zero replay gaps. The standalone replay validator
retains its required verified declarations and zero-gap invariant. A new negative fixture checks
that a module-local `usize` constant cannot be replaced by a same-named root constant. The complete
Stage1 test matrix, optimized replay at O2/O3, full dogfood, and all Stage0 bootstrap kernel
harnesses passed. A broader prototype that imported every `usize` constant exhausted control-flow
budgets in large replay functions; that experiment was narrowed before acceptance. No whole-source
self-proof is claimed, and the full-source audit remains open.

The adversarial shadowing checks also found a soundness defect in contract handling: a function
postcondition referring to a global constant could previously be reinterpreted against a same-named
local, allowing a false result to pass. Contracts are now resolved in declaration scope at function
entry and the normalized requires/ensures are retained in the verified function summary, so caller
locals cannot capture a callee's global names. Negative local-shadow and call-boundary fixtures now
confirm these false proofs are rejected, with complete replay and zero gaps. The audit caught this
while adding machine-sized constants; it is included here as a soundness correction, not merely a
constant-import extension.

## Standalone replay self-verification: direct borrowed-name projection (2026-09-20)

`proof_kernel_replay_ident_name` was unverified because it copied a `ProofKernelNode` through the
tuple-returning `proof_kernel_replay_node_at` helper and then returned that copy's `sview` field.
The resource checker could not encode the borrowed-result summary across that aggregate temporary.
After preserving both existing root bounds checks, the function now indexes the already-validated
node directly and returns its `name` field. This keeps the same empty-string behavior for invalid
roots and non-identifier nodes while making the borrow's source place explicit to the verifier.

The standalone source audit now proves and replays this function, and its validator requires that
declaration to remain verified. On the same source, standalone coverage increased from 220 proven
certificates out of 1,546 obligations to 227 out of 1,548, with zero replay gaps in both reports.
The new availability also exposes more downstream region-call obligations, so the broader
self-verification gap remains open; this is not a claim that the replay module is fully proved.

## Standalone replay self-verification: bounded entry-state headroom (2026-09-20)

The standalone report showed that typed arena parameters add 83 trusted type-bound facts to
`proof_kernel_replay_unsigned_marker_info` before its body runs, exceeding the normal 64-fact
symbolic-state budget. The control-flow guard now permits a bounded 128-fact ceiling when a
function starts with more than 64 but no more than 128 facts. The independent 64-step control-flow
limit is unchanged, and larger entry states remain unsupported. The budget finding now identifies
whether the exhausted resource was steps, facts, names, or values, rather than reporting all four
as an undifferentiated state-budget failure.

At this cap the standalone module initially emitted 1,615 obligations and 243 certificates, all
independently replayed with zero gaps (previously 1,548 obligations and 227 certificates). The
newly verified `proof_kernel_replay_difference_affine_query` is required by the standalone
coverage test. A further refactor removed aggregate temporaries from
`proof_kernel_replay_unsigned_marker_info` and kept direct element access behind explicit unsigned
index and array-bound guards. The current report emits 1,647 obligations and 273 certificates,
again with zero replay gaps; the validator now requires at least 270 certificates.

That helper is still dependency-unverified: field operators on dynamic array elements lack exact
primitive-type witnesses, and its width decoder depends on the recursive, unverified
`proof_kernel_replay_constant_int`. We keep those refusals rather than treating the fields or
recursive summary as trusted. An experiment using the pre-existing 256-fact small-function cap
emitted 365 certificates, but the dogfood probe consumed about 6.3 GB RSS; that cap was rejected
and is not part of the implementation. Full self-verification remains open.

## Rejected allocation-heavy constant-evaluator work stack (2026-09-21)

The standalone replay report identifies `proof_kernel_replay_constant_int` as an unverified
recursive component, so an experiment replaced its recursion with an explicit `darray` frame
stack. The Stage1 build succeeded, but the standalone replay audit then crossed its 2,000,000-KiB
RSS watchdog after 7.51 seconds without emitting JSON. The previous recursive implementation
emitted its normal report with 1,994 obligations, 436 replayed certificates, and zero replay gaps.
The experiment was reverted and the product rebuilt from the restored source. A per-call dynamic
work stack is not viable here: it adds arena allocations in a heavily reused kernel helper. Any
future iterative evaluator must reuse bounded caller-owned scratch rather than allocate a fresh
stack per evaluation; the recursive helper remains unverified and no new proof authority was
introduced.

## Constant evaluator operator decomposition (2026-09-21)

The evaluator's unary and binary arithmetic dispatch is now isolated in small pure helpers. This
keeps the recursive traversal responsible only for validating and descending the arena tree, and
lets the arithmetic dispatch obligations be checked independently. The Stage1 build, literal
constant positive/negative regression suite, and optimized replay suites at O2 and O3 pass. The
standalone self-audit now emits 1,996 obligations and 438 replayed certificates (up from 1,994
and 436), with zero replay gaps and no semantic errors. The recursive component itself remains
unverified for the same resource-summary and fact-snapshot-budget findings; this refactor is
modular verification progress, not closure of that gap.

The string-kind dispatch was also rewritten as an explicit `match` to reduce branch-state
complexity, without changing the evaluator's admission rules. The standalone audit is unchanged at
1,996 obligations and 438 replayed certificates; the same recursive borrow-summary and
fact-snapshot-budget findings remain. To separate return-shape concerns from that gap, the
`shared_borrow_calls` regression now includes self-recursion over a shared collection returning a
scalar-only aggregate. It proves and replays all 23 obligations, while the existing adversarial
fixture still rejects escaping references, moved arguments, and a shared lend that overlaps a live
mutable borrow. The unresolved evaluator failure therefore requires more than merely allowing a
recursive shared borrow or aggregate result.

### Rejected entry-fact cap increases (2026-09-21)

For diagnosis, the entry-state-only fact cap was raised from 128 to 192. This raised the
standalone report from 438 to 449 replayed certificates, but did not clear the evaluator's
fact-snapshot-budget finding. A timed repeat peaked at 3,768,320,000 bytes RSS before it was
stopped. Raising the cap to 256 was worse: the same audit reached about 1.7 GiB in five seconds.
Both increases are rejected, and the committed cap remains 128. The next sound avenue is to
reduce unnecessary entry witnesses or the recursive helper's live symbolic state, not widen this
resource bound.

### Rejected whole-body field-name witness filter (2026-09-21)

An experimental prepass collected field names mentioned anywhere in each function body and
omitted parameter-field witnesses whose names were absent. The standalone report fell from 438
to 422 replayed certificates, while peak RSS rose to 4,181,426,176 bytes; the recursive evaluator
remained unverified with the same findings. The experiment was reverted. A body-only name set does
not account for witness dependencies introduced through call summaries and contracts, and
running a recursive AST scan for every function is itself too costly. A viable reduction needs
dependency-aware field selection and should run only for types whose eager witness set is large.

### Constant evaluator: remove a redundant checked lookup (2026-09-21)

`proof_kernel_replay_valid(nodes, root)` is exactly `root < nodes.count` (its implementation and
postcondition both state that equivalence). `proof_kernel_replay_constant_int` already checked
that bound before reading the node, so calling the predicate again and then calling
`proof_kernel_replay_node_at` duplicated the same condition and introduced another borrow-bearing
call. The evaluator now keeps the explicit early rejection and assert, then reads `nodes[root]`.
This preserves malformed-root rejection and keeps the indexed read dominated by its guard.

On the standalone replay fixture, coverage rose from 438/1,994 to 440/1,997 obligations; all 440
certificates replay, with zero gaps and no semantic errors. The unsupported borrow-summary findings
for this function fell from two to one. The recursive component is still not verified: the
remaining borrow-summary finding and the fact-snapshot budget remain. Literal-constant and
shared-borrow positive/adversarial regressions pass, as do optimized replay checks at O2 and O3.

### Constant evaluator: isolate nonrecursive leaf cases (2026-09-21)

The integer-literal and empty-array-`count` cases now live in
`proof_kernel_replay_constant_leaf`. The recursive function dispatches only unary/binary nodes
recursively and delegates all other kinds to this nonrecursive leaf checker. The leaf helper
passes the arena and scalar node fields explicitly; its `nodes[left]` access remains guarded by
`left < nodes.count`. This split verifies the leaf semantics independently and avoids carrying a
node aggregate through the shared-borrow call.

The standalone report now contains 2,004 obligations and 448 certificates (previously 1,997 and
441); all 448 replay with zero gaps and no semantic errors. There is no remaining
`borrow-call-summary-unsupported` finding for `proof_kernel_replay_constant_int`, and the leaf
function itself is now required verified by the standalone validator. The recursive component
still fails only with `control-flow-analysis-budget`; this split does not claim that evaluator is
verified.

### Verify the recursive constant evaluator with a remaining-depth measure (2026-09-21)

The fact-budget diagnostic showed the recursive evaluator grew from 64 to 85 facts after eagerly
adding 51 scalar-operator witnesses for a local copy of `ProofKernelNode`. A trial 96-fact cap was
rejected: the standalone audit reached about 1.3 GiB RSS after 2:47 without completing. Instead,
the evaluator now keeps the guarded arena node as a place and copies only the child indices and
operator needed before recursive calls; it no longer creates the unused local-record witness set.

The depth argument is normalized once to `remaining = DEPTH_LIMIT - depth`. A private recursive
worker counts that value down, retaining the same boundary behavior: leaf nodes are still
evaluated at zero remaining depth, while unary/binary nodes return unknown there. Purity analysis
now admits only literal/range/wildcard and recursively composed or-patterns in matches, with pure
guards and bodies; binding/constructor patterns stay excluded. That certifies the worker's
read-only recursive calls and preserves the branch fact needed for both binary children.

The standalone stage1 audit now verifies both `proof_kernel_replay_constant_int` and its recursive
worker. It reports 2,032 obligations, 476 certificates replayed, zero replay gaps, and zero
semantic errors. The standalone validator now requires both declarations to remain verified. This
replaces the earlier 448-certificate state and closes the fact-budget/recursive-summary gap without
raising the analysis cap.

### Constant evaluator: remove an unreachable depth branch (2026-09-21)

`proof_kernel_replay_constant_int` has the precondition `depth <= PROOF_KERNEL_REPLAY_DEPTH_LIMIT`.
Its additional `depth > limit` fallback was therefore unreachable for a valid call. Removed that
branch while retaining both pre-descent `depth >= limit` refusals and the `depth + 1 <= limit`
assertions. The stage1 build passed, and the standalone replay validator still reports 448/448
certificates replayed, zero gaps, and zero semantic errors. This cleanup does not resolve the
recursive component's fact-snapshot budget finding; the unchanged audit result confirms it was not
the source of that budget exhaustion.

### Locate control-flow snapshot budget failures (2026-09-21)

`proof_return_analysis_budget_available` previously emitted every control-flow budget finding at
line 0, even when a particular return-analysis statement or captured-block entry triggered it.
Threaded the statement position into the budget check and added a standalone-validator assertion
that a budget finding for `proof_kernel_replay_constant_int` retains a nonzero location. The
stage1-built standalone report now locates its existing `control-flow-analysis-budget` finding at
line 368 in the compiler's expanded-source coordinates. The evaluator remains
`recursive-component-unverified`; coverage stays at 448 replayed certificates with zero replay
gaps and zero semantic errors. This improves diagnosis, not proof coverage.

### Measure every bounded analysis cutoff (2026-09-21)

Control-flow, frame, and resource-state analysis budget findings now include structured
`dimension`, `observed`, and `limit` fields in JSON and repair output. For step limits, `observed`
counts the step that was refused (the completed-work counter remains capped); for fact snapshots,
it reports the actual snapshot size. This makes diagnostics actionable without weakening any
bound or changing an `unsupported` result. The standalone validator rejects budget findings whose
measurement does not actually exceed the configured limit. The stage1-built standalone audit and
the full proof test suite passed, including O2/O3 optimized replay; all source files remain below
600 lines.

### Make the constant evaluator wrapper total (2026-09-21)

`proof_kernel_replay_constant_comparison` was blocked from verification by its calls to
`proof_kernel_replay_constant_int(..., 0)`: the source checker did not normalize the imported depth
limit enough to discharge the wrapper's `0 <= limit` precondition. Calling the recursive
remaining-depth worker directly removed that obligation but exposed its recursive resource-call
graph to resource replay and caused one certificate gap; that approach was rejected. The wrapper
now has no caller precondition and returns unknown when `depth > limit`, before subtracting. At the
limit boundary it retains the prior zero-remaining semantics. This lets the comparison helper
verify without creating a new recursive resource boundary. The standalone validator now requires
the comparison helper to verify; the standalone audit replays every certificate without gaps, and
the full test suite including O2/O3 replay passes.

### Verify direct literal comparison admission (2026-09-21)

The next standalone declaration audit found that `proof_kernel_replay_direct_literal_comparison`
was unverified only because its two calls to the tuple-returning `proof_kernel_replay_node_at`
produced `borrow-call-summary-unsupported` at the left and right node reads. The helper now checks
both requested roots against `nodes.count` first, then reads only each guarded node's `kind` in
place. It still declines non-integer nodes and delegates admitted comparisons to the verified
constant comparison helper. The standalone validator now requires this helper to verify. The
standalone audit has zero replay gaps, and the full suite passes, including O2/O3 replay.

### Verify unsigned-order atom recognizers (2026-09-21)

The standalone audit next identified two unverified replay helpers,
`proof_kernel_replay_order_atom` and `proof_kernel_replay_peer_is_nameable`. Both copied full
arena records through `proof_kernel_replay_node_at` merely to distinguish integer, identifier,
and field nodes, which produced unsupported resource-summary obligations. They now pattern-match
the guarded root discriminator and access only the needed fields in place; field bases are bounds
checked before the second node read. The standalone validator requires both helpers to verify.
The standalone replay audit and the full suite pass, with no replay gaps and O2/O3 checks green.

### Verify sign-kernel literal and product destructors (2026-09-21)

The sign-reasoning module had two more body-unverified helpers,
`proof_kernel_replay_zero_literal` and `proof_kernel_replay_product_operands`. They copied an
entire node through the tuple-returning arena accessor to inspect only a kind, scalar value, or
operator. Both now reject an out-of-range root first and use pattern matching on the guarded node
kind, reading only the fields needed in each branch. This preserves the rule that product sign
reasoning applies only to a primitive `*` node and zero recognition applies only to integer zero.
The standalone validator now requires both declarations verified. The standalone audit and full
suite pass, with all certificates replayed and O2/O3 checks green.

### Verify arithmetic binary operand destructors (2026-09-21)

`proof_kernel_replay_binary_operands` and `proof_kernel_replay_negated_operand` were also
body-unverified because they copied full records through `proof_kernel_replay_node_at` for small
kind/operator tests. They now reject an invalid root before matching the arena node kind and
return only the operand indices from the matching branch. The accepted shapes are unchanged:
binary nodes must still match the requested operator, and unary nodes must still be `not`. Both
helpers are now required verified by the standalone validator. The standalone audit and full suite
pass with no replay gaps, including the optimized replay checks.

The adjacent name-equality closure remains intentionally unverified for separate reasons: its
recursive collector still has unresolved resource-summary calls and crosses the fact-snapshot cap.
This change does not claim equality-closure coverage; that collector needs its own bounded recursive
proof-state treatment.

### Verify equality-pinned arithmetic constants (2026-09-21)

`proof_kernel_replay_pinned_constant` was unverified because its tuple-returning node lookups copied
whole arena records at each step, leaving unsupported borrow-summary obligations. It now delegates
to two exact-shape helpers: one accepts only a direct integer literal, and one accepts only an
equality whose left side is the requested identifier and whose right side is a direct integer
literal. The outer lookup preserves first-matching-fact order and still rejects every other shape.
All three helpers are now verified by the standalone report; the replay count is 551/551 with zero
gaps and no trusted assumptions. The full test matrix passes, including the optimized replay checks
at O2 and O3, and the complete dogfood suite passes through the executable kernel, tactic, replay,
and portable-script harnesses.

The full dogfood run also exposed two self-contained executable fixtures that included
`model.elisa` without its separate `model/findings.elisa` declaration. Stage1 rejected both with
`unknown struct/type ProofFinding`. The fixtures now include the findings module in the same order
as `src/main.elisa`; both compile, and the previously blocked tactic and summary-replay harnesses
pass in the full dogfood run.

### Verify Boolean contradiction and conjunction recognizers (2026-09-21)

The inconsistency path copied full nodes through `proof_kernel_replay_node_at` just to recognize a
false Boolean literal, `not true`, or an `and` node. These are now three small bounded recognizers
that pattern-match the guarded root and return only a Boolean or child indices. All three verify in
the standalone audit. `proof_kernel_replay_facts_inconsistent` now delegates those exact cases to
the helpers; its fact-snapshot budget finding is gone. Its bounded recursion now uses a remaining
depth counter, and omits a recursive call at one remaining level because that call would return
false immediately. This also removes the separate recursive-decreases obligation. The checker
now verifies both the remaining-depth worker and `proof_kernel_replay_facts_inconsistent`. Removing
the unused `children` arena from this traversal allowed the resource summary to converge. The
depth precondition at its call from `proof_kernel_replay_facts_propositionally_inconsistent` is
explicitly established. The broader wrapper remains unverified because its general structural
fact-denial path calls the recursive expression-equality helper. The standalone report now replays
all 582 certificates with zero gaps and no trusted assumptions. The full proof test matrix passes,
including O2/O3 replay, and the complete dogfood suite passes its malformed-arena, runtime-kernel,
stage0-bootstrap, and tactic-script checks.

### Verify expression-equality leaf cases (2026-09-21)

The next equality-path refinement extracts its nonrecursive leaf cases into
`proof_kernel_replay_expr_leaf_equal`: absent nodes compare equal after the caller's shape checks;
integer and Boolean leaves compare values; float/string/character/identifier/shorthand leaves
compare names. The helper is verified in the standalone audit and the main structural comparator
dispatches to it only after matching kind/operator and validating both node shapes. The recursive
compound-term comparison remains unverified and is not claimed closed. Verification passed the
source-length and diff checks, the full proof test matrix (including O2/O3 replay), and the complete
dogfood suite. The standalone dogfood report currently proves 583 of 2,086 obligations with zero
replay gaps and no trusted assumptions; this does not close the remaining compound equality path.

### Simplify structural equality arena reads (2026-09-21)

`proof_kernel_replay_expr_equal` now reads the two roots directly from the arena after its validity
checks, and reads call-argument wrapper nodes only after recursive equality succeeds and explicit
index bounds checks pass. This removes the tuple-returning `node_at` calls from the comparison path,
whose resource summaries could not be encoded. Standalone replay coverage increased from 583 to
585 certificates (2,084 obligations, zero replay gaps, no trusted assumptions); the comparator is
still unverified because recursive borrow-call summaries remain opaque and its fact budget is still
exceeded (94 observed, 64 limit). This is not a soundness-closure claim. Source-length and diff
checks, the full proof test matrix including O2/O3 replay, and the complete dogfood suite all pass.

### Make structural equality iterative (2026-09-21)

Replaced recursive expression descent with a bounded worklist of `(left, right, depth)` pairs.
Every pair rechecks the depth limit, both arena indices, and both node shapes before comparing;
compound cases enqueue exactly the child pairs used by the former recursive cases. Call arguments
retain their wrapper-kind/name check. Worklist growth is capped by the named
`PROOF_KERNEL_REPLAY_MAX_EXPR_EQUALITY_WORK` limit, and exhaustion returns false (conservative
unknown equality), never equality. The enqueue helper verifies and is now required by the standalone
audit. This removed the recursive `borrow-call-opaque` findings from `expr_equal`, and standalone
coverage is 593 proven certificates with zero replay gaps and no trusted assumptions. However,
`expr_equal` remains unverified: its current branch structure exceeds the control-flow fact budget
(67/64) and resource-analysis step budget (129/128), so callers `proof_kernel_replay_fact_denies`
and `proof_kernel_replay_facts_propositionally_inconsistent` also remain unverified. Full regression
verification passed: source-length/diff checks, the full proof test matrix (including O2/O3 and
standalone trust-boundary validation), and the complete dogfood suite all pass. The control-flow and
resource-analysis budget findings remain open; passing regressions do not turn this routine into a
verified declaration.

### Refine bounded equality work items (2026-09-21)

Equality work items now distinguish call-argument pairs, so their wrapper kind is checked when the
pair is popped rather than by eagerly indexing an untrusted child node. Verified leaf, node-pair,
ordinary-enqueue, call-argument-enqueue, and child-enqueue helpers keep the driver smaller; all five
are required by the standalone audit. At the original 64-step cap, the standalone report has 603
proven certificates, 603/603 replayed, zero gaps, and no trusted assumptions. The comparator no
longer reports recursive borrow opacity or index-safety findings, but remains unverified because it
needs 65 control-flow steps (limit 64). Raising that shared cap to 128 exposed additional index
obligations and more failed goals without verifying equality, so the global limit was restored to
64. The comparator and its downstream fact-denial routines remain open.
The full proof test matrix (O2/O3 replay included) and complete dogfood suite pass on this exact
worklist/helper state; source-length and diff checks also pass.

Follow-up analyzer-shape experiments on this state did not close the remaining 65/64 limit and were
discarded. Moving child enqueueing into a separate helper made that helper itself unverified: its
direct child-arena reads were not discharged, and replacing them with checked child access still
exceeded the helper's bounded fact snapshot (129 observed, 64 limit). Recasting the inline dispatch
as grouped string-pattern arms also failed to help: the comparator retained the 65/64 control-flow
finding and acquired a 129/128 resource-analysis finding. The committed worklist remains unchanged;
the next useful approach must reduce analyzer state/cost without creating opaque or over-budget
callee summaries. In particular, these experiments do not justify raising shared analysis limits.

### Use total child lookups in structural equality (2026-09-21)

The worklist comparator's variable-arity branch now reads each serialized child through the total
`proof_kernel_replay_child_at` accessor and refuses comparison if either lookup is unknown. The
existing overflow-safe whole-range guard remains; its second range predicate was redundant, while
the per-element accessor independently checks every actual read. The standalone report for this
exact source remains at 603/603 certificates replayed with zero gaps, and the trust-boundary
validator passes. `proof_kernel_replay_expr_equal` is still unverified at 65/64 control-flow steps;
this hardening does not claim to close it. A direct root-bound rewrite was rejected because it
introduced lower-bound obligations, so the explicit `proof_kernel_replay_valid` checks and
assertion remain. A statement-only reinterpretation of the shared budget was also reverted: it did
not verify equality and made the malformed arena-cycle fixture take over 2½ minutes before
interruption. Under the original budget, that fixture completes as failed with 605/605 certificates
replayed and zero gaps.

### Verify bounded child-span enqueueing (2026-09-21)

The variable-arity traversal is now a focused `proof_kernel_replay_expr_child_span_enqueue` helper.
It validates the count and both child-span starts before subtracting or indexing, reads each child
through the total accessor, checks both lookup results, and preserves call-argument wrapper tagging
when enqueuing. The helper is required verified by the standalone trust validator. Its caller keeps
the structural arity equality check and delegates span bounds to the helper, avoiding duplicate
range-state in the main comparator. The standalone audit proves 604 certificates, replays 604/604
with zero gaps, and reports zero semantic errors. The comparator itself remains unverified at
65/64 control-flow steps; this narrows the remaining gap but does not close it.

### Verify bounded structural equality (2026-09-21)

The return-analysis work budget is now selected per function: the ordinary limit remains 64, while
`proof_kernel_replay_expr_equal` gets a named 128-step analysis allowance. Lower tested limits of
65 and 66 still refused at 66/65 and 67/66 respectively. This changes only
verification-analysis completeness, not runtime/kernel behavior or proof rules; budget exhaustion
still reports `unsupported`. The standalone report now verifies the comparator, and the trust
validator requires that declaration to remain verified. The corpus remains `unsupported` overall;
`proof_kernel_replay_fact_denies` and `proof_kernel_replay_facts_propositionally_inconsistent`
still have unverified resource-summary dependencies. The run produced 605 certificates, replayed
all 605 with zero gaps, had zero semantic errors, and passed the standalone trust validator. Existing
kernel arena runtime probes exercise positive equality and reject unequal hidden node payloads.

### Admit all-shared aggregate lends (2026-09-22)

The resource checker now recognizes the narrow case where every callee formal is an immutable
shared reference and the return is already proven reference-free. Nested capability storage cannot
escape through an immutable formal, and the existing return-region/reference guards remain in
force; mixed, by-value, mutable, or reference-returning calls retain the stricter target-storage
check. This lets read-only kernel helpers compose without an unnecessarily opaque summary. The
standalone report improved from 605 to 607 proven certificates, removed three `borrow-call-opaque`
and three `region-call-opaque` findings, lost no verified declaration, retained zero semantic errors,
and replayed all 607 certificates with zero gaps. The fact-denial caller remains independently
unverified because its formal metadata is not in this all-shared class.

### Admit mixed immutable shared/value formals in read-only frames (2026-09-22)

The previous lend predicate was too narrow: it required every callee formal to be an immutable
shared reference, so a helper with shared aggregate inputs plus scalar indexes or depth bounds was
still treated as opaque. At that point, the predicate checked each formal independently: immutable shared
references are permitted, while non-reference formals must be target-reference-free and mutable
references were rejected. To preserve the kernel's zero-gap invariant, summary-free mixed lends
were still refused when the *caller* had a mutable reference capability; ordinary verified summary
composition was responsible for those frames. This closed the resource-summary gap for
`proof_kernel_replay_fact_denies` without trusting a body summary or weakening replay. The
standalone report now proves 638 certificates, replays 638/638 with zero gaps, and reports zero
semantic errors; the writable-lend adversarial matrix also remains fully replay-covered. The
mutable `proof_kernel_replay_add_signed_type_bounds` frame was explicitly unsupported until the
kernel traversal fix documented below.

### Replay nested scalar calls in resource arguments (2026-09-22)

The remaining replay gap was not an ownership failure. The kernel's no-region value traversal
treated a call's callee head as a runtime value, so a scalar argument such as
`proof_kernel_signed_width_min(marker.width)` looked up the function name as a resource binding
and failed closed. Call arguments are the runtime values; the callee expression is syntax and is
now skipped by that traversal. A focused bounds-composition fixture reproduces the former gap and
now replays all 6/6 certificates. Removing the temporary mixed-lend caller guard then raises the
standalone corpus to 647 certificates, replays 647/647 with zero gaps, and removes the need for
that conservative restriction. The guard and its now-unused helper were removed; malformed or
region-bearing call arguments remain rejected by the recursive argument traversal.
