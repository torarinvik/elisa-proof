# Resource calls in default expressions

## Current replay boundary

The source call graph includes calls found in parameter defaults. Resource-call
production, however, checks a function's body and does not emit resource
transitions for its defaults. Replay keeps those default-call names in the
owner census while disabling resource-expression capture during that scan.

This mismatch is fail-closed. A source-call surplus can be accepted only when
the omitted name passes the resource-call omission classifier. That classifier
requires every same-named candidate to be a replay-checked pure, scalar,
region-free function, and rejects unresolved dispatch, opaque imports,
shadowing, and unsupported source shapes. A default call whose target can have
resource effects therefore prevents admission of that resource-safety root.
Source admission requires such a root for every non-lemma function, closing the
gap even though resource production checks only function bodies. The separate
default-call admission check requires unique resolution and no `requires`
clause; it does not establish resource purity.

The current behavior loses completeness: even an effectful default that is
never used can make the report inadmissible. The reviewed source paths show no
way for a resourceful default call to be accepted without a resource
transition under this restriction.

## Expressivity follow-up

To admit resourceful defaults, model their effects at the call site where an
argument is omitted. Expand the selected default using the caller's exact
argument-to-parameter mapping, bind each nested call to its parser-owned
source position and declaration identity, and give its transitions stable
invocation identities. Keep these call-site effects distinct from the
callee-body resource summary. Until that representation is validated,
resourceful default calls must remain inadmissible; removing their names from
the census would reopen an omitted-effect gap.

Relevant implementation anchors: `src/proof/replay/source_call_api.elisa`,
`src/proof/replay/resource_call_site_validation.elisa`,
`src/proof/replay/resource_call_name_counts.elisa`,
`src/proof/replay/resource_call_shadow_validation.elisa`,
`src/proof/replay/resource_call_pure_source.elisa`,
`src/proof/model/report_effect_containment_admission.elisa`,
`src/proof/model/report_default_call_requires_admission.elisa`, and
`src/proof/resources/statement_checker.elisa`.

## Follow-up source audit

A second source-only red-team review of the current resource-call replay path
found no concrete forged omission or mismatched-event bypass. Owner coverage
builds the source-call snapshot, rejects incomplete or unresolved dispatch,
requires unique event byte offsets, and reconciles calls and events by name.
Every emitted event must then bind to one exact parser-owned source position,
callee declaration, and module; ordinary calls also authenticate the linked
summary against that exact declaration. Argument counts, argument/formal names,
expressions, and region mappings are checked against the AST. Unsupported forms
or dispatch make the owner unresolved and fail coverage.

Zero-argument ordinary calls require an exact zero-argument source call and
matching summary. A `resource-call-lend` is rejected if the callee has no
reference formal. Event child shapes are validated separately in
`src/proof/kernel_replay/arena_child_validation.elisa`. This is source inspection,
not a compiler or runtime validation; it does not change the conservative
default-call restriction above.

The owner census was reviewed separately. It enumerates parser-owned function
nodes through nested modules/scopes and requires exactly one `resource-safety`
attempt for each `(name, line, offset)` identity. Every attempt must be
producer-proven, point to a replayed certificate, and link to a kernel root
whose kind, operator, name, line, and offset match that source identity
(`src/proof/model/report_effect_containment_admission.elisa:135-192`). The
report-wide count rejects extra resource attempts. Replay then resolves the
owner to exactly one declaration at the same name/line/offset and checks its
module (`src/proof/replay/resource_call_source_validation.elisa:323-331`). This
census runs in checked-view admission against the issued source snapshot after
replay flags are reset (`src/proof/replay/api.elisa:321-348` and
`src/proof/replay/api.elisa:473-493`). This closes the reviewed root-omission
and duplicate-attempt cases at source level; compiler and runtime qualification
remain outstanding.
