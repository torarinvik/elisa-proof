# Original-source callee frame mapping — 2026-10-07

`frame_source_calls.elisa` resolves one exact original Call occurrence using all
source-position fields, a unique original owner and globally unique unshadowed
leaf callee. Traversal shares a 4096-node budget and refuses depth 64, local
binders and unsupported statement/expression scopes. No producer summaries or
reserved alias names establish call identity.

`frame_source_call_changes.elisa` independently reconstructs the callee policy,
lowers its complete supported direct body and replays every frame event before
mapping declared changes through original positional arguments to caller formal
places. Ordered parameter identity and field suffixes are retained, depth is
bounded to three and mapped paths are checked against original caller types.
Positional arguments carry one empty name per argument in the pinned parser;
nonempty names, mismatched cardinality, computed actual places, unsupported
callee bodies and failed callee policies refuse the complete mapping. A callee
without declared changes is accepted as empty only after complete direct-body
reconstruction and refusal of any assignment.

Fourteen runtime controls pass at O0/O2: bare places, reordered actuals, field
suffixes and nested-field concatenation, call-free readonly callee, and rejection
of wrong position, unframed writes, preservation violations, named arguments,
arity mismatch, formal callee shadow, duplicate callee, computed actual and
nested callee calls. The probe is included in the integrated runtime matrix.

Strict all-products O2 build succeeds using immutable installed compiler
96761822e6469efb929c5d50a804bb765f6bc3f7 and matching runtime/parser sources;
generation bcd875dfb459440bb58a85d46679dfc2. Existing source-frame CLI controls,
exact-count admission diagnostics and 193-entry/10-table kernel inventory pass.
Artifacts in the engine checkout: build/validation/frame_source_calls-O0 and
-O2, their compilation logs, and prover-frame-call-mapping-final-build.log.

This helper establishes callee effect mapping only. It does not establish
absence of effects in other caller expressions, complete caller inventories,
logical call preconditions or certificate/report admission. Integration must
retain conditional/short-circuit execution, original callee-clause identity,
all producer events and independently reconstructed mapped predicates. The
condition-call fixture still refuses goal-attempt-coverage with 30 original
obligations and 18 replayed certificates. The seven engine proof failures,
full prover matrix and broader implementation plan remain open.

## Caller allowance replay

`frame_source_call_replay.elisa` binds an allowance root to the complete original
caller policy and one exact mapped callee changes ordinal. It requires fact-free
whole-arena kernel replay, exact predicate operation/owner/formal cardinality,
ordered caller policy correspondence, and independently reconstructed actual
place. The runtime probe now has twenty controls, adding an accepted caller
allowance and rejection of wrong call position, out-of-range changes ordinal,
injected facts, weaker predicate relabelling and foreign owner. Complete caller
event accounting and preservation replay are still pending.

## Caller preservation replay

Caller preservation roots now bind one original combined header/body preservation
clause and one original callee changes ordinal. Fact-free whole-arena replay,
exact caller owner/formal count, preserved source path and mapped actual place
are all required. Four new controls accept disjoint preserved formals and reject
wrong changes ordinal, selection of a changes clause as preservation, and an
overlapping actual place. The runtime probe has 24 controls. The previous
allowance-facade all-products build completed as generation
b406c2a29a3640c9a9ca8d2e846b7357; existing frame CLI regressions pass. Complete
caller event inventory/producer integration is still pending, so no engine
proof failure is claimed repaired by these helpers.
