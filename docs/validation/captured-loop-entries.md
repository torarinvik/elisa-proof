# Captured for-loop invariant entry replay

`AudioVirtual.next_virtual` returns a loop with a header accumulator:
`for slot in 0..<MAX_SOUNDS |best: usize = MAX_SOUNDS| -> best`.
Its invariant entry had an initial `best == 32` fact, but replay's original
declaration lookup supported direct declarations and a limited while-loop
wrapper. It did not reconstruct this returned for-loop block.

Replay now authenticates that initial equality against the exact original
owner, returned block, header declaration, constant initializer and single
for-loop invariant. The consumer must match the original invariant expression
and all six root-position fields. Loop-invariant or loop-condition premises
exclude this entry path, preventing the initial equality from surviving
preservation or exit. Unknown scopes, imported operator environments,
shadowed integer types, ambiguous owners and unsupported wrapper shapes refuse.
No goal, contract or certificate protocol label changes.

The supported shape has one integer accumulator initialized to a resolved
constant, one sequential for binder and one invariant. This does not establish
general loop source coverage or whole-program certificate correspondence.

## Evidence — 2026-10-07

Compiler `63585c5f56bd3c18d9ff983503bac8f005df40b4`, matching runtime/parser,
strict O2 pair `f37be51f77cc4de78d6deccdc2bc5134`.

* Seven CLI controls pass both JSON routes: valid loop 4/4; invalid initializer,
  invalid update, stale equality/lower bound after the loop, wrong entry bound
  and a conditional invalid update are refused.
* The direct source-predicate harness passes O0 and O2: valid source plus six
  refusals for changed initializer, changed source offset, a return contract
  masquerading as entry, loop-state premises, duplicate owner and shadowed
  integer type. These minimal source records are not complete kernel certificates.
* Existing indexed-snapshot, source-call-result, guarded-call, source-admission,
  frame-source, frame-call and portable-frame controls pass. Source length and
  whitespace checks pass. Both source runtime probes are in the full matrix.
* AudioVirtual now replays **109/109** obligations with zero findings/gaps.
  The uncached engine sweep improves from 68/73 to **69/73**. Remaining files:
  `action_input_context`, `action_input_deadzone`, `audio_anim_events`,
  `sound_event_assets`.

Engine evidence under `build/validation`: `prover-captured-entry-final-build.log`,
`captured-entry-source-runtime.log`, `audio-virtual-captured-entry.json`, and
`proof-captured-entry-final-sweep.log`. The complete prover/shared/native gates
remain open.
