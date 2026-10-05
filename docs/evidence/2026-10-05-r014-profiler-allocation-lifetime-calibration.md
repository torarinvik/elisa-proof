# R-014 profiler allocation/lifetime calibration

## Scope

This is a deterministic synthetic calibration of the adjacent `elisa-profiler`
allocation-lifetime analyzer, not a profile of the proof engine and not a
performance result. The fixture supplies one 64-byte observed region, two known
allocation events (8 and 16 bytes), a reclaim of the first allocation, and a
region reset that retires the second. The expected peak logical live size is
24 bytes, the capture-end live size is zero, the largest recorded lifetime is
50 ns, and 64 bytes of backing capacity remain observed after reset.

The fixture is an analyzer-input fragment containing only the fields needed by
the analyzer; it is not claimed to be a complete schema-valid profiler report
or evidence emitted by a real runtime. No returned-sview/region probe is
included: this check calibrates event accounting only, and does not establish
the Elisa borrow/lifetime semantics needed to interpret a view's liveness.

## Exact identities

- Profiler repository: `elisa-profiler`, clean `main` at
  `39f46e4983c4e233b542e7c57ff27f15c96fb8e2`.
- Analyzer: `scripts/analyze-allocation-sites.py`, SHA-256
  `fbd028562ea84ee99329a4f41418d40ea975da879bd9513a545b8c9227eeb81a`.
- Profiler CLI used to inspect commands/options: `bin/elisa-profiler`, SHA-256
  `eb4e06d91e737abb87aedd7a1b2d280218ed1036033d609bc729befbb32f4101`.
- Proof repository baseline during the change: `b5793019` on `main`, with
  unrelated pre-existing edits left untouched.

## Commands and results

From `elisa-proof`:

```sh
python3 -m unittest scripts.tests.test_profiler_allocation_lifetime_calibration -v
python3 -m py_compile scripts/tests/test_profiler_allocation_lifetime_calibration.py
git diff --check
```

The automated test dynamically loads the exact adjacent analyzer path
`../elisa-profiler/scripts/analyze-allocation-sites.py` and checks its Python
API and CLI. It verifies the known live/retired counts, backing-capacity
separation, complete-capture acceptance, each currently recognized loss field
(`allocation_events_dropped`, `frame_dropped`, `trace_dropped`,
`capture_bytes_dropped`, and `trace_stack_overflow_entries`), incomplete-capture
refusal, and the analyzer's 100,000-event bound/truncation marker.

No Elisa program was compiled, no Stage0 or Stage1 binary was used, and no
shared build output was touched. Therefore this calibration says nothing about
compiler correctness, runtime hook coverage, sview validity, proof-engine
performance, or real workload allocations. It validates the current analyzer
behavior for this known event sequence and its tested refusal indicators only.
