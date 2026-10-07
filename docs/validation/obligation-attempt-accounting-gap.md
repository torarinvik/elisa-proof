# Source obligation and branch attempt accounting gap

The strict report-invariant runtime reaches status 34 on current source:
removing one open ledger event and decrementing the total leaves two open
attempts attached to one event, yet source admission accepts the report.
The existing adversarial assertion is retained.

The old attempts <= obligations rule cannot be restored: one source obligation
can legitimately have multiple branch attempts. The new
`report_branch_accounting_runtime.elisa` validates that positive case with one
proven ledger event, two attempts and two certificates. Its strict O0 compile,
native link and execution pass. It is wired into the standard matrix.

Required fix: record the accounting event identity for each attempt and validate
that association independently during admission. Permit many attempts per event,
permit unsupported events without attempts, refuse attempts for deleted events,
and reconcile event outcomes with their associated path results. Carry this
association through report serialization/cache/portable package boundaries and
mutation controls. Do not substitute a loose aggregate count check.

This is an open task. The positive control establishes the legitimate branch
case; it does not authenticate arbitrary claimed event identities. Production
admission has not been changed in this slice. Engine validation artifacts:
`report-invariants-probe` (status 34), `report-branch-accounting` (status 0).

An attempt-span prototype records the contiguous attempts preceding each
accounting event, including empty spans for unsupported events. Its checker
rejects gaps, overlaps, out-of-range spans and trailing orphan attempts.
The omitted-open-event mutation advances past status 34 under this prototype.
Integration is incomplete: synthetic source-coverage fixtures also introduce
extra branch attempts and must preserve their intended event associations.
The prototype patch is retained in engine build/validation as
`obligation-attempt-span-candidate.patch`; production source was restored.
A separate minimal nested-array clear control returns the expected count 2,
so the suspected reset defect was not reproduced and is not claimed.

The span implementation is now integrated. Each event records `attempts_start`
and `attempts_count`; the recorder consumes attempts since the previous event.
Admission requires ordered contiguous spans with safe bounds and complete
coverage. Empty event spans and multiple attempts per event remain supported.
The strict report-invariant harness now passes, including its omitted-open-event
control. The branch control passes and rejects missing trailing coverage,
nonzero first start and an out-of-range count, then accepts the restored span.

Both proof/replay products build with compiler 96761822. An uncached engine
sweep retains 66/73, with the same seven failures. Conditional, guarded-call,
deterministic-call and portable disjunction controls pass. The source-admission matrix subsequently passed after its stale focused-goal
expectation was aligned with the documented complete-source CLI contract
(398b2c45). The full prover matrix remains failing. Logs: `prover-attempt-span-build.log`,
`proof-attempt-span-full-sweep.log`, `source-admission-span.log` in engine
build/validation. The new spans are internal report accounting metadata;
portable replay retains its separate source/certificate validation boundary.
Further resealed-metadata mutation and outcome-association coverage remain open.

## Static frame event evidence gap

The new admission diagnostic isolates goal-attempt-coverage for a minimal
void-returning frame write (`test/repro/frame_accounting_allowed.elisa`).
There are three successful events: a valid changes clause, an allowed write
and resource safety. Only resource safety creates a goal/certificate, which
replays. The report correctly remains refused despite 3/3 producer counters,
no source diagnostics, no findings and no replay gaps. This is independent
of postcondition and branch accounting.

The outside-frame control has 3 events, 2 marked successful, one replayed
resource certificate and frame-write-outside. The preservation control has
5 events, 4 marked successful, one replayed resource certificate and
frame-preserve-write. Both are semantically clean and refused.

The correction needs checked evidence for each static frame event, bound to
its source frame, actual write/call place, formal owner and policy operation.
A replayed resource certificate alone checks resource transitions; it does
not establish a changes/preserves policy. Do not remove these events, replace
them with literal-true certificates, relax the proven-attempt lower bound or
associate them with unrelated resource evidence. Header and body frame specs,
direct/dynamic writes, call frame mapping and preservation checks share this
accounting path and all need coverage. False frame containment and overlapping
preservation controls must remain refused after accepted checks replay.

