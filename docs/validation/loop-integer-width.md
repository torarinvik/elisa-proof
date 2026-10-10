# Typed counting-loop binder ordering (2026-10-08)

Clean paired source `1e7435c6` has one replay gap in the original
`examples/guard_and_flag_facts.elisa`: `k3` line 12, the index upper bound after
`continue if i >= values.count`. The binder is a tagged `(name, source-offset)`
atom. It had a primitive scalar marker but no integer-width witness, and kernel
negated-comparison collection correctly refused to assume scalar meant integer.

The producer now supplies the exact unsigned width for a counting range with a
nonnegative literal lower endpoint and an exactly marked unsigned identifier or
field upper endpoint. The lower literal must fit that width. The witness belongs
to the opaque binder atom, preserving shadowed binder identity. Existing signed
literal ranges and unsigned foreach rules retain their separate type sources.

Kernel integer-order classification admits tagged loop atoms only with a matching
unsigned/signed width marker and the exact two-element tag shape. Producer and
kernel closed-value classification admit these typed atoms to Boolean denial
reasoning. Arbitrary scalar tuples and floating tags remain unsupported; no scalar
marker alone supplies integer totality.

Frozen compiler `52d60fcf`, matching runtime, O0 executable:
`python3.14 scripts/test_loop_integer_width.py` passes. All nine original fixture
certificates replay. Removing the exact width marker refuses both integer
classification and the original index goal. Malformed tuple arity and floating
source-offset tag refuse classification; restoring the authentic tag succeeds.

Clean paired product build, complete guard-and-flag positive/adversarial regression,
existing integer/float denial controls and uncached engine sweep remain pending.
Full compatibility and production promotion remain open.

## First paired qualification and budget regression

Clean `a7ccedf2` generation `5284e8e81a4a48018e62f9f4c8489b6b` builds in
47.10s at 2,617,728 KiB RSS under 8 GiB. The complete original guard-and-flag,
integer-disjunction denial, float/integer bounds and Boolean/equality denial scripts
pass. The engine sweep fails `audio_anim_events.elisa`: `consume_state` reaches
69 facts against its unchanged limit of 68, then cannot prove one index upper bound.
There is no replay gap in that failed report. Exact report and bounded failure log
are in `../elisa-engine/build/validation/loop-integer-width-engine-reports/`
and `loop-integer-width-engine-sweep.log`.

The follow-up replaces the redundant primitive-scalar marker with the exact unsigned
width marker on these loop atoms. Producer/kernel witness caches independently decode
that canonical typed marker as scalar identity; the kernel also checks the exact loop
atom shape. The original fact budget is unchanged. Existing signed literal range facts
are unchanged. The compiled typed-loop harness passes again with this replacement.
Clean paired engine qualification of the follow-up is pending.

## Follow-up clean paired qualification

Clean source `57663d01`, generation `aa71933424c7491098a87dcadd25dda9`,
builds in 44.18s at 2,284,464 KiB RSS under 8 GiB. Both source/manifests and
actual binary hashes match (`build/loop-integer-width-budget-product-identity.json`).

The original guard-and-flag regression passes positive and adversarial fixtures,
with all 9/9 positive certificates independently replayed. Original integer
ordering denial, float/integer bounds (both whole-file and focused routes), and
Boolean/equality denial scripts also pass. False integer, floating total-order,
unsafe upper bound, missing guard, Boolean and nullable claims remain refused.

The uncached engine sweep passes all 73 reports / 4,246 obligations with zero
semantic errors, diagnostics, gaps or trusted assumptions. The audio-animation
budget regression is repaired within the original limit. Sweep time is 2.02s,
216,288 KiB RSS under 3 GiB. Reports, inventory and bounded log are in
`../elisa-engine/build/validation/loop-integer-width-budget-engine-reports/`,
`loop-integer-width-budget-engine-inventory.json` and
`loop-integer-width-budget-engine-sweep.log`. Full compatibility and production
promotion remain open.
