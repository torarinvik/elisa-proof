# R-014: post-reset sview negative control

The real profiler runtime-lifetime harness now checks the existing
`examples/rejected_sview_after_region_destroy.elisa` fixture as a separate
verifier-side negative control. The fixture reads an `sview` after its backing
region has been destroyed. The proof checker refuses it before target execution:
the report has `status: failed`, a `region-destroy-live-borrow` finding with
`status: unknown`, and zero replay gaps. This is a safe static refusal; no stale
pointer is dereferenced by the test.

The positive profiler probe remains distinct: it reads a returned `sview` while
the source region is still live, then destroys that region. A successful live
read does not establish that a view remains valid after reset/destruction.

## Validation and identities

Command:

```sh
ELISA_PROOF_BIN=/path/to/elisa-proof/build/elisa-proof \
python3 scripts/tests/test_profiler_runtime_lifetime.py
```

The command rebuilt the native profiler at O2, captured the known allocation,
reclaim, reuse, and reset sequence, ran the negative verifier control, and
passed all assertions. Python bytecode validation and `git diff --check` passed.

- Proof checker SHA-256: `12c6347093b8cd95d77fc2d54eb843ca605bc166165b1b7c2c281699f35f7a54`.
- Negative fixture SHA-256: `0e087a79ffe803638cd360f7267e234b6cd2bae3a609f826d61f7a5efd0a7f6e`.
- Compiler checkout revision: `bc8def2eadf41dd088adce22b4d3d9e74aadfee9`.
- Stage1 SHA-256: `96eca8200bb268ea5cc1635a66d6b0da0cd85611331319c3227362d9421c2947`.
- Matching runtime object SHA-256: `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`.
- Profiler checkout revision: `39f46e4983c4e233b542e7c57ff27f15c96fb8e2`.

This control establishes the verifier's refusal for this region-destroy shape.
It does not test arbitrary raw-pointer invalidation or every arena reset route.
