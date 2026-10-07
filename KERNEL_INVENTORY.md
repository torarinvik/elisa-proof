# Kernel inventory

This is the reviewed inventory of the proof kernel's term language, certificate rules, fact
provenance and trust boundary (implementation plan item P1-01). Every table between a pair of
`<!-- inventory:... -->` markers is checked against the source by
`scripts/test_kernel_inventory.py`, which extracts each closed set from the code and requires
exact equality with the first column. A kind added to the kernel without a row here, or a row
left behind after a kind is removed, fails `scripts/test.sh`.

Paths are relative to `src/`. "Kernel" means `proof/kernel_core.elisa` plus
`proof/kernel_replay/*`; "replay" means `proof/replay/*`.

## Arena node kinds

`ElisaProofKernelCore::ProofKernelNode` has ten fields: `kind`, `operator`, `left`, `right`,
`auxiliary`, `children_start`, `children_count`, `value` (i64), `name`, `secondary_name`.
`proof/kernel_replay/arena_shapes.elisa` admits exactly the kinds below and requires every field
that the "Fields" column does not mention to be zero or empty. Any other kind makes
`proof_kernel_replay_arena_shape_valid` false, which rejects the whole arena before any rule runs.

Consumers are all kernel modules unless the row names specific ones. Structural equality
(`quantifiers_and_arena.elisa`) and typing (`proposition_typing.elisa`) cover every kind.

