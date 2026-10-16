# Global field resource admission gap

**Status (2026-10-16): source audit; field-place replay is not qualified.** The compiler's
`Global.Read`/`Global.Write` permission classification is separate and already covers mutable
fields of plain global aggregates.

## Current boundary

The proof resource checker models per-function bindings. `proof_resource_check_var` can decode a
mutable borrow such as `&permission_record.value`, but then looks up the place root in that local
binding table. A global root is absent, so it emits `borrow-source-opaque` and records an opaque
binding. Replay also refuses non-value `resource-bind` events in
`proof_replay_resource_local_borrows_absent_at_with_work`; source-bound local reference bindings
are therefore a prerequisite, not just a global-name lookup. These checks conservatively prevent
such a function from being accepted as proved.

For a direct write, `proof_resource_check_write` looks up the root in the local binding table.
Replay's resource-write validator requires a nonzero binding witness, and the source coverage path
currently authenticates local/formal writes rather than global field places. The producer now
records a failing `resource-write-opaque` obligation when a write has no tracked root or targets
storage outside the function resource frame; lookup exhaustion records a resource-analysis budget
failure. This prevents a report from claiming successful resource replay after silently skipping
such a write, but it does not validate the write's field identity or permit successful proofs of
global field-place operations. The grant harness therefore checks only semantic permission
diagnostics for its global field positives and negatives; it does not assert successful proof
replay for those cases.

The failure blocks whole-report source admission. `proof_resource_add_failing_obligation` records a
false proof obligation and a finding; the latter increments `report.results.failed`. Checked-view
admission requires both zero failures and equality between producer-proven obligations and total
obligations for `source_checks_complete`, and report-level source completion includes that flag.
`proof_checked_view_source_admissible` therefore returns false for the report. Certificate replay
status remains separately queryable as a kernel-only result and does not itself admit the source.

The theorem catalog also exposes a narrower claim for each theorem. A resource finding attributed
to that lemma makes its lemma-finding summary unclean, so that lemma cannot be reported as verified.
An unrelated function's resource failure may leave an independently verified theorem row available;
the theorem row is scoped to that theorem's source goals, facts, declaration identity, and replayed
certificates. It does not make the full report admissible. Consumers that need a whole-source result
must use the top-level report admission (or package admission), not an individual theorem row.

## Source identity audit

Globals are represented in parsed source as `Ast::Decl.Const(name, type, initializer,
is_global, position)`, not as a separate global declaration variant. The resource place encoder
reduces a field/index target to its root spelling, and `proof_resource_lookup_with_source_work`
only resolves names in the function's local/formal binding table. The existing static-scope data
is for qualifying immutable constant values; it does not identify mutable global storage.

Replay has a source-position index for local resource bind/use/write events. Its source walk
annotates writes only when a local or formal binder resolves the target root; an unbound name is
not thereby authenticated as a global. The global mutable-array validator has a separate source
lookup for annotated fixed arrays, but its root and annotation rules do not establish general
global field identity or mutability.

Kernel replay also requires each `resource-write` root to resolve to a slot in its replay binding
table and its `auxiliary` value to match that slot's authenticated `resource-bind` event. A global
declaration key cannot safely stand in for this local slot witness. Global admission needs a
source-derived storage entry in replay state, with an explicit relationship to local aliases; a
synthetic local bind would make local shadowing and alias overlap ambiguous.

A safe first admission tier needs the same source key on both sides: file identity, enclosing
module path, global declaration position, and the validated projection path. Replay must resolve
that key from declarations and reject ambiguous same-spelled rows. Global borrows and paths that
load references remain unsupported until their binder and scope events also receive source
identities; the direct-write tier must not imply those capabilities.

## Work required

Supporting global field places safely needs the producer and replay to derive the same bounded
storage identity from source declarations. That identity must distinguish a global declaration
from a same-spelled local, validate the projected field path and mutability, and remain stable
across borrow and write events. The replay must also source-bind reference declarations and scopes
instead of applying the current blanket refusal. It needs reverse source coverage for global writes
as well as exact event validation. Replay must reject missing, duplicate, shadowed, malformed, or
over-budget source rows. A spelling-only root or a producer-authored binding event is not enough.

Until that source-derived identity and event census exist, keep global field borrows fail-closed and
do not claim the field-place cases are independently replayed. This gap is separate from the
compiler's already-covered `Global.Write` classification.

Relevant code: `src/proof/resources/statement_bindings.elisa`,
`src/proof/resources/region_flow.elisa`, `src/proof/resources/places_and_calls.elisa`,
`src/proof/replay/resource_write_source_validation.elisa`,
`src/proof/replay/resource_write_coverage.elisa`,
`src/proof/replay/resource_binding_identity_validation.elisa`, and
`scripts/test_global_mutable_grants.py`. The static guard in
`scripts/test_resource_binding_identity_source_guard.py` now also pins the
opaque-write obligation, opaque-borrow binding state, and replay refusal for
non-value local bind events. It follows those failures through report findings,
producer-obligation accounting, and checked-view source admission. This guards
the current fail-closed boundary; it does not add declaration-derived identities
or global field replay support.

No build or runtime test was run; current compiler validation remains held by the RSS gate.
