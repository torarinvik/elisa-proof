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
