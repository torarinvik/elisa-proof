# R-014: profiler event-loss completeness gate

## Control

The profile summary now emits `capture.complete_measurement_accepted`, derived
from the runtime completion bit plus sample-count consistency, malformed
records, missed samples, setup failures, dropped-record/overflow counters, and
requested repetition completion. Any recorded quality problem closes this
gate, even when the raw runtime `capture_complete` bit says true.

The synthetic regression keeps the sample count exact and the runtime bit true,
then sets only `stack_overflow_entries` to one. The result retains the raw
runtime bit for diagnosis, marks sample quality degraded, names the dropped or
overflowed-record reason, and refuses to accept the capture as a complete
measurement. A clean fixture asserts the gate is open. This is analyzer-level
evidence from a synthetic capture; it does not test profiler runtime emission.

## Validation

```sh
python3 scripts/test_perf_luna_profile_summary.py -v
python3 -m py_compile scripts/perf_luna_profile_summary.py scripts/test_perf_luna_profile_summary.py
git diff --check
```

All 11 focused tests passed, including the single-counter overflow control.
Python bytecode compilation and `git diff --check` passed.