<!-- inventory:node-kinds -->
| Kind | Family | Fields | Producer |
|---|---|---|---|
| `int` | scalar | `value`; `operator` = width tag `u64`/`usize` only with `value` < 0 (denotes `value` + 2^64), else empty | `proof/kernel.elisa` |
| `typed-int` | scalar | `value` = typed bit pattern; `name` = exact primitive integer sort | `kernel_typed_arithmetic.elisa`, `kernel_contextual_constants.elisa` |
| `bool` | scalar | `value` in {0,1} | `proof/kernel.elisa`, `check/kernel_proposition_environment.elisa` |
| `float` | scalar | always rejected: NaN breaks reflexive equality | none |
| `opaque-float-literal` | leaf | `name` = exact source spelling; valid only as a direct comparison operand, with no numeric value or scalar witness | `proof/kernel.elisa` |
| `string` | scalar | `name` = literal text | `proof/kernel.elisa`, `check/kernel_proposition_environment.elisa` |
| `char` | scalar | `name` = literal text | `proof/kernel.elisa` |
| `ident` | scalar | `name` = identifier | `proof/kernel.elisa` |
| `shorthand` | leaf | `name` = implicit field shorthand | `proof/kernel.elisa` |
| `absent` | leaf | no fields; stands for an omitted optional operand | `proof/kernel.elisa` |
| `unsupported` | leaf | `operator` = source tag; opaque to every rule | `proof/kernel.elisa` |
| `unary` | unary | `operator`, `left` = operand | `proof/kernel.elisa` |
| `move` | unary | `left` = moved operand | `proof/kernel.elisa` |
| `field` | access | `left` = base, `name` = field | `proof/kernel.elisa`, `resources/places_and_calls.elisa` |
| `scope` | access | `left` = qualifier, `name` = member | `proof/kernel.elisa`, `check/declaration_checks.elisa` |
| `binary` | access | `operator`, `left`, `right` | `proof/kernel.elisa`, `resources/places_and_calls.elisa` |
| `index` | access | `left` = container, `right` = index | `proof/kernel.elisa`, `resources/places_and_calls.elisa` |
| `dict_entry` | access | `left` = key, `right` = value | `proof/kernel.elisa` |
| `slice` | projection | `left` = base, `right`/`auxiliary` = low/high bound | `proof/kernel.elisa` |
| `index-n` | projection | `left` = base, children = indices | `proof/kernel.elisa` |
| `checked-index` | projection | `left` = container, `right` = index | `proof/kernel.elisa`, `check/index_checks.elisa` |
| `checked-get` | projection | `left` = container access | `proof/kernel.elisa`, `check/index_checks.elisa` |
| `if` | control | `left` = condition, `right` = then, `auxiliary` = else | `proof/kernel.elisa` |
| `call_arg` | control | `left` = value, `name` = label | `proof/kernel.elisa` |
| `field-init` | control | `left` = value, `name` = field | `proof/kernel.elisa` |
| `construct` | aggregate | `left` = type, children = field inits | `proof/kernel.elisa` |
| `record-update` | aggregate | `left` = base, children = field inits | `proof/kernel.elisa` |
| `call` | aggregate | `left` = callee, children = arguments, `auxiliary` = 0 or argument count | `proof/kernel.elisa` |
| `array` | aggregate | children = elements | `proof/kernel.elisa` |
| `tuple` | aggregate | children = elements | `proof/kernel.elisa`, `check/kernel_proposition_environment.elisa` |
| `set` | aggregate | children = elements | `proof/kernel.elisa` |
| `dict` | aggregate | children = entries | `proof/kernel.elisa` |
| `quantifier` | aggregate | `operator` in {forall, exists}, `name` = binder, `left` = range, `right` = body, `auxiliary` = body statement count (1 or 2) | `proof/kernel.elisa` |
| `effect` | effect | `name` = effect | `check/declaration_checks.elisa` |
| `effect-row` | effect | children = effects | `check/declaration_checks.elisa` |
| `effect-call` | effect | `left` = callee row, `name` = callee | `check/declaration_checks.elisa` |
| `effect-containment` | effect | `left` = declared row, children = calls, `name` = function | `check/declaration_checks.elisa` |
| `resource-sview-param` | resource binding | `name`, `secondary_name` = region, `auxiliary` = sview flag | `resources/sview_certificates.elisa` |
| `resource-bind` | resource binding | `operator` = mode, `left` = source, `auxiliary` = flags | `resources/state_and_regions.elisa` |
| `resource-region-param` | resource binding | `operator` = external, `name` = region | `resources/statement_checker.elisa` |
| `resource-region-return` | resource binding | `operator` in {param, param-call, sview, sview-call}; `param`/`sview` `left` = the returned root's own use or allocation, `param-call`/`sview-call` `left` = the immediately preceding call, `secondary_name` = the caller formal that replay re-derives from the callee summary; summaries are read with returns nested in branch scopes; an empty `name` is admitted only for a `param`/`param-call` reference return, whose `param` witness must be a use of a region-less reference formal of equal mutability | `resources/statement_checker.elisa`, `resources/return_witnesses.elisa`, `resources/sview_certificates.elisa` |
| `resource-region-open` | resource region | `name` = region | `resources/statement_checker.elisa` |
| `resource-region-close` | resource region | `name`, `auxiliary` = explicit destroy | `resources/state_and_regions.elisa`, `resources/statement_checker.elisa` |
| `resource-region-alloc` | resource region | `name`, `secondary_name` = region, `auxiliary` = extent flags | `resources/state_and_regions.elisa` |
| `resource-region-bind` | resource region | as alloc; sview flag allowed | `resources/state_and_regions.elisa`, `resources/sview_certificates.elisa` |
| `resource-region-alloc-discard` | resource region | `left` = value, `secondary_name` = region | `resources/state_and_regions.elisa` |
| `resource-region-return-alloc` | resource region | `left` = value, `secondary_name` = region | `resources/state_and_regions.elisa` |
| `resource-region-call-alloc` | resource region | `left` = call, `secondary_name` = region | `resources/call_regions.elisa` |
| `resource-region-rebind-alloc` | resource region | `left` = value, `name` = target, `secondary_name` = region | `resources/state_and_regions.elisa` |
| `resource-region-assign` | resource region | `left` = value, `name` = target, `secondary_name` = region | `resources/region_flow.elisa` |
| `resource-write` | resource event | `name` = place root, `left` = place | `resources/region_flow.elisa` |
| `resource-move` | resource event | `name` = place root, `left` = place | `resources/expression_checker.elisa` |
| `resource-use` | resource event | `name` = place root, `left` = place | `resources/expression_checker.elisa` |
| `resource-call-arg` | resource event | `operator` in {value, borrow, reference, region-new}, `left` = argument | `resources/borrows_and_bindings.elisa`, `resources/call_regions.elisa` |
| `resource-call-formal` | resource event | `operator` = formal mode, `name` = formal | `resources/borrows_and_bindings.elisa` |
| `resource-call-lend` | resource call | children = lend pairs plus `right` extra roots | `resources/borrows_and_bindings.elisa` |
| `resource-call` | resource call | `left` = call, children = arguments then `auxiliary` formals | `resources/call_regions.elisa` |
| `resource-call-region` | resource call | `operator` = param, `name`/`secondary_name` = formal/actual region | `resources/borrows_and_bindings.elisa`, `resources/call_regions.elisa` |
| `resource-call-result` | resource call | `operator` in {"", sview}, `left` = call, `auxiliary` = flags | `resources/statement_checker.elisa`, `resources/sview_certificates.elisa` |
| `resource-scope` | resource summary | children = events in scope | `resources/state_and_regions.elisa` |
| `resource-join-move` | resource summary | `name` = place, `auxiliary` = join count | `resources/state_and_regions.elisa` |
| `resource-safety` | resource summary | `name` = function, children = events, `secondary_name` = `resource-v1` | `resources/state_and_regions.elisa` |
| `resource-disjoint` | resource summary | `operator` = `!=`, `left`/`right` = places, children = premise facts | `resources/places_and_calls.elisa` |
| `structural-argument` | structural | `operator` in {same, strict}, `name`/`secondary_name` = formal/actual, `value`/`auxiliary` = sizes | `check/flow_and_type_model.elisa` |
| `structural-edge` | structural | `name`/`secondary_name` = caller/callee, children = arguments | `check/flow_and_type_model.elisa` |
| `structural-safety` | structural | `name` = SCC root, children = edges, `secondary_name` = `structural-v1` | `check/flow_and_type_model.elisa` |
| `frame-field` | frame policy | nonempty field label; other fields zero/empty | frame policy runtime probes; source producer pending |
| `frame-place` | frame policy | versioned parameter ordinal and up to three backward field children | frame policy runtime probes; source producer pending |
| `frame-policy` | frame policy | versioned spec/allow/write/preserve operation, actual place, bounded partitioned policy children and owner label | frame policy runtime probes; source producer pending |
<!-- /inventory:node-kinds -->

