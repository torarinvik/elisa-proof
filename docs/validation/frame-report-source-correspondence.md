# Frame report correspondence to original source

The private `proof_direct_frame_report_matches_source` helper derives the complete
supported direct-event inventory from the original declarations/tokens/source.
It requires every source event in original order, one distinct attempt per event,
exact owner, kind and source ordinal, a full six-field source-position mirror,
zero facts and the expected certificate family. It independently replays each
root and compares the verdict to both attempt and obligation, including failures.
Successful attempts require distinct certificates with matching root, occurrence,
owner, family and fact-free shape. Additional unattached frame attempts or
certificates for that owner are rejected by independent family counts.

This check does not mark certificates replayed and is not enabled in the CLI.
Original source semantic admission, report invariants, source-context dispatch,
whole-report event coverage and broader nested/alias/callee effect mappings remain
required. It conservatively refuses ambiguous owners. Family counts use the leaf
owner name, so overloads require qualified owner identity before wider enablement.

The report-model probe exercises two valid recordings (four successes; five
successes plus one failed preservation event) and seven report mutations: wrong
source ordinal, wrong owner, substituted attempt, substituted certificate, omitted
obligation, extra attempt and extra certificate. O0 and O2 pass with compiler 96761822. The all-products strict O2 build
passes, generation b85b0766cfbb482592723c38a5d93493. Source admission matrix
(six malformed classes, twelve routes), invariant diagnostics and kernel
inventory (190 entries) pass. Contract-placement and condition-call fixtures
still report goal-attempt-coverage: production recording remains disabled.
Artifacts: engine build/validation/frame_report_source-O0/-O2 and
prover-frame-report-source-build.log. The integrated runtime matrix includes this
probe; focused results do not establish full implementation-plan completion.

## Source-context replay API

`proof_replay_certificates_with_source` first performs ordinary replay, then walks
the original declarations with a shared 4096-declaration and 64-level budget.
Only complete independently source-matched frame reports can set frame certificate
flags. Unmatched/orphan family records remain gaps. Traversal exhaustion revokes
all provisional frame flags; counters and completeness are recomputed. The
AST-only API continues to refuse this family and clears a prior source replay
result. The ordinary rule dispatcher is not widened. The shared attempt mirror
matcher accepts frame mirrors only for exact attempt/certificate association;
source replay checks their full occurrence positions and roots separately.
Zero-length fact spans must still be bounded and exactly associated.

The API requires callers to supply independently parsed original source context
and still apply semantic admission and report invariants. CLI producer integration
and full whole-report coverage remain open. The runtime probe now checks source
replay counts for both valid recordings and all seven mutations, plus AST-only
refusal before and after source replay. During development, the first O0 probe
found flag writes targeting copied foreach records; indexed report writes fixed
that failure. The corrected O0 probe passes. O2 also passes after fact-span and shared association checks. The final
all-products strict O2 build passes, generation
a2fa74389b2148b488174fed7d43f1e9; source admission matrix, invariant diagnostics
and 190-entry kernel inventory pass. CLI frame recording remains disabled, so
the two static frame-accounting repros still report goal-attempt-coverage.
Artifacts: engine build/validation/frame_source_api-O0/-O2 and
prover-frame-source-api-build.log.

## Structural ledger admission bridge

The existing source-postcondition inventory check rejected every non-postcondition
source tag, including newly recorded frame events. `report_frame_inventory.elisa`
now recognizes changes/preserves/allow/preserve tags only when there is exactly
one bounded AST owner, one associated attempt, matching owner and frame family,
matching proven/has-certificate state, an inert true mirror and zero facts. Owner
lookup shares a 4096-declaration budget and refuses depth/exhaustion/ambiguity.
Foreign owners and unknown tags remain rejected. This is structural validation;
it neither replays a frame root nor replaces original-source event coverage.
The AST-only replay API still refuses these certificates. Production static
frame events have not yet been replaced or attached, so their original accounting
failures persist.

The report-model probe passes at O0; its expanded O2 version adds foreign-owner
and unknown-tag invariant rejection (eight source replay mutation controls).
The existing reduced report-invariant runtime compiles and passes, ensuring the
standalone model remains supported. All-products strict O2 build passes,
generation 7ef40bfe119e42b385a3e53ef210c571. Source admission matrix, invariant
diagnostics and kernel inventory pass. Artifacts: engine build/validation/
frame_inventory_bridge-O0/-O2, report_invariants-frame-bridge and
prover-frame-inventory-bridge-build.log. Producer event attachment and CLI source
replay integration remain the next work; broad implementation scope is unchanged.

## Production producer and CLI integration

`proof_check_with_source_context` performs ordinary semantic preparation, then
bounded source frame lowering and per-event replay into a producer workspace.
No original bytes or compiler symbol table are retained. Supported owners are
prepared only when the whole direct inventory is known and nonempty. Workspace
rows and declaration traversal share explicit 4096 limits; exhaustion clears
all prepared owner mappings. Unknown mappings retain the existing checker.
Report reset clears the workspace between runs.

At the existing function frame phase, prepared events emit one attempt and
source-tagged obligation each, and one certificate per successful predicate.
Their original body/header/direct checks are replaced together, preventing
duplicate accounting. Active owner state is reset at function entry/exit; direct
write checks skip only the completely prepared owner. The CLI now uses this
source-context checker and independently source-bound certificate replay.
AST-only public checker/replay compatibility routes remain conservative.

The three CLI repros now have consistent admission accounting: allowed is proved
(3/3 obligations and certificates), outside is rejected (3 events/2 certificates,
frame-write-outside), and preservation is rejected (5 events/4 certificates,
frame-preserve-write). Failed events have goal-linked findings and no certificate.
`scripts/test_frame_source_cli.py` asserts full and summary JSON routes and runs
in the Python matrix. Composed producer/runtime controls pass at O0/O2; admission
mutation matrix, invariant diagnostics and 193-entry kernel inventory pass.
All-products strict O2 build passes, generation
fc86464d1b494b06b1b5e824f4701d47. Engine sweep remains 66/73 with the same seven
failures. Logs: engine build/validation/prover-frame-cli-build.log and
proof-frame-cli-sweep.log; artifacts frame_cli_runtime-O0/-O2.

Contract-placement and condition-call fixtures remain at goal-attempt-coverage:
their broader branches/calls/conditions are not yet a complete source inventory.
Nested, aliased, dynamic and callee-mapped effects, expression-bodied headers,
qualified owners, portable source-context replay, the full compatibility matrix,
compiler qualification and the broader engine implementation plan remain open.