The pending certificate rule now has a source-neutral frame relation model
in `kernel_replay/frame_policy_model.elisa`. Places use caller parameter
ordinals and canonical zero-to-three field paths. It checks the entire bounded
policy before looking for containment, and refuses writes overlapping a
preserved ancestor or descendant. A strict O0 standalone compile/link/run
passes 13 controls: exact and ancestor containment, sibling preservation,
outside-frame writes, ancestor/descendant overlap, foreign/out-of-range
parameter identity, malformed trailing policy entries, empty changes and
over-budget parameter count. Runtime artifact: engine
`build/validation/frame-policy-relations`. Certificate encoding, source
correspondence, replay dispatch and producer event integration remain pending;
this model alone is not used to admit any source theorem.

The frame-place arena format has a canonical decoder in
`kernel_replay/frame_policy_places.elisa`: versioned frame-place nodes carry
parameter ordinals and up to three ordered frame-field leaves. All unused
metadata must be zero/empty, empty paths have zero child offset, and selectors
must point backward to canonical leaf nodes. A strict O0 compile/link/run
passes 16 controls including field/whole-place round trips, cycles, foreign
parameters, truncated child tables, invalid roots, unknown versions, metadata
mutation, noncanonical empty paths and over-depth paths. Runtime artifact:
engine `build/validation/frame-policy-places`. General arena admission and
source certificate dispatch remain pending; the decoder is not proof of the
source origin of a supplied place or policy.

A bounded frame-policy arena evaluator now checks versioned spec, write and
preservation nodes against canonical place records. It checks policy partition
counts, both bounded lists, backward edges, actual place identity and every
entry before evaluating containment/overlap. A strict O0 standalone
compile/link/run passes 16 controls spanning genuine claims, wrong containment,
preservation overlap, malformed/truncated tables, cycles, malformed operation
partitions, unknown operations/versions and budget refusal. All three frame
runtime probes are now included in the primary matrix's integrated kernel
runtime script. General arena dispatch, source binding and producer event
certification remain pending. No source theorem is admitted by this addition.
Artifact: engine `build/validation/frame-policy-certificates`.

General arena admission now recognizes the three canonical frame node kinds
and checks their exact child kinds with backward edges. The dedicated public
`proof_kernel_replay_frame_report_checked_arena` validates the entire arena,
refuses all supplied facts and then evaluates the frame policy. Frame nodes
remain non-propositions: ordinary goal replay refuses them even when the caller
supplies the policy itself as an assumption. The expanded strict O0 runtime
probe passes 24 controls, including full arena admission, ordinary-proposition
refusal, injected-fact refusal, false policy and cyclic-child refusal. The
kernel inventory passes ten tables and 188 entries. Runtime artifact: engine
`build/validation/frame-policy-arena`. Source-bound certificate dispatch and
producer event lowering are still pending; the mathematical frame relation
verdict does not authenticate any source frame declaration or write.

The committed 976caffe all-products build completes successfully with compiler
96761822. Admission diagnostics, all six malformed-source classes across twelve
routes and the ten-table/188-entry kernel inventory pass on that product. The
full adversarial `examples/kernel_arena_runtime/main.elisa` probe compiles
strictly at O0, links and exits zero, covering the existing resource, tactic,
quantifier, provenance and arithmetic arena controls. The uncached engine
sweep remains 66/73, with the same seven failing rows. Logs/artifacts: engine
`build/validation/prover-frame-arena-integrated-build.log`,
`frame-integrated-arena-controls` and
`proof-frame-arena-integrated-sweep.log`. Source admission still rejects static
frame events without evidence; these qualification results do not close that
source-bound integration requirement or the full compatibility matrix.

The source-binding layer now has an independent AST place decoder in
`replay/frame_source_places.elisa`. It reconstructs formal ordinals and ordered
field paths without reading producer ProofFramePlace values. It validates the
entire bounded formal-name list, including unrelated duplicates/empty names,
and refuses unknown roots, indexed/computed expressions, paths beyond three
fields and exhausted AST traversal. The strict O0 source AST runtime probe
passes 13 controls, including formal reordering and the exact traversal budget
boundary, and is included in the regular runtime matrix. Artifact: engine
`build/validation/frame-source-places`. Obtaining those formals from the exact
source owner, checking actual declared policy and field/type correspondence,
and integrating certificate/event admission remain pending. The decoder by
itself does not authenticate the caller-supplied formal-name list.

### Exact source owner lookup