## Typing binding kinds

`ProofKernelTypingBinding` records are the only typing environment the kernel trusts. The
validation lives in `proof_kernel_replay_typing_binding_valid` (`kernel_replay/type_environment.elisa`),
and the source producer is `check/kernel_proposition_environment.elisa`.

<!-- inventory:typing-kinds -->
| Kind | Meaning | Required shape |
|---|---|---|
| `value` | a named value and its sort/type | no owner, no signature |
| `reference-value` | a by-reference scalar parameter or local, indexable only at `[0]` | no owner, no signature; marked `parameter_by_reference` |
| `function` | a callable, with signature identity | no owner; parameter count bounded |
| `function-parameter` | one parameter of a signature | owner and signature identity set |
| `proposition` | a named proposition | sort `proposition` |
| `type` | a named or container type | `type_name == name`, type identity set |
| `field` | a field of an owner type | owner and owner type identity set |
| `enum-member` | an enum member value | owner is the enum; identities agree |
| `enum-tag` | an enum tag used in `is` tests | owner is the enum; identities agree |
| `enum-scope-segment` | one qualified enum path segment | enum type identity and bounded path ordinal/count agree |
<!-- /inventory:typing-kinds -->

## Certificate rules

`proof_replay_certificate_rule_valid` (`replay/certificate_validation_integrated_helpers.elisa`) is the closed rule
protocol. `proof_replay_certificate_with_stack` (`replay/fact_trace_validation.elisa`) dispatches
each certificate to one public kernel entry point, after it has tied the certificate to a proven
goal attempt, bound every fact to a trace and re-matched the AST against the arena.

