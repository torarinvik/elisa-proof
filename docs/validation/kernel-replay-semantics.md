# Kernel replay semantics and soundness boundary

## Status

This is a source-level specification of the current replay boundary, not a proof that the
implementation is sound. The replay code is a collection of decision procedures and certificate
checkers in Elisa; this document records what a successful result is intended to mean and the
assumptions that remain. `ensure` contracts, dogfood proofs, static inventory checks, and passing
adversarial tests are implementation evidence. They do not, by themselves, prove the mathematical
soundness of the replay rules or the compiler that executes them.

The main implementation entry points are in `src/proof/kernel_replay/api.elisa`; arena syntax and
shape admission live in `src/proof/kernel_replay/tactic_arena_validation.elisa` and
`src/proof/kernel_replay/arena_shapes.elisa`. The source-neutral node definitions and machine-width
constants are in `src/proof/kernel_core.elisa`.

## Intended theorem

For a logical replay entry point, let `H` be the supplied hypotheses, `C` the supplied goal, and
`D` an admitted interpretation of the node language. A successful replay is intended to establish

> for every interpretation `D` satisfying every proposition in `H`, `C` also holds in `D`.

This implication is conditional on the exact supplied hypotheses. It does not establish that an
Elisa source file generated `H`, that `C` is the source obligation, or that the supplied type,
operator, resource, effect, or declaration metadata came from the source program. Source adapters
must separately authenticate those links. An empty or forged premise set is not repaired by kernel
replay.

## Entry points and their claims

| Entry point family | What success checks | What success does not establish |
| --- | --- | --- |
| `proof_kernel_replay_goal_report` | Source-neutral logical replay after arena and proposition-shape admission. Identifiers, calls, and projections are opaque atoms unless a checked rule gives them more meaning. | Elisa typing, source provenance, operator resolution, declaration identity, or that the goal is required. |
| `proof_kernel_replay_proposition_formation_report` and typed replay | Proposition formation under the supplied `ProofKernelTypeEnvironment`, followed by replay. | Provenance of the environment. A source-backed caller must reconstruct and bind its rows to declarations. |
| Tactic step, branch, and trace replay | The serialized transition has a recognized action shape and preserves the recorded state according to the replayed rule. Typed variants also check formation under a supplied environment. | That a source tactic actually produced the trace, unless its adapter binds each root and transition to source. |
| Effect, resource, frame, checked-index/get, and structural reports | The corresponding serialized certificate satisfies the dedicated structural or state-transition checker. | That a resource/effect witness belongs to a source declaration, or that a source obligation was not omitted. These are adapter obligations. |

Every public entry must validate its roots or explicitly receive an internally established
admission result. Workspace arrays are scratch, not authority. Cache reuse is sound only while the
same immutable arena snapshot is being checked; public workspace APIs revalidate rather than
trusting a previous verdict.

The bool goal-report API treats a failed search as “not established.” Callers that need to report
why may use `proof_kernel_replay_goal_report_status` or its workspace variant, which also reports
whether the cumulative logical goal-search meter exhausted its limit. This status does not classify
arena-admission failures; those remain a separate refusal boundary.

Source certificate replay receipts and full report output expose a batch-wide
`goal_search_work_exhausted` diagnostic. It records that some logical replay in the batch hit the
shared limit; it does not identify a particular goal or change its verdict. Producer-side
`timeout` findings continue to describe only exhaustion in the source proof search.

## Logical rules

The proposition checker admits the logical fragment represented by the arena: Boolean constants,
opaque propositional atoms, negation, conjunction, disjunction, implication, conditional
propositions, and explicitly tagged universal or existential quantifiers. A bare scalar term is
not a proposition. Quantifier replay is conditional on the encoded binder, range, and body being
well formed and on its substitution/range side conditions being validated; parser syntax alone
does not determine a quantifier's logical kind.

Exact fact containment is an assumption rule: a goal may be concluded when it is the same admitted
proposition as a supplied hypothesis. Structural equality is not a source-identity proof. Any
source-facing caller must validate the hypothesis trace independently.

Classical contradiction and disjunction rules are part of the source-neutral logical theory where
the corresponding replay path admits them. They must not be interpreted as constructive proofs.
An API that promises constructive evidence must use a separate rule set and representation.

