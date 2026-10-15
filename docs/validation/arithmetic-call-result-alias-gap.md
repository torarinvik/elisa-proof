# Arithmetic call result alias replay gap

## Current source status (2026-10-15)

The replay source now contains an independent bridge for this local-result alias in
`src/proof/replay/call_result_binding_provenance.elisa`. It locates one immutable local
initializer in the exact owner, rejects reassignment and borrowing of that local, compares the
initializer with the traced call, validates the exact source call span and callee signature, and
requires a scalar result. Both bare and scoped callees must also pass replay's bounded
source-purity check; a scalar signature alone does not make effectful repeated calls equivalent.
Scoped callees resolve through the declaration and module-alias indexes, with exact caller
identity. The targeted scoped-call gate also rejects a local binding that shadows the leading
identifier of a module path, matching the compiler's local-before-module resolution. The static
guard pins that check. `scripts/test_source_call_result_alias.py` includes the
arithmetic and literal positive cases plus distinct-invocation and wrong-alias refusal controls.

This source-level implementation does not close the incident by itself. The result remains
unqualified until the positive and negative fixtures run with a proof binary matched to the current
source and compiler. The binary observations below are historical evidence and must not be read as
results for the current source.

`test/repro/arithmetic_call_result_alias.elisa` minimizes the remaining
engine `audio_triggers` failure on prover 671ec265. The producer proves the
bound, but the then-current replay accepted 6/7 certificates. The call has arithmetic arguments;
its summary describes an internal result symbol and a local-binding fact
connects the source local to that symbol. At that time, source replay had no independent
validation of this connection. A parameter-only call result did replay.

The rejected fixture lowers the final bound to 998 and makes both guarded
returns zero, so refusal must cover the final computed branch. At threshold=0,
full=10000, drop=9999, the scaled share is 749 and the final result is 999.
The rejected fixture reports unproven obligations with no semantic errors.

The replay boundary must independently reconstruct result identity from the source call and its
validated summary. Merely trusting the producer's internal-name binding would weaken it. Engine
contracts remain unchanged.

## Source-call identity controls

A query on the binary used for the original investigation also left
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

Both exited 1 on the binary used for the original investigation. They are rejection controls for
the source-derived invocation mapping; matched-build execution is still needed to establish that
the current replay rejects them while accepting the literal and arithmetic positive controls.
Distinct invocation identities remain required; weakening call purity is insufficient.