`replay/frame_source_owners.elisa` derives ordered formal names and body statements
from a unique function name plus declaration line in the independently bound AST.
It rejects duplicate matches, malformed formal names, more than 64 formals,
64-level traversal exhaustion and a cumulative 4096-declaration budget exhaustion.
A failed lookup returns empty outputs, including when an earlier match existed.
The source file identity and qualified owner identity still require admission checks.

The parser-backed `examples/frame_source_owners_runtime.elisa` passes six controls
at strict O2 with compiler 96761822: exact source/formal order, wrong line, wrong
name, duplicate owner with cleared outputs, and depth exhaustion. The same O0
executable crashes in main (EXC_BAD_ACCESS); increasing linker stack size did not
resolve it. This probe is not yet in the runtime matrix and the new lookup is not
yet imported into production replay. Investigate the O0 lowering failure before
claiming optimization-independent qualification. Policy/type correspondence and
certificate/event admission remain open. Artifact: engine
`build/validation/frame-source-owners` (O2, exit 0).

Follow-up: the O0 crash was isolated to the probe's duplicate-array construction
using two `duplicate.extend(&file.top_decls)` calls. Replacing these with individual
`push` operations preserves the duplicate-owner negative and passes at O0. Added
exact 4096-declaration acceptance and 4097-declaration refusal after a valid early
match, with empty outputs on refusal. All eight controls now compile, link and run
(exit 0) at O0 and O2 with compiler 96761822. The owner probe is included in the
regular runtime matrix. The original extend lowering failure is not repaired by
this fixture change; production source admission remains unchanged. Artifacts:
engine `build/validation/frame-source-owners-o0` and `frame-source-owners`.

### Ordered source body policy

`replay/frame_source_policy.elisa` reconstructs top-level body changes/preserves
clauses from the unique source owner, retaining kind, formal ordinal, ordered
field path and complete AST position. It rejects any malformed clause without
returning a partial policy, caps statements at 4096 and clauses at 64, and does
not use producer frame metadata. Parser-backed controls pass at O0 and O2 with
96761822, including ordered clauses/positions, wrong owner line, a foreign root
after a valid clause, exact 64-clause acceptance and 65-clause refusal. The probe
is in the runtime matrix; artifacts are engine build/validation/frame-source-policy
and frame-source-policy-o2. This is source reconstruction, not source theorem
admission: header clauses, type/field validation, source identity/qualified owner,
write-site mapping and certificate correspondence remain required. Production
replay does not yet import these helpers.

### Body policy to arena correspondence

`replay/frame_source_correspondence.elisa` compares the complete independently
reconstructed body policy against canonical frame-policy write lists: exact owner
name, version, parameter count, list cardinality, changes/preserves partition,
ordered formal ordinals and field paths. It rejects forward place references and
malformed canonical places. The expanded parser-backed policy probe passes at
O0 and O2, including a matching certificate list and swapped partition contents,
wrong partition boundary and altered formal ordinal negatives. This helper only
establishes body-list correspondence; write-site/source identity/type validation
and signature policy remain separate obligations. Parser signature clauses are
stored in side-table rows rather than body Contract nodes, so header handling
requires independent token/source reconstruction before production integration.

### Source direct mutation targets

`replay/frame_source_writes.elisa` independently finds a unique top-level `<-`
assignment by all six source position fields in the exact owner body, decodes its
formal-rooted target, and rejects local binders with the same root spelling. It
uses no producer write or shadow metadata. Bounded owner/body traversal, unknown
roots, indexed paths, wrong owners, forged positions and ambiguous matching
assignments fail closed. Parser-backed controls pass at O0 and O2 with compiler
96761822: direct field mutation with correct formal ordinal, unknown root, typed
local shadow, binding-assignment shadow, indexed target, plus wrong owner and
changed-column controls for each case. Artifacts: engine build/validation/
frame-source-writes and frame-source-writes-o2. Included in the runtime matrix.
This helper does not yet cover nested control flow, compound mutation operators,
aliases, mapped callee writes or dynamic indexes, nor does it validate field types.
Those paths and header reconstruction remain part of the full frame admission
work; no production admission rule has been loosened or replaced.