<!-- inventory:certificate-rules -->
| Rule | Kernel entry point | Notes |
|---|---|---|
| `goal` | `proof_kernel_replay_goal_report_with_workspace` | quantifier-rooted goals go to the quantifier report |
| `index-lower` | `proof_kernel_replay_goal_report_with_workspace` | reusable by `check/certificate_reuse.elisa` under exact goal and fact equality |
| `index-upper` | `proof_kernel_replay_goal_report_with_workspace` | same reuse rule as `index-lower` |
| `slice-lower` | `proof_kernel_replay_goal_report_with_workspace` | |
| `slice-upper` | `proof_kernel_replay_goal_report_with_workspace` | |
| `slice-order` | `proof_kernel_replay_goal_report_with_workspace` | |
| `checked-index` | `proof_kernel_replay_checked_index_report_with_workspace` | |
| `checked-get` | `proof_kernel_replay_checked_get_report_with_workspace` | |
| `quantifier-forall` | `proof_kernel_replay_quantifier_report_with_workspace` | mode `forall` |
| `quantifier-exists` | `proof_kernel_replay_quantifier_report_with_workspace` | mode `exists` |
| `resource-safety` | `proof_kernel_replay_resource_report_with_workspace` | trace certificate; source goal is literal `true`; root admitted by `proof/certificate_admission.elisa` (`resource-v1`); embedded facts checked by `proof_replay_resource_event_facts_with_owner` |
| `structural-safety` | `proof_kernel_replay_structural_report_with_workspace` | trace certificate; root admitted as `structural-v1` |
| `effect-containment` | `proof_kernel_replay_effect_report_with_workspace` | trace certificate |
<!-- /inventory:certificate-rules -->

## Certificate construction entry points

These functions append `ProofGoalCertificate` values to the report. The inventory checker finds
the construction sites under `proof/` and requires this exact producer set. This makes new report
certificate admission paths visible for review; it does not establish that the source facts,
kernel root, or replay dispatch are sound.

<!-- inventory:certificate-producers -->
| Function | Source module | Certificate family |
|---|---|---|
| `proof_add_goal_attempt` | `proof/model/report_recording.elisa` | ordinary goal and quantifier obligations |
| `proof_reuse_goal_attempt` | `proof/check/certificate_reuse.elisa` | exact-state reuse of index bounds |
| `proof_add_resource_goal_attempt` | `proof/certificate_admission.elisa` | resource-safety trace |
| `proof_add_effect_goal_attempt` | `proof/certificate_admission.elisa` | effect-containment trace |
| `proof_add_structural_goal_attempt` | `proof/certificate_admission.elisa` | structural-safety trace |
<!-- /inventory:certificate-producers -->

## Fact trace kinds

Each fact a certificate uses must be bound to a `ProofFactTrace` whose kernel expression is
structurally equal to the fact.

Boundary kinds describe source facts emitted by the named producer in `check/`.
`proof_replay_boundary_trace_shape_valid` requires no dependency and no premises, so a
summary trace cannot be relabelled as one. Selected kinds also have source validators in
`replay/boundary_trace_shapes.elisa`, including constants, enum facts, match exhaustiveness
and deterministic calls. These validators narrow the producer trust boundary; they do not
establish independent source correspondence for every boundary fact.

