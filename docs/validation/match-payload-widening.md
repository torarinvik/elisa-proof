# Match payload widening replay (2026-10-08)

The frozen `ee9c67a9` full matrix fails `test_widening_cast.py`: `wide_first`
produces 36 certificates but only 35 replay. Its cast equation is
`wide == __elisa_rebind_0`. The declaration validator rejected the internal
receiver before reaching its existing match-arm validator.

The source change routes internal receivers directly through that validator.
Ordinary parameter validation remains separate. The match validator still
requires the unique source arm, immutable enum subject, exact payload ordinal,
range-preserving builtin conversion, unchanged payload, and consuming return.
No certificate is admitted from a symbol spelling alone.

## Focused source admission

Run `scripts/test_match_widening_source.py` with compiler `52d60fcf` and its
matching Stage1 product, bounded to 3 GiB / 360 seconds. Result: status 0,
32.06 seconds, 1,367,088 KiB peak RSS. The authentic equation is accepted;
12 forged trace/source controls are refused. Controls cover wrong line,
receiver and target; narrowing, mutable target, wrong cast method/payload,
payload shadow/write, mutable subject, prior fresh witness and changed return
path. The harness is registered beside the widening-cast matrix test.

Evidence: engine `build/validation/match-widening-source-controls.log` and its
watchdog JSON. Product replay, portable replay and engine sweep still require
qualification on a clean paired build. This source admission result does not
establish full matrix compatibility or repair quantified branch consequences.

The existing 601-line invariant harness is restored to the 600-line policy by
joining its final print opening line; its assertions are preserved.

## Paired product follow-up

Clean generation `a34270215af342c5881e4d49040a35c2` identifies commit
`1ff203f6` with `source_dirty: false`; both actual binary SHA-256 values match
the manifests. Paired build completes in 82.19 seconds at 2,530,352 KiB RSS
under 8 GiB. The full widening product control remains **failed**, 35/36
certificates replayed. The earlier source admission result is not sufficient.

The first compiled per-fact audit stops at the `zero(rest) == 0` summary,
but it omitted complete arena/replay initialization. Its dependency refusal is
an audit setup failure, not sufficient evidence for locating the product gap.
The corrected audit runs `proof_replay_certificates` before checking individual
facts. Source inspection identifies the conservative reset after the earlier
method-shaped cast; the baseline/new-source comparison below tests that cause.
Do not admit arbitrary numeric-looking methods as pure from their names.

Evidence: engine `build/validation/match-widening-clean-pair-build.log`,
`match-widening-clean-pair-identity.json`, `match-widening-product-controls.log`,
and `match-widening-fact-audit-retry.log`. The first audit compile was refused
for accessing a private helper from outside its module; the retry used a
test-only wrapper and did not change production visibility. This pair is not
promoted into the engine's live qualification run.

The clean pair retains the uncached engine inventory: 73 reports / 4,246
obligations, all proved and independently replayed, zero semantic diagnostics,
errors or replay gaps, and no trusted assumptions. The isolated report directory
avoids overwriting reports used by the live native gate. Sweep result: status 0,
2.49 seconds, 216,256 KiB RSS under 3 GiB. Evidence: engine
`build/validation/match-widening-engine-sweep.log`,
`match-widening-engine-inventory.json`, and `match-widening-engine-reports/`.
This does not establish native GPU correctness or full prover compatibility.

## Source types retained through builtin conversion initializers

The call-site walk now keeps a lexical source type list alongside its value
substitutions. Formal and local types and exact enum payload types are recorded;
all branch, block, match and loop exits restore the enclosing type list. A value
reset does not erase the type. Initializers are evaluated against the incoming
types before introducing their own local.

Only a zero-argument numeric conversion of a plain source identifier with a
known primitive integer type avoids the possible-write reset. Both primitive
type spellings must be unshadowed. Any ordinary/extern function with the
selector's name or `__cast__` keeps the operation opaque. Reference/alias/user
types, compound receivers, extra arguments and other methods keep the reset.
The general method-write checker is unchanged. Cast arithmetic and range proofs
still run in the independent logical kernel.

`test_typed_cast_call_source.py` checks all 36 certificates of the real widening
fixture, then refuses 11 source dispatch/state mutations. Controls retain the
later call's exact span, including offsets, so position changes cannot conceal
a purity or state-admission error. Separate source buffers preserve the original
trace while parsing controls. The same regression compiled against the clean
`1ff203f6` source snapshot fails its complete replay assertion (expected negative
control, status 1, 27.11 seconds / 1,245,920 KiB RSS). Current source passes in
25.75 seconds / 1,502,768 KiB under the original 3 GiB cap. The prepared per-fact
audit also passes (17.53 seconds / 1,310,576 KiB). Evidence: engine
`build/validation/typed-cast-call-source-controls-final.log`,
`typed-cast-call-source-baseline-control.log`, and
`typed-cast-call-prepared-fact-audit.log`.

Harness compilation initially refused a private helper access; a test-only
wrapper preserves production privacy. The larger nested match harness also
encountered a backend decline. The final harness uses a small expression
selection helper, preserving all assertions and controls. The source snapshot
negative control is a successful compile followed by the intended replay refusal.
Paired product replay, portable replay, engine sweep and full matrix qualification
remain separate acceptance steps.

Existing `scripts/tests/test_replay_scope_and_context_holes.py` also passes on
the changed source: 89.39 seconds / 1,595,872 KiB under 3 GiB. It retains
shadowed constants, nested redeclarations, stale loop bindings through a derived
step or reused memo, and wrong-call precondition refusals. Evidence: engine
`build/validation/typed-cast-scope-context-controls.log`.
