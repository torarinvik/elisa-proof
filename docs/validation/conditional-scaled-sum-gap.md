# Conditional scaled sum replay gap

On prover d3609076 with compiler 96761822, the engine capture-timing failure
minimizes to `test/repro/conditional_scaled_sum_bound.elisa`. Its valid upper
bound is proved by the producer but not replayed: 2 certificates, 1 replay,
1 gap. This remains an open prover task, not an accepted regression.

The same scaled sum with `capped <= 999999999` as a parameter precondition
fully proves and replays 2/2. A whole-seconds early-return guard also fully
replays 3/3. Introducing the immutable conditional cap reproduces the gap
with either a precondition or an early-return guard on whole seconds.

`test/repro/rejected_conditional_scaled_sum_bound.elisa` lowers the claimed
maximum by one. It is correctly refused with one unproven obligation and
no semantic errors or replay gaps. At whole=9000000000 and fraction=1000000000,
the result is 9000000000999999999, contradicting that claim.

A fix must replay the valid conditional-derived bound while preserving the
invalid-bound rejection and the engine's original implementation/contracts.
