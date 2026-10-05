# Integrated Luna implementation slices: validation checkpoint

This checkpoint validates the source-site deterministic-call replay guard, scalar witness name
index, portable decoder regressions, and recent CLI/build instrumentation slices together. It is a
focused checkpoint, not completion of the full implementation plan.

## Product identities and pair mismatch

The clean validation worktree was at proof commit
`c937bd45e1d6b1abbac28fbe71a057b0fa84b20a`. The proof product records source tree digest
`72d57a84b7c759943ea348ec1af50ccf8e678e5530c44751fa75d0778749a17f`, while the reusable replay
product still records the older tree digest
`43bc34bd11ff5db911be2365ecb64931a5a605153eb0a2665f6ecea49dc6974f` from proof HEAD
`66ecbb4fc5d9fc0dc3c32f8a974142f21d364569`. Both products use strict mode at O2 for
`arm64-apple-darwin27.0.0` with pinned Stage1 compiler revision
`7b27fa312c5af923f044f6ee0e5e1de4f811f595` (binary SHA-256
`f77278c716dea7f3dba8f4fcbcf76ecc473426ab3f163c95fea4e358f6337653`) and runtime object SHA-256
`b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`.

- `build/elisa-proof`: SHA-256
  `02f87230510bc1007376db9b46478bce8fef82f1001f92b7881b7b4a0ba3a1f4`, manifest build identity
  `1f41dedb57bbd44bc068b525320b677222148c54c58d3e31b7ab95542a5730f0`.
- `build/elisa-proof-replay`: SHA-256
  `e50f691b560f26e8577e91ca9e18a062365f2a5c370c7a72d1c005e8da8c8246`, manifest build identity
  `ac5f61524d35fd400bb01ece72fd67140b823a7b804fb4a1f7844a72b15e2063`.

The manifests agree on compiler, runtime, target, strict mode, and optimization level, but their
proof source-tree digests differ. The run is therefore not a coherent product-pair validation
under R-015. A focused portable-replay run passed with these binaries, but it is diagnostic only
until the build path refreshes both product identities from one source snapshot. The validation
checkout was clean at the recorded source commit.

## Focused checks

All checks below passed against the named proof/replay binaries unless a standalone runtime
harness is noted; producer/replay results remain subject to the product-pair mismatch above.

- `scripts/test_source_admission_matrix.py`: six malformed classes refused on all twelve routes.
- `scripts/test_report_summary.py`: compact and full report conclusions and authoritative counts
  agree.
- `scripts/test_fact_growth_work_budget.py`: the relevant under-cap case proves; the over-cap case
  refuses without a model or replay gap.
- `scripts/test_deterministic_call_chain.py`: positive nested calls and widened-call controls prove
  and replay; effect, mutable-global, mutable-borrow, and indirect-call controls refuse.
- `scripts/test_portable_replay.py`: all 16 positive packages replay and the package-reader,
  schema, semantic, UTF-8, and Boolean payload attacks refuse with structured results.
- `scripts/test_long_difference_chain.py`: the bounded difference facts are checked through each
  link.
- `scripts/test_unsigned_division_bounds.py`, `scripts/test_unsigned_remainder_range.py`, and
  `scripts/test_monotone_orders.py`: positive arithmetic certificates replay and false controls
  remain unproved.
- `python3 -m unittest test_perf_luna_allocation_summary` from `scripts/`: four tests pass; Python
  compilation also passes. The summary keeps logical live bytes, backing capacity, and capture
  quality separate and does not infer RSS or source-site identity.
- `scripts/test_build_dependency_closure.py` and
  `scripts/test_build_manifest_sidecar_integrity.py`: unrelated edits preserve products, and a
  corrupted checksum sidecar triggers recompilation/relink of only the affected product in the
  stub-tool orchestration fixture.
- `scripts/tests/test_soundness_incident_registry.py` and
  `scripts/soundness_incident_registry.py`: strict registry validation passes with zero confirmed
  incidents recorded.

Three source-level runtime harnesses were compiled with the pinned Stage1 compiler at O0, linked
against the pinned runtime and profiler hooks, and exited 0:

- `examples/deterministic_call_trace_replay_runtime.elisa` rejects parenthesized-reference and
  forged-scalar trace mutations, then restores and replays source-backed traces.
- `examples/tactic_runtime.elisa` confirms that mutating a disjunction child leaves its sibling
  and parent fact arrays unchanged.
- `examples/marker_dispatch_runtime.elisa`, compiled in permissive mode, confirms the scalar-name
  scan and hash index agree on valid and malformed marker cases, including a same-bucket collision.

## Remaining limits

No full dogfood or complete proof/compiler suite was run. No paired performance, allocation
reduction, retained-memory, or scaling claim is made. The R-005 source-site walk fails closed on
control-flow call sites and does not prove post-call state liveness. R-019 only indexes scalar
marker names; differential performance and allocation savings are unmeasured. R-006 still needs
decoder fuzzing, the complete boundary matrix, parser-resource tests, and worst-case memory
evidence. R-007's mutation check covers one tactic fact-array path. R-009's registry is not yet
wired to artifact consumers. R-014 has no frozen proof-workload captures or phase/source/store
attribution, and R-018 has no real-build no-op cost measurement.
