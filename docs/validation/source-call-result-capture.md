# Source-local capture of one call result — 2026-10-07

Non-total-pure unsigned call results retain their reserved SSA snapshots. The
producer additionally records the exact original Call instantiation of each
applicable summary (excluding old-reference summaries) with the same original
parameter bindings, callee owner, require-goal IDs and ensure ordinal. When the
SSA result is bound into a source local, summary substitution can instantiate
that local's result without treating repeated call text as one scalar value.

Reserved-name recognition only selects producer bookkeeping; it grants no replay
authority. Existing replay independently resolves the unique original local
binding and same-site direct Call summary, its exact source span and argument
mapping, executable callee ensure, original owner and proven requirements. No
reserved-name admission path or purity classification was widened. The ordinary
callee body and source semantic admission remain required.

Accepted minimized controls now prove/replay arithmetic_call_result_alias 7/7
and call_result_literal_alias 5/5. The wrong 998 upper bound is refused (actual
maximum 999), as are substituting the second call's 150 result for the first 75
result and claiming their unsigned difference is zero. The new regression suite
checks complete admission/replay for accepted reports and open goal-linked
findings for all rejected claims. Guarded call-result controls, full conditional
frame accounting and conditional-call CLI controls remain passing.

AudioTriggers now proves/replays all 49 implementation-linked obligations with
no findings. The uncached engine sweep improves from 66/73 to 67/73. Six failures
remain: action_input_context, action_input_deadzone, audio_anim_events,
audio_virtual, motion_overlay_policy and sound_event_assets. Broader call-order
transport test still fails its finding-set assertion on
`automatic_captured_conditional_result`; comparison with prior immutable
product generation ea3896a8da7a440ca20b90fc89d56882 shows the identical finding
set, 57 obligations and zero replay gaps. This is an existing full-matrix gap,
not a passing full compatibility gate.

Evidence in engine build/validation: prover-source-call-result-build.log,
prover-source-call-result-final-build.log, audio-triggers-call-result.json and
proof-source-call-result-sweep.log. The final all-products strict O2 build and focused qualification pass,
generation 7551c030af11443b8b79d9bd025d27a4, using installed compiler 96761822
and matching runtime/parser sources. Full prover matrix,
compiler/CI qualification and engine shared/native gates remain open.
