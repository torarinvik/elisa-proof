# Frame inventory with scalar body contracts

`contract_placement` previously retained 31 proven producer events but only 27
replayed certificates. Its direct frame function contains body-level requires
and ensure clauses, so the complete direct-event inventory conservatively
refused it. `frame_source_scalar_contracts.elisa` now reconstructs a bounded
call-free scalar comparison/Boolean grammar in those contracts without emitting
frame events for the logical predicates. Their proofs remain ordinary checker
obligations. The owner lookup retains the exact declared return type so `result`
references require a direct primitive scalar return type.

Supported atoms are integer/Boolean literals, direct primitive scalar formals,
and result in ensure clauses. Parentheses, comparisons, Boolean connectives and
not are supported. Work is shared across contracts with a 4096-node cap and a
64-level depth cap. Calls, arithmetic, fields, non-scalar types, aliases and
reference wrappers are not yet reconstructed. A bounded whole-declaration guard
refuses imported/implementation scopes and primitive type shadowing until their
operator correspondence is independently resolved. Unknown expressions still
invalidate the entire inventory; existing unsupported-owner checks remain intact.

The composed event probe passes 24 controls at O0/O2, adding body-frame contracts,
Boolean predicates, calls/arithmetic refusal, nominal operands, invalid result
context, primitive shadowing and implementation-scope refusal. Owner probes at
O0/O2 confirm declared return type retention and clearing after failed lookup.
Strict all-products O2 build passes, generation
7f7fc181b9bf425f9f8bf71b5b8a87f3. The full contract-placement fixture now proves
31/31 obligations with 31 replayed certificates, zero findings and no admission
invariant failure on full and summary JSON routes. Its regression expectation
checks that complete count explicitly. Condition-call positions still retain
30 producer events/14 replayed certificates and fail goal-attempt-coverage.

Frame CLI and portable frame regressions, malformed-source admission matrix,
updated invariant diagnostics and 193-entry kernel inventory pass. The uncached
engine sweep remains 66/73 with the same seven failures. Evidence: engine
build/validation/prover-frame-scalar-contracts-build.log and
proof-frame-scalar-contracts-sweep.log; artifacts frame_scalar_events-O0/-O2 and
frame_scalar_owner-O0/-O2. Broader contracts, operator/type resolution, arithmetic
writes, branches, aliases, dynamic places, callee mappings and full engine/compiler
qualification remain required by the original implementation scope.
