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