Direct write follow-up: all eleven parser compound operators (`+=`, `-=`, `*=`,
`/=`, `%=`, `^=`, `|=`, `&=`, `<<=`, `>>=`, `?=`) now use the same exact source
target reconstruction as `<-`. The operator whitelist continues to exclude `=`
bindings and non-assignment tokens. `direct_write_matches` binds the reconstructed
source target to the canonical frame policy's actual place with exact formal
count, ordinal and ordered field path, rejecting foreign owners and forward roots.
The expanded parser-backed probe passes at O0 and O2 for all twelve mutation
spellings, source negatives, forged positions/owners and altered certificate
formal ordinals. This establishes target correspondence only: it does not prove
write authorization or authenticate header policy/source file identity. Nested
flow, alias/type mapping and production certificate admission remain open.

### Production compilation of source reconstruction helpers

The replay facade now imports all five frame source reconstruction modules. The
all-products strict O2 build succeeds with compiler 96761822 (generation
`aaf92589dee5450b8922c22655d4705a`); source admission still refuses six malformed
classes on all twelve CLI routes, admission diagnostics retain both static-frame
accounting refusals, and the kernel inventory matches ten tables / 188 entries.
The fresh uncached engine sweep remains 66/73 with the same seven failing rows.
Logs: engine build/validation/prover-frame-source-integrated-build.log and
proof-frame-source-integrated-sweep.log. Importing these helpers does not enable
a frame certificate family or alter admission.

Next integration requirements, in dependency order: independently retain/rebuild
signature frame clauses from source tokens (the current report retains AST and
annotations but no source token stream); validate formal/field types and qualified
owner identity; compose policy-list and exact-write correspondence with the
fact-free kernel rule; add producer certificate lowering and bind every static
frame event to its own matching attempt; then extend nested/alias/dynamic/callee
write mappings and run the full compatibility matrix. Header metadata must not
be silently omitted or accepted solely because a producer annotation claims it.

### Exact source signature bounds

Owner reconstruction now also returns the exact AST def-keyword position.
`frame_source_headers.elisa` locates the unique corresponding Def token and
checks actual keyword/name bytes, source span bounds, monotone signature spans,
matching parentheses/brackets/braces, a 64-delimiter depth cap and a 4096-token
signature budget. It requires a top-level colon rather than consuming another
declaration or body. Tokens/source must still belong to the independently checked
file identity; this helper does not authenticate a caller-supplied token stream.

Eight parser-backed controls pass at O0 and O2 with 96761822: exact header bounds,
wrong owner/line, out-of-bounds token, mismatched delimiter, missing colon and
duplicate exact Def span. Existing owner, policy and write probes were recompiled
and pass at O0 with the extended owner result. Header probe added to the runtime
matrix. Artifacts: engine build/validation/frame-source-headers and
frame-source-headers-o2. Header clause decoding remains next; the header helper
is not yet imported into production replay. The production owner API changed,
so a fresh full build is still required before qualifying that revision.

### Header paths and combined source policy

`frame_source_header_policy.elisa` independently decodes ordered comma-separated
changes/preserves formal paths from the bounded signature token stream, retaining
each target's full source span. It recognizes clause boundaries, skips grouped
non-frame payloads and refuses unknown roots, indexed/computed paths, malformed
targets, excessive field depth and clause count. `source_policy` combines header
then body clauses and checks both 64-place partition limits without returning
partial results. Expression-bodied signatures are explicitly refused by this
helper until their signature delimiter is modeled. Source bytes/tokens still
require independent identity binding; semantic field/type validity is separate.

The expanded header probe passes at O0 and O2 with 96761822, including mixed
clauses, whole/nested/comma targets, source positions, unknown/indexed/computed
paths, expression-body refusal, header/body order, 64 changes plus one preserve
acceptance, and a 65th change refusal. Both header modules are now in the replay
facade. The all-products strict O2 build succeeds, generation
`c211196c42f343b98a63a8bd8497d8ed`; admission matrix and invariant diagnostics
pass, kernel inventory remains 10 tables / 188 entries, and the uncached engine
sweep remains 66/73 with the same seven failures. Logs: engine build/validation/
prover-frame-header-source-build.log and proof-frame-header-source-sweep.log.
No new frame certificate family is admitted yet. Next: combine full source policy
with arena correspondence, validate actual formal/field types and qualified owner
identity, and connect each static event to a matching checked frame attempt.

### Full policy list correspondence

