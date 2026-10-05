# P-01 workload inventory and provenance gate

This evidence closes one narrow P1.1/P1.2 infrastructure gap: every fixture in the existing
P-01 sentinel cohort now has a path, SHA-256, byte count, line count, expected process/verdict
status, obligation summary and emitted obligation rows, trusted-assumption inventory, trusted
boundary-fact count, and proof/replay certificate totals. The manifest also identifies the exact
proof/compiler/frontend/runtime products used for the probe and the companion standalone replay
product. It is a probe inventory, not a speed result or an independently trusted correctness oracle.

## Exact semantic probe

- Proof commit: `1d899e8a332c5db44970c39d208718026c33dbed`
- Proof source tree SHA-256: `717b33e5813d91247525a542af938cdb8d33a9e55e7dc9a344774139d1cb0cb0`
- Compiler/Stage1 frontend revision: `6b475d894331f0a81c3112167ef7fcf5c642a424`
- Stage1 product SHA-256: `65a9308c53b510365aa69644a0bcaa9a071ea2006683dad6bf2ec12fc394f6b3`
- Frontend tree identity: `401bd5368e7909168e9500c872ab122ae421750c`
- Runtime object SHA-256: `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`
- Proof product SHA-256: `e61f59753196c4d6f0979c88dc1aa2f63997e9f37992b7bdf8e9d3d892d58464`
- Standalone replay product SHA-256: `183565a5f67d22988348269da35b988e9cadbaee76a699ea75b380f8ef9df084`
- Target/configuration: `arm64-apple-darwin27.0.0`, strict, O2
- Immutable generation: `c739899e43ef4a34a1c5e48a975ca4c9`

Stage1 freshness validation passed before building. The compiler checkout had a pre-existing
`.gitignore` worktree edit; the manifest binds the exact compiler revision, frontend tree, compiler
product, and runtime hashes rather than treating the checkout's cleanliness as product identity.

## Gate result

The focused manifest test passes. It rejects a missing fixture, omitted or malformed digest, changed
fixture bytes, missing semantic rows, contradictory verdict, omitted obligation row, absent
assumption details, inconsistent replay totals, and absent compiler/proof probe provenance. The
P-01 runner additionally refuses an observation with any replay gap or incomplete source-obligation
inventory; instrumentation data cannot turn these into admitted baseline samples.

The fresh probe does **not** qualify as a performance baseline:

- `adversarial` reports 78 obligations but emits 77 goal rows, 30 replayed certificates, and 19
  replay gaps. Its source-obligation inventory is explicitly marked incomplete.
- `branch_join` has 12 obligations but only 9 replayed certificates (3 gaps).
- `qualified_constants` has 17 obligations but only 11 replayed certificates (6 gaps).
- `qualified_constant_refusal` has 17 obligations but only 7 replayed certificates (4 gaps).
- The other seven fixtures emitted gap-free reports in this probe. This does not establish a valid
  corpus-wide baseline because the four ineligible workloads are part of the pinned cohort.

No timing comparison or speedup is claimed. Existing P-01 artifacts do not meet the complete gate:
the earlier kernel-core timing report had a smaller corpus and no complete current semantic
inventory, and this fresh exact pair exposes replay/inventory failures. The current cohort is still
not the canonical set required by P1.1: malformed and unsupported inputs, call/match/loop-heavy
workloads, high-fact stress, and package import/replay need explicit pinned fixtures. P1.2 also
remains partial: source bytes/lines are recorded, while AST nodes, declarations/facts by source
inventory, branches/calls, package nodes, and certificate-DAG sizes are not yet independently
measured for every workload. Internal phase timing and comprehensive deterministic work counters
remain unavailable or incomplete.

Reproduce the fresh build with the recorded proof commit and compiler revision, then run
`python3 scripts/test_p01_baseline.py`. Run the normal P-01 runner only to observe eligibility; a
report with `complete: false` is diagnostic evidence, never a performance baseline.
