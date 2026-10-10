# Arithmetic call result alias replay gap

`test/repro/arithmetic_call_result_alias.elisa` minimizes the remaining
engine `audio_triggers` failure on prover 671ec265. The producer proves the
bound, but replay accepts 6/7 certificates. The call has arithmetic arguments;
its summary describes an internal result symbol and a local-binding fact
connects the source local to that symbol. Source replay has no independent
validation of this connection yet. A parameter-only call result does replay.

The rejected fixture lowers the final bound to 998 and makes both guarded
returns zero, so refusal must cover the final computed branch. At threshold=0,
full=10000, drop=9999, the scaled share is 749 and the final result is 999.
The rejected fixture reports unproven obligations with no semantic errors.

The fix must independently reconstruct result identity from the source call
and its validated summary. Merely trusting the producer's internal-name
binding would weaken the replay boundary. Engine contracts remain unchanged.

## Source-call identity controls

A fresh query on the current binary also leaves
`test/repro/call_result_literal_alias.elisa` at 4/5 replayed certificates,
with no source diagnostics or producer findings. Its arguments are literals.
Arithmetic argument normalization is therefore not necessary to reproduce the
missing invocation-result identity validation.

Two new refusal controls retain 5/5 replayed admitted certificates, one open
obligation, one finding, and no semantic errors:

- `call_result_distinct_invocations_rejected.elisa`: cap(1, 10) returns 75 and
  cap(2, 10) returns 150. Their difference cannot equal zero, including u64
  wrapping. Collapsing both invocation results into one symbol would admit it.
- `call_result_wrong_alias_rejected.elisa`: the returned second call is 150,
  not the first call's 75. Reusing the earlier result identity is invalid.

Both exit 1. These are rejection controls for the pending source-derived
invocation mapping, not evidence that the accepted alias gap is repaired.
The eventual repair must cover literal and arithmetic argument calls and
retain distinct invocation identities; weakening call purity is insufficient.
