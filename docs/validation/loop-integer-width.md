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
