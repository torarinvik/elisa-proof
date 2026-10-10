# Signed source-local call snapshots — 2026-10-07

Successful signed scalar Call initializers now capture one source-local symbol
and reinstantiate their exact-site callee summaries under that symbol. Require
an unshadowed local, unique original callee return type and matching signed
width; conversion-only calls retain their existing separate path. Nested calls
are not made repeatable, purity classifications are unchanged, and source replay
still reconstructs each local binding, original Call position/arguments, callee
owner/ensure and proven requirements. Ordinary later writes and call-state
invalidation continue through the existing symbol/frame logic.

The minimized signed clamp chain proves/replays 13/13 obligations, while an
invalid count-minus-two bound rejects 12/13 with an open goal-linked finding.
The unsigned arithmetic/literal alias controls remain 7/7 and 5/5; wrong bounds,
wrong aliases and distinct invocation claims remain refused. Full condition-call
accounting and guarded-call controls pass. MotionOverlayPolicy now proves/replays
all 72 implementation-linked obligations with no findings. The initial uncached
engine sweep improves to 68/73; five failures remain: both ActionInput reports,
audio_anim_events, audio_virtual and sound_event_assets. The final same-width product passes strict all-products O2 build and the
focused regressions, generation 01a9c1dc48dc4ca3befeae4d70653e3e. Its uncached
sweep also passes 68/73 with the same five remaining failures.

Before implementation, committed prover main was merged (906e345d), retaining
platform-aware link/provenance changes and compiler pin 96761822. Two fixture
conflicts were resolved by retaining both platform and runtime-recipe inputs.
Follow-up d10e85d5 restores recipe files in the independent-root and source-race
fixtures. All 10 provenance tests pass, independent mocked builds use distinct
locks/snapshots/generations, and source/compiler races retain snapshot isolation
and fail-closed publication. Wasm-browser gains were already merged.

Evidence: engine build/validation/prover-signed-call-snapshot-build.log,
prover-signed-call-snapshot-final-build.log, signed-call-result-chain.json,
motion-overlay-signed-call-snapshot.json and proof-signed-call-snapshot-sweep.log.
The installed immutable compiler 96761822 with matching runtime/parser sources
is the qualification context. Full prover matrix, richer call/type/loop mappings,
shared/native gates, hosted qualification and the entire engine plan remain open.