<!-- inventory:boundary-trace-kinds -->
| Kind | Producer | Source construct |
|---|---|---|
| `global-constant` | `check/global_constants.elisa` | a module constant's value (re-validated by `replay/global_constant_validation.elisa`) |
| `global-constant-qualified` | `check/global_constants.elisa` | a module constant reached through a qualified name (re-validated by `replay/global_constant_validation.elisa`) |
| `variant-exclusion` | `check/variant_exclusion.elisa` | `not (x is E.V) or not (x is E.W)` for distinct variants of a uniquely declared enum (re-validated by `replay/variant_exclusion_validation.elisa`) |
| `match-exhaustiveness` | `check/returns/matches.elisa` | complete finite match over a uniquely declared enum's variants (re-validated against source declarations and proposition typing) |
| `precondition` | `check/declaration_checks.elisa` | a function `requires` clause |
| `type-bound` | `check/bounds_and_facts.elisa` | the range of a parameter's machine-integer type |
| `deterministic-call` | `check/function_contracts_and_frames.elisa` | a scalar witness for a verified, effect-free, acyclic by-value call; replay reconstructs and validates the call chain |
| `runtime-assert` | `check/returns/contracts.elisa` | a statement after an aborting `assert` |
| `runtime-guard` | `check/returns/matches.elisa` | an early-return guard's negation |
| `branch-condition` | `check/statement_checks.elisa`, `check/bounds_and_facts.elisa`, `check/returns/matches.elisa` | the condition of the taken branch |
| `loop-condition` | `check/statement_checks.elisa`, `check/returns/loops.elisa` | a `while` condition inside the body |
| `loop-invariant` | `check/statement_checks.elisa`, `check/returns/loops.elisa` | an invariant assumed at body entry (and proved separately) |
| `loop-range` | `check/loop_range_facts.elisa` | a `for` index's range bounds |
| `local-binding` | `check/symbol_and_move_state.elisa` | `name == value` for an immutable local |
| `collection-push` | `check/collection_push.elisa` | after `v.push(x)` on a mutable darray reference parameter: `v.count == T + 1`, `v[T] == x` and `v[v.count - 1] == x`, the pre-push count T an unsigned 64-bit scalar at most 2^63 - 2 |
| `collection-pop` | `check/collection_pop.elisa` | after a statement `v.pop()` on a mutable darray reference parameter: `1 <= S` (the builtin traps on an empty array) and `v.count == S - 1`, S the pre-pop count |
| `entry-count` | `check/collection_push.elisa` | the entry symbol E behind `old(v.count)` is an unsigned 64-bit scalar |
| `indexed-write` | `check/indexed_writes.elisa` | `v[i] == x` for the stored cell after an indexed write `v[i] <- x`, on a scalar element whose stored value's reads survive the write |
| `linear-certificate` | `linear/linear_certificate_search.elisa` | a hint naming premises and multipliers; it asserts nothing, and `kernel_replay/linear_certificates.elisa` admits a goal only when the premises are facts and the weighted constraints cancel to `0 < c <= 0` |
| `const-enum-exclusion` | `check/operator_impl_chain.elisa` | distinct const-enum variant exclusion; replay validates source enum identity and values |
| `const-enum-member-value` | `check/enum_value_types.elisa`, `check/operator_impl_chain.elisa` | const-enum member scalar comparison; replay validates source member value |
<!-- /inventory:boundary-trace-kinds -->

Derived kinds are never axioms. Their premises are themselves traced. Replay re-proves each step
twice: with the AST `proof_replay_goal`, and, for its kernel expression, with the kernel goal
report.

<!-- inventory:derived-trace-kinds -->
| Kind | Producer | Checked by |
|---|---|---|
| `proof-step` | `check/block_checker_and_patterns.elisa` | premises traced, step re-proved |
| `lemma-step` | `check/returns/contracts.elisa` | premises traced, step re-proved |
| `loop-invariant-step` | none: reserved, never emitted | premises traced, step re-proved |
| `branch-conjunct` | `check/bounds_and_facts.elisa` | premises traced, step re-proved |
| `unit-resolution` | `check/symbol_and_move_state.elisa` | premises traced, step re-proved |
| `branch-join` | `check/call_and_branch_state.elisa` | premises traced, step re-proved |
<!-- /inventory:derived-trace-kinds -->

Summary kinds import another declaration's proven contract. They need the exact theorem
instance, with each substituted `requires` tied to a replayed certificate. They also need
`proof_replay_dependency_is_checked`, which tracks the SCC stack with a depth limit of 16 so that
circular reasoning fails.

