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
