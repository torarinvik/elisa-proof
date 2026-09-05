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

Not covered. The witness follows declared types, so a comparison whose operand is a synthesized
symbol the producer never typed — an unresolved call result, for instance — is still admitted by
these tiers. That is a strictly smaller surface than before and it fails toward admission rather
than refusal, so it remains an open item: closing it needs the callee return type recorded in the
function table.

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
