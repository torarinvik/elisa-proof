# Resource disjointness premise scope

## Current replay boundary

`resource-disjoint` has no source offset or control-flow context. Its children are the producer's
current fact snapshot (`src/proof/resources/places_and_calls.elisa`). General trace validation can
authenticate a `branch-condition` against a matching condition somewhere in the owner body
(`src/proof/replay/boundary_branch_fact_sources.elisa`), but that alone does not establish that the
fact held at this resource event.

The current replay boundary closes that path conservatively. When validating a disjoint premise,
`proof_replay_kernel_fact_root_is_traced_with_stack` admits `global-constant`,
`global-constant-qualified`, `global-mutable-array-type`, `global-mutable-array-index-bound`, and
`const-enum-member-value` traces. A resource-only exception admits a body-leading `requires
left != right` when both names resolve to unique immutable by-value `usize` parameters, the
comparison has no source overload, and neither parameter is shadowed or touched anywhere in the
owner body. This narrow fact is stable for the entire function, so it does not need a resource
event source offset. Other entry preconditions, branch and loop facts, local assertions, and
derived traces remain rejected. The accepted global constant validator rejects references
shadowed by owner parameters or local declarations; the mutable-array fact validator checks the
exact global fixed-array declaration and rejects local shadowing. An index-bound trace additionally
requires the exact function precondition and rejects any body write, aliasing call, or shadow of its
by-value index parameter. The const-enum validator recomputes member comparisons from explicit
immutable variant tags. These premises describe immutable declarations, fixed array representation,
or an untouched scalar binding, so the independently replayed inequality remains valid across
assignments and control-flow joins.

Replay therefore keeps previously proved disjoint pairs for the whole resource trace. Clearing
them after writes, calls, shadowing binds, and joins was unnecessarily rejecting later uses of the
same stable theorem. The resource replay state no longer carries a fact-liveness bit or invalidates
these pairs at those transitions.

This boundary preserves soundness only while the premise allowlist remains restricted to stable,
source-validated declarations. The producer still clears its fact snapshot at additional boundaries.
There is a `proof_resource_clear_facts_at_position` helper, but it has no producer call sites, and
`resource-facts-clear` is not admitted by arena or source validation. Neither should be treated as
the safety mechanism for the current boundary.

## Expressivity work required

The narrow `requires left != right` case described above is admitted without a source event
position. Preconditions involving mutable or non-`usize` parameters, local assertions, and useful
resource separations based on branch facts still require binding each disjoint event to its exact
source occurrence and reconstructing which premises are active there. At that point replay must:

1. Authenticate the expression or statement whose resource transition needs the inequality.
2. Check premise provenance transitively, so a proof step derived from a branch fact remains scoped.
3. Track polarity for false `if` arms, earlier `elif` exclusions, match patterns and guards, and
   enclosing nested branches.
4. Prevent facts from a child scope escaping unless every joining path establishes them.
5. Mirror producer invalidation after writes, calls, moves, branches, loops, matches, and lexical
   scopes, or independently reconstruct equivalent source facts at each event.

Do not reject branch-derived facts globally as the final solution: a fact established independently
on every arm is valid after a join. Replay needs to distinguish that case from a fact that held on
only one path.

## Evidence and qualification

Relevant code paths include `src/proof/replay/certificate_validation.elisa`,
`src/proof/replay/boundary_branch_fact_sources.elisa`,
`src/proof/replay/resource_alternative_source_validation.elisa`,
`src/proof/kernel_replay/resource_events.elisa`, and
`src/proof/resources/places_and_calls.elisa`. This remains a source audit without runtime
qualification. The pin-matched compiler build could not run because the available Stage1 product
reports provenance v1 while the pinned compiler revision requires v5. A one-off build with the
older October 9 product reached parsing but rejected multiline guards already present in the proof
source; that result does not isolate the replay change.