<!-- inventory:summary-trace-kinds -->
| Kind | Producer |
|---|---|
| `lemma-summary` | `check/alias_stability.elisa` |
| `function-summary` | `check/bounds_and_facts.elisa` |
<!-- /inventory:summary-trace-kinds -->

## Resource fact-free leaves

A `resource-safety` certificate carries no top-level proposition, so logical facts can enter only
through `resource-disjoint` children. `proof_replay_resource_event_facts_with_owner` walks the
resource tree:

- It requires each disjoint premise to be a traced fact.
- It recurses through `resource-safety`, `resource-scope` and `resource-call`.
- It accepts exactly the leaves below as carrying no facts.
- Any other kind fails closed.

<!-- inventory:resource-fact-free-leaves -->
| Kind |
|---|
| `resource-region-open` |
| `resource-region-close` |
| `resource-region-alloc` |
| `resource-region-bind` |
| `resource-sview-param` |
| `resource-region-alloc-discard` |
| `resource-region-return-alloc` |
| `resource-region-call-alloc` |
| `resource-region-rebind-alloc` |
| `resource-region-assign` |
| `resource-region-return` |
| `resource-region-param` |
| `resource-write` |
| `resource-move` |
| `resource-use` |
| `resource-join-move` |
| `resource-call-arg` |
| `resource-call-formal` |
| `resource-call-region` |
| `resource-call-result` |
| `resource-call-lend` |
| `resource-bind` |
<!-- /inventory:resource-fact-free-leaves -->

## Trust ledger

Line counts are as of this inventory. `scripts/test_kernel_inventory.py` checks the dependency
claims marked "(checked)".

| Tier | Modules | Lines | Role |
|---|---|---|---|
| Trusted kernel | `proof/kernel_core.elisa`, `proof/kernel_replay.elisa`, `proof/kernel_replay/*` | ~7.9k | Decides every certificate from arena terms alone. Calls no `proof_*` function defined outside the kernel (checked). |
| Trusted certificate admission | `proof/certificate_admission.elisa` | ~80 | Admits trace-certificate roots by kind and version tag. |
| Trusted replay adapter | `proof/replay.elisa`, `proof/replay/*` | ~2.4k | Binds certificates to goals and facts to traces; re-proves derived steps. Calls into the kernel through public entry points, and calls only the external helpers listed under limitation 1 (checked). |
| Trusted source adapter | `proof/kernel.elisa`, `proof/check/*`, `proof/resources/*`, `proof/expr/*` | ~18k | Lowers source to arena terms and emits boundary facts. Soundness depends on each boundary fact meaning what its row above says. |
| Trusted package reader | `portable/*`, `app/portable_io.elisa` | ~0.5k | Reads `elisa-proof-package-v1` files under exact schemas and hands every sequent to kernel replay. Trusted by `elisa-proof-replay` and by the correspondence checker (DESIGN.md, "Portable replay packages"). |
| Trusted correspondence checker | `correspondence/*` | ~1.2k | Re-derives a function's obligations from the parsed source by its own reference semantics and matches them against replayed theorems term by term (DESIGN.md, "Checked correspondence"). Calls only the kernel's public entry points, the package reader and the output helpers listed under limitation 5 (checked). It does not call the source adapter. |
| Untrusted search | `proof/linear/*` search, `proof/tactics/*`, `proof/tactic_json*.elisa`, `app/repair.elisa` | ~5k | Finds proofs. A tactic's `solved` flag and the solver's verdict are never authority; the kernel re-checks every result. |
| Presentation | `app/*` except repair | ~2.8k | Output and CLI. Fingerprints are binding guards only (limitation 2). |

### Host-side soundness-incident registry

`scripts/soundness_incident_registry.py` validates the confirmed-incident ledger and can determine
whether an exact persisted product is named by an incident for the exact semantic rule/version it
used. The match requires product kind, identity and SHA-256 as well as rule and semantic version;
cache/artifact schema labels do not participate. Invalid registries or malformed product metadata
raise an error, so callers must refuse reuse. This Python policy is not part of kernel replay and
does not currently gate the report-cache reader, declaration-artifact store reader, or portable
package replay path; those integrations and a complete rule-version inventory remain open R-009
work. The focused host-side regression is `scripts/tests/test_soundness_incident_registry.py`.