Arena list matching now shares one bounded canonical comparison for body-only
and complete header/body policies. `source_lists_match` reconstructs both source
policy regions before comparing every place and partition; a body-only match is
not a substitute for it. Header probe controls reject omitted header changes and
swapped changes/preserves contents, while accepting the exact combined policy.
Both header and prior body policy probes were compiled/linked/run at O0 and O2
with 96761822. All-products production build succeeds, generation
`5f96da6425444c26b903838d36d05e00`. Admission matrix, invariant diagnostics and
10-table/188-entry kernel inventory pass. Fresh engine sweep remains 66/73 with
the same seven failures. Logs: engine build/validation/prover-frame-full-policy-build.log
and proof-frame-full-policy-sweep.log.

Remaining admission integration must supply the independently parsed source and
token buffer to replay, not a producer-authored policy row. The CLI has source
bytes and lexer tokens at replay time; the existing AST-only proof_check API
does not retain them. A source-bound replay entry point can receive that context
without treating copied report annotations as authority. Formal/field type and
qualified-owner checks, nested/alias mapping, and per-event frame certificate
production/admission remain open.

### Source nominal field typing

Owner reconstruction now retains ordered formal type expressions from the exact
source declaration. `frame_source_types.elisa` validates canonical formal ordinals
and field paths against unique source struct/alias declarations, unwraps reference/
mutability/storage/refinement wrappers, follows nested member types, rejects
duplicate fields/types and cyclic aliases, and shares a 4096-step declaration/member
budget across the whole path. Owner body size is checked at 4096 statements before
copying it; exhaustion clears all returned arrays, including formal types.
Qualified/generic/tuple type identity and mutation permissions remain separate
checks; source semantic admission is still required. This helper is not yet used
by a frame certificate admission rule.

Parser-backed type controls pass at O0 and O2 with 96761822: aliased reference to
a nested nominal field, missing field, scalar field access, malformed path, wrong
owner line, ambiguous type, cyclic aliases, duplicate fields, cumulative budget
exhaustion, whole formal and out-of-range ordinal. Owner body 4096/4097 boundary
controls also pass at O0/O2. Existing owner/policy/write/header probes were
recompiled at both profiles after adding the formal type result. Type probe added
to the runtime matrix; artifacts use engine build/validation/
frame_source_types_runtime-O0 and -O2, and frame_source_owners_runtime-O0/-O2.

All-products strict O2 production build succeeds, generation
`892a7cfc2b544babac9a9963f52969dd`. Source admission matrix and invariant diagnostics
pass; kernel inventory remains 10 tables / 188 entries. Fresh engine sweep remains
66/73 with the same seven failures. Logs: engine build/validation/
prover-frame-source-types-bounded-build.log and proof-frame-source-types-sweep.log.
Next integration must compose full source policy, typed paths, exact source writes
and the fact-free kernel rule using independently parsed source context, then bind
each frame event to its own matching certificate attempt.

### Composed direct write replay boundary

`frame_source_admission.elisa::direct_write_replays` requires zero facts, the full
canonical arena/kernel frame rule, complete independently reconstructed header/body
policy lists, declared field types for every policy place, and the unique exact
source mutation target with matching type/ordinal/path. Its caller must supply
independently parsed, semantically admitted source and token context with a checked
identity. This helper does not itself admit a report or create a certificate family.

Nine parser-backed controls pass at O0 and O2 with 96761822: valid direct write,
injected facts, forged source position/owner, changed source target, changed source
policy, invented preserve list, missing declared field and omitted source preserve
clause. Probe included in the runtime matrix; artifacts: engine build/validation/
frame_source_admission_runtime-O0 and -O2. All-products strict O2 build succeeds,
generation `fee71c1752164967b0082219059991aa`; source admission matrix/invariant
diagnostics and kernel inventory pass. Engine sweep remains 66/73 with the same
seven failures. Logs: engine build/validation/prover-frame-source-admission-build.log
and proof-frame-source-admission-sweep.log.

Per-event integration must preserve the existing separate allowance and preservation
checks: the current `write` kernel rule proves their conjunction, so it cannot
replace a successful allowance event when a distinct preservation event correctly
fails. Add a changes-membership predicate with checked complete policy metadata,
bind preservation predicates to the exact source preserve list, and bind spec
predicates to exact source clause spans. Retain all existing events and diagnostics,
then wire source-context replay and producer certificate attempts. Qualified owner/
type identities, nested/aliased/dynamic/callee mappings and complete event inventory
remain required before claiming the static-frame accounting gap closed.