## Arithmetic and finite-model rules

Arithmetic conclusions are admitted only through the active, metered replay paths. Those paths
check primitive scalar witnesses, signedness and widths where needed, range/overflow conditions,
and exact fact membership before applying interval, difference, linear, congruence, or other
specialized rules. Linear certificates are untrusted: replay checks that each premise is present,
that multipliers satisfy the rule's sign and magnitude restrictions, that checked arithmetic
normalization succeeds, and that variable coefficients cancel with a positive residual constant.
The unsigned strict-progress rule also admits the complete goal comparison against untrusted
operator markers and requires primitive scalar witnesses for both operands before using its
arithmetic argument. This source-level guard still needs matched-build positive and forged-root
runtime controls; it is not yet runtime-qualified.

Scalar-element witnesses are rooted at the owning container or scalar reference. When the
resolved scalar element type overrides a primitive operator, source analysis emits an
`__elisa_untrusted_operator_type(place, "Element.All")` marker. Replay recognizes this distinct
marker and rejects primitive admission for indexed terms whose index path resolves to that exact
place. The marker currently blocks all primitive operators on those elements because the replay
entry points do not carry protocol identity consistently. Source marker provenance and the
indexed-path match are both required; malformed marker payloads or exhausted work remain unknown.

The bounded-model procedure is a finite countermodel search, not a general theorem prover. It may
prove an implication only when its admitted finite domain is complete for the current hypotheses
and type bounds, its evaluator agrees with admitted source arithmetic on every evaluated term, and
all assignments in that domain have been checked. It refuses when the finite frame, symbol count,
work budget, arithmetic semantics, or type bounds are incomplete. In particular, its `i64` storage
does not justify treating unsupported shifts, bitwise operations, overloaded comparisons, or
unrepresentable machine-word values as ordinary mathematical integers.

Type-marker calls in hypotheses are metadata-bearing premises. Their spelling and serialized
shape are not source authentication. Goal replay rejects a type marker as a goal; source adapters
must validate marker provenance and meaning before using such facts for an Elisa guarantee.

## Resource, effect, and state rules

Resource reports interpret the serialized event stream using the resource-state transition
checker, including place overlap, borrow/lend state, call argument binding, and bounded recursive
call replay. Effect containment checks declared rows. Frame policies describe which locations a
certificate permits a function to read or modify. These meanings are conditional on the exact
validated event, row, or frame inputs. They are not proofs that a source body obeys those inputs
until source reconstruction and owner identity checks connect the certificate to the body.

All traversal and search procedures must be finite and fail closed: malformed shapes, invalid
indices, cycles, depth exhaustion, arithmetic overflow, incomplete metadata, or work exhaustion
must not produce `proven`. A refusal means “not established”; it is not evidence that the negation
is true.

## Assumptions and open proof obligations

The following are not discharged by this source specification:

1. A formal or mechanically checked soundness argument for each logical, arithmetic, quantifier,
   congruence, tactic, resource, effect, frame, and structural rule.
2. Proof that the bounded-model domain includes every interpretation satisfying its hypotheses,
   and that evaluator operations coincide with source semantics on every admitted term.
3. Proof that interval, difference-bound, equality-closure, Farkas/linear, division, widening,
   fixed-width, and conditional normalization preserve truth under all admitted widths and sorts.
4. Independent source reconstruction proving that hypotheses, type markers, operator witnesses,
   call summaries, resource events, declaration owners, and required-goal inventories correspond
   exactly to the delivered source and dependency closure.
5. Correctness of the Elisa compiler, runtime, arithmetic implementation, memory model, and any
   imported or foreign implementations used to execute the checker. These identities and
   assumptions must be recorded for qualification; a matching digest proves identity, not
   semantic preservation.
6. A matched producer/replay build and adversarial runtime qualification of current changes.

The implementation inventory and focused regression suites should be used to select and track
these obligations, but must not be reported as a whole-kernel soundness proof. Changes to a rule
should update this document, add a positive and a forged-certificate negative control, and state
which formal or runtime evidence actually discharges the changed obligation.