## Guarded arithmetic completeness rules

These rules reuse the ordinary `goal` certificate; they add no trusted fact or arena kind.

- **Linear disequality by denial.** After the premises and primitive goal pass machine-wrap
  guards, the producer temporarily assumes the equality complement of `a != b`. The existing
  linear disequality-refutation procedure must contradict an actual premise. Kernel replay
  independently constructs that complement and repeats the refutation, including goal safety.
  It does not accept the producer's contradiction flag or reinterpret wrapping arithmetic.
  `scripts/test_correlated_disjunction.py` covers correlated cases, a false stronger goal,
  a missing premise, and a wrapping goal. Portable controls reseal identities before checking
  that a genuine claim replays and a false wrapping claim is rejected.
- **Closed width-uniform OR goals.** `kernel_replay/closed_width_formulas.elisa` independently
  evaluates literal ring terms (`+`, `-`, `*`, unary sign) and Boolean comparisons at signed and
  unsigned widths 8, 16, 32, and 64. It accepts only truth at every width. Exact intermediate
  arithmetic must fit i64; typed literals, unknown terms, and ambiguous negative plain-literal
  payloads are excluded. A shared 512-visit budget covers all width evaluations and shared DAG
  paths; exhaustion refuses the rule. This is a closed-formula rule, not general modular
  arithmetic or a substitute for source typing. `scripts/test_closed_width_formulas.py` and the
  portable suite cover true uniform formulas and a resealed width-dependent false near-match.

The shared AST helpers listed below remain source-adapter dependencies; independent arena
evaluation does not remove their existing source-correspondence limitation.

## Known limitations

1. **Shared helpers.** Replay calls exactly the functions below that are defined outside
   `proof/replay`. The rows for `proof/linear` are a common-mode dependency on untrusted search
   code: a bug there affects the solver and the AST replay together. The kernel's own guard
   (`kernel_replay/safe_comparison_constants.elisa`) is independent, and every certificate also
   passes kernel replay. A shared bug can therefore make replay reject but cannot make the
   kernel accept. Moving these helpers into replay is tracked as a refactor, not a soundness fix.

<!-- inventory:replay-external-calls -->
| Function | Defined in | Tier |
|---|---|---|
| `proof_safe_comparison_constant` | `proof/linear/fixed_width_arithmetic.elisa` | untrusted search (shared) |
| `proof_has_ambiguous_integer_constant` | `proof/linear/fixed_width_arithmetic.elisa` | untrusted search (shared) |
| `proof_has_ambiguous_integer_constant_in` | `proof/linear/fixed_width_arithmetic.elisa` | untrusted search (shared) |
| `proof_closed_formula_at_width` | `proof/linear/closed_width_formulas.elisa` | untrusted search (shared) |
| `proof_closed_formula_width_uniform` | `proof/linear/closed_width_formulas.elisa` | untrusted search (shared) |
| `proof_expr_mentions_name` | `proof/expr/constant_arithmetic.elisa` | source adapter |
| `proof_expr_equal` | `proof/expr/ast_equal.elisa` | source adapter |
| `proof_quantifier_kind` | `proof/expr/ast_equal.elisa` | source adapter |
| `proof_kernel_expression_supported` | `proof/kernel.elisa` | source adapter |
| `proof_kernel_budget_note` | `proof/model/report_recording.elisa` | report model |
| `proof_kernel_report_append_allowed` | `proof/model/report_recording.elisa` | report model |
| `proof_internal_rebind_name` | `proof/check/internal_name_safety.elisa` | source adapter |
| `proof_closed_integer_arithmetic` | `proof/linear/fixed_width_arithmetic_integrated_helpers.elisa` | untrusted search (shared) |
| `proof_count_named_aggregates` | `proof/check/enum_value_types.elisa` | source adapter; aggregate identity lookup |
| `proof_ident_name` | `proof/expr/ast_equal.elisa` | source adapter |
| `proof_is_comparison` | `proof/expr/constant_arithmetic.elisa` | source adapter |
| `proof_loop_binder_value` | `proof/check/loop_range_facts.elisa` | source adapter; loop binder expression |
| `proof_payload_binder_types` | `proof/check/enum_value_types.elisa` | source adapter; pattern binder types |
| `proof_report_builtin_operator_impl_exists` | `proof/check/operator_witnesses.elisa` | source adapter; builtin operator override guard |
| `proof_signed_constant_at_width` | `proof/linear/fixed_width_arithmetic.elisa` | untrusted search (shared) |
| `proof_signed_type_width` | `proof/check/bounds_and_facts_integrated_helpers.elisa` | source adapter; signed machine width |
| `proof_source_expression_has_overloaded_operator` | `proof/check/source_operator_guard.elisa` | source adapter; overloaded operator audit |
| `proof_type_head_name` | `proof/check/flow_and_type_model.elisa` | source adapter; resolved type head |
| `proof_unsigned_type_width` | `proof/check/bounds_and_facts_integrated_helpers.elisa` | source adapter; unsigned machine width |
<!-- /inventory:replay-external-calls -->

