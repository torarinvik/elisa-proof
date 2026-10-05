# R-014 nested-store analyzer control

## Scope

This is a deterministic synthetic-input regression for the adjacent Elisa
profiler's production allocation-lifetime analyzer. Its event fragment models
two nested proof stores as distinct arena identities: an outer store (`arena`
7) and an inner store (`arena` 9). Their allocation events carry separate
source stacks and source locations. Resetting the inner arena must retire only
its allocation; the outer allocation remains live until the outer reset.

The test establishes that, for this supplied event sequence, the analyzer
preserves each source-site attribution and computes the corresponding observed
lifetime (30 ns for the inner allocation and 80 ns for the outer allocation),
with 24 peak logical live bytes and zero at capture end. It does not establish
that runtime hooks emit nested-store identities or source stacks correctly, nor
that a real proof workload has these events. The synthetic capture is not a
performance measurement, profiler-noninterference check, or overhead estimate.

## Exact identities

- Proof repository base: `3ebb360598c3299820c9386f2ceb1844bd6dc1c6`.
- Profiler repository: `elisa-profiler`, `main` at
  `39f46e4983c4e233b542e7c57ff27f15c96fb8e2`.
- Analyzer: `scripts/analyze-allocation-sites.py`, SHA-256
  `fbd028562ea84ee99329a4f41418d40ea975da879bd9513a545b8c9227eeb81a`.
- Test: `scripts/tests/test_profiler_allocation_lifetime_calibration.py`,
  `test_nested_store_resets_keep_lifetimes_and_sites_separate`.

## Commands and results

```sh
python3 -m unittest scripts.tests.test_profiler_allocation_lifetime_calibration -v
python3 -m py_compile scripts/tests/test_profiler_allocation_lifetime_calibration.py
git diff --check
```

All six calibration tests passed, including the nested-store control. The
isolated worktree was under `/private/tmp`, so the test's existing adjacent
repository lookup was satisfied during this run with a temporary symlink to
the identified profiler checkout; the symlink was removed after the test.
No compiler or proof binary was run, and no profiler capture was collected.

The result calibrates analyzer behavior on hand-authored events only. Real
nested-store event emission/attribution, profiler noninterference, matched
overhead measurement, and real proof-workload profiles remain open.
