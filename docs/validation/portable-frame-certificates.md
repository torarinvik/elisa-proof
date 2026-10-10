# Portable frame predicate certificates

The first production frame package exported only its resource certificate: frame
roots had no canonical identity and were omitted by the existing unknown-identity
export policy. `portable_io.elisa` now identifies frame-field, frame-place and
frame-policy nodes. Place identities bind formal ordinal and ordered field labels;
policy identities bind owner/version/operator, formal count, partition split,
actual place and every ordered policy place. Arena indices remain excluded.
The Python resealing oracle independently uses the same structural encoding.

The portable checker recognizes frame-spec/frame-allow/frame-preserve and requires
the corresponding exact kernel operation and zero hypotheses. It dispatches to
the frame policy kernel through a bounded workspace graph validator. The iterative
walker now traverses actual places and policy/field children; the first package
probe exposed the missing traversal. Dedicated workspace controls cover positive
replay, failed allowance and injected facts at O0/O2.

Portable replay retains its existing explicit trust record: source correspondence
and hypotheses are adapter-supplied, fingerprints are identity hints, and source
is not authenticated. It proves the exported source-neutral predicate, not that
an arbitrary supplied policy describes the source program. The CLI independently
checks original-source correspondence and complete supported event inventory
before export. Package replay checks every declared theorem; it does not establish
whole-program source obligation coverage.

`scripts/test_portable_frame.py` requires all five certificates from a positive
changes/preserves fixture, compares every canonical identity with the Python
oracle, and checks relabelling, unresealed identity changes, resealed false
allowance/preservation and injected hypotheses. The failed allowance/preservation attempts remain absent from exports, while
their independently replayed sibling certificates export as valid theorem
subsets under the existing source-admissible package contract. The test is included in the Python matrix. All-products strict O2 build passes, generation
2c120cc80c774876b7d8f06f766b3ba6. The frame package probe retains/replays all
five certificates, rejects thirteen mutations, and checks valid sibling subsets
for the two failed frame fixtures. Valid arena mutations of formal count,
partition split, field label, place ordinal and child order specifically fail
with statement-mismatch, proving identity binding before predicate replay.
The existing portable suite passes eighteen positive packages, semantic/schema
attacks, structured resource controls and 576 raw byte mutations (594 decoder
runs, no crash or partial theorem replay). Workspace controls pass at O0/O2.
CLI frame regression, malformed source admission, invariant diagnostics and
193-entry kernel inventory pass. Fresh engine sweep remains 66/73 with the
same seven failures. Evidence: engine build/validation/prover-portable-frame-build.log,
portable-frame-final-suite.log and proof-portable-frame-sweep.log; artifacts
frame_policy_workspace-O0/-O2. Broader frame source mappings,
full compiler/engine qualification and the implementation plan remain open.