2. **Scalar fingerprint encoding.** `proof_push_kernel_identity` (`app/runtime.elisa`) hashes some
   kinds (`field-init`, `resource-*`, `effect-*`) without their operand subtrees. Distinct goals
   can therefore share a `goal_fingerprint`. The fingerprint is a staleness guard only:
   - A targeted tactic run is replayed against the goal and facts regenerated from the imported
     source (`app/cli.elisa`), not against the fingerprint.
   - Certificate reuse requires exact `proof_expr_equal` of the goal and every fact.
3. **No floating point.** `float` terms are rejected until IEEE semantics, including NaN, are
   modelled.
4. **Boundary facts are trusted, not replayed.** A producer bug that emits a boundary fact for the
   wrong construct is outside the kernel's reach. The source-admission gate matrix (P1-05) and
   the checked correspondence (P2-02) narrow this. For a function that `--correspondence` reports
   `checked`, the boundary facts are no longer trusted: every hypothesis is a fact of the
   checker's own reference semantics, and the source adapter is not consulted.
5. **Correspondence checker dependencies.** The checker is a second reading of the source, so it
   must not share code with the adapter it audits. Outside its own modules and the kernel, it
   calls only the functions below.

<!-- inventory:correspondence-external-calls -->
| Function | Defined in | Tier |
|---|---|---|
| `proof_package_array_field` | `portable/package_reader.elisa` | package reader |
| `proof_package_build_nodes` | `portable/package_reader.elisa` | package reader |
| `proof_package_check_theorem` | `portable/package_checker.elisa` | package reader |
| `proof_package_index` | `portable/package_reader.elisa` | package reader |
| `proof_package_index_field` | `portable/package_reader.elisa` | package reader |
| `proof_package_malformed` | `portable/package_reader.elisa` | package reader |
| `proof_package_ok` | `portable/package_reader.elisa` | package reader |
| `proof_package_over_budget` | `portable/package_reader.elisa` | package reader |
| `proof_package_read_header` | `portable/package_reader.elisa` | package reader |
| `proof_package_read_kernel` | `portable/package_reader.elisa` | package reader |
| `proof_package_rejected` | `portable/package_reader.elisa` | package reader |
| `proof_package_string_field` | `portable/package_reader.elisa` | package reader |
| `proof_push` | `app/portable_io.elisa` | output |
| `proof_push_json_i64` | `app/portable_io.elisa` | output |
| `proof_push_json_string` | `app/portable_io.elisa` | output |
| `proof_package_input_preflight` | `portable/package_reader.elisa` | bounded package input preflight |
<!-- /inventory:correspondence-external-calls -->
