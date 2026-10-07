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
