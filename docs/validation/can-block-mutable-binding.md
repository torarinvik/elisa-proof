# Capability-block mutable binding replay (2026-10-08)

Clean paired source `364edfdb` still refused one certificate in
`examples/can_block_frame.elisa`: `learns_inside`, return line 33, whose goal
is `m < 11` after a direct assignment `m <- 10` in a capability block.
The original test failed with 15 certificates / 14 replayed and one gap.

`mutable_local_bindings.elisa` now treats a `can` block without a bound name
as a once-executed scope. A direct assignment to an outer typed mutable integer
can reach a later consumer only if the inner and enclosing suffixes preserve
it. Assignments inside conditional branches and loops keep their nested scope
restrictions. Existing source span, unique declaration, stable value, primitive
operator and alias/write checks remain required.

The compiled O0 source harness
`python3.14 scripts/test_can_block_binding_source.py` passes on frozen compiler
`52d60fcf` and matching runtime: one authentic direct assignment is accepted;
eleven forged trace/source controls are refused (wrong line/local/value, changed
literal, outer/inner later write, conditional/loop site, conditional enclosing
block, shadow declaration and reference local). Three additional controls use
the actual traces generated from the changed conditional/loop source and require
that a binding trace exists before testing refusal. These establish the scope
restriction independently of a stale source span.

An initial nested literal pattern in the test harness was declined by the frozen
backend. Ordinary bound patterns with explicit value comparison compile and pass;
no production source rewrite was required for that harness limitation.

Clean paired build and the complete original positive/adversarial regression,
plus the uncached engine proof sweep, are pending. Full compatibility and
production promotion remain open.

## Clean paired qualification

Clean source `7d89ab5a`, generation `edc1bd983f0641d78752602beff17f99`,
builds in 44.30s at 2,309,440 KiB RSS under 8 GiB. Both manifest/source
identities and actual binary hashes match (`build/can-block-binding-product-identity.json`).
The complete original `scripts/test_can_block_frame.py` passes both positive
and adversarial fixtures. Positive evidence is now 15/15 certificates proven
and independently replayed with zero gaps (`build/can-block-binding-product-report.json`).

The uncached engine sweep retains all 73 reports / 4,246 independently replayed
obligations with zero semantic errors, diagnostics, gaps or trusted assumptions.
Reports and inventory are in `../elisa-engine/build/validation/can-block-binding-engine-reports/`
and `can-block-binding-engine-inventory.json`; the bounded log is
`can-block-binding-engine-sweep.log`. Full compatibility and production promotion
remain open. The loop-exit, pop-value and other confirmed replay failures are
separate pending repairs.
