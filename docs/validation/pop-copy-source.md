# Copied pop literal source replay (2026-10-08)

Clean paired source `6478c65e` still has two gaps in
`examples/collection_pop_value.elisa`: the returned first captured value in
`take_last` and `take_two`. The fixture has eight certificates, six replayed.
The copied literal (`x == 9` / `x == 5`) already appears as a generic proof-step
before slot restatement can add a specialized collection-pop-value trace.

Replay now authenticates that receiver-free literal consequence with the existing
`ElisaProofFrameSource::pop_value_source` predicate. Only a proof-step without
summary/dependency metadata at its source copy line qualifies. The existing source
rule requires a typed builtin mutable darray reference, matching immutable local
and exact source span, a contracts-only prefix with a positive count guard and
last-slot literal, and a suffix containing only further pops of the same receiver
and return of the captured local. Historical collection equalities remain expired.
Both source/kernel trace validators retain AST/kernel correspondence checks before
this admission. No producer fact or obligation is removed.

`python3.14 scripts/test_pop_copy_source.py` compiles and executes both O0 harnesses
with frozen compiler `52d60fcf` and matching runtime. All eight original fixture
certificates replay, and five forged proof-step controls are refused (wrong line,
kind, summary index, literal and local). The unmodified original pop snapshot
harness also passes its two positive and eleven negative cases (wrong literal,
local, source spans, first slot, local write, prior pop, shadowed pop, receiver
mutability, missing guard and mismatched element type). The harness uses saved
index counts for calls that mutate report context during trace iteration.

Clean paired build, original public positive/adversarial regression and uncached
engine sweep are pending. Full compatibility and production promotion remain open.
