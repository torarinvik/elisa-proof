# R-004 proven obligation ledger duplicate control

The shared report admission invariant rejects a duplicated proven result in the independent
obligation ledger while the rest of the report remains plausible. The control starts with one
proven obligation and its matching goal attempt/certificate, then adds a second open obligation
with an unproven goal attempt. Changing only that second ledger result from `false` to `true`
returns the dedicated failure code if `proof_report_source_admission_invariants_consistent`
accepts the mutated report.

## Matched source and build

- Proof repository source: `9e5f307b4c1b7286d7b4f72280287e5819a81e82`
- Compiler repository revision: `bc8def2eadf41dd088adce22b4d3d9e74aadfee9`
- Stage1 compiler SHA-256: `96eca8200bb268ea5cc1635a66d6b0da0cd85611331319c3227362d9421c2947`
- Runtime object SHA-256: `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`
- Profile hooks object SHA-256: `ff7eb87b67bbc470ee95c320bb95ff125300f1edc8c2e67585d282e27e0e9711`

## Focused result

Compiled `examples/report_invariants_runtime.elisa` with the stage1 compiler using
`-permissive -emit obj -O0`, linked it with the runtime and profile hooks objects, and ran the
resulting executable. The harness exited `0`, so all existing invariant controls and the new
duplicate-proven-result control passed.
