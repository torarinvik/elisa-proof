# R-014 allocation capture summary slice

## Implemented

`scripts/perf_luna_allocation_summary.py` reads the `allocation_captures` section
of a bounded memory benchmark JSON artifact and emits one row per workload
repetition. It preserves event counts, explicit dropped-event counts, capture
completeness, and lifetime availability. It reports logical live-byte peaks
separately from observed backing-capacity peaks, and labels process RSS and
allocation-site identity as unavailable instead of inferring them.

The input is capped at 128 MiB, with explicit workload and repetition limits.
Malformed or missing accounting fields fail closed. The synthetic probe covers
complete, dropped-event and truncated capture states, metric separation, and
malformed event counters.

## Validation

Commands on the isolated R-014 branch:

```text
cd scripts && python3 -m unittest test_perf_luna_allocation_summary.py
python3 -m py_compile scripts/perf_luna_allocation_summary.py scripts/test_perf_luna_allocation_summary.py
git diff --check
```

The unit probe passed (4 tests). The compatibility reader was also run against
the existing adjacent `Elisa-compiler` memory artifact
`docs/measurements/memory-speed-20260914.json`, SHA-256
`432656cb6f0e597b2553355b197c0368582a8fb4c48471a2523629576dbff240`.
It summarized six workload groups and 18 repetitions; every captured repetition
reported `capture_complete=true`, zero dropped allocation events and available
lifetime metrics. This validates the reader against an existing producer
artifact. Those workloads measure compiler/runtime allocation behavior and are
not proof-assistant workloads or performance evidence for this repository.

## Remaining R-014 gates

- Run lifecycle captures on a frozen proof workload and dominant timeout.
- Connect allocation events to stable source identity, store generation, and
  search phases.
- Distinguish reserved, committed, live, and dead-retained storage in proof
  captures; the current reader separates only the logical-live and backing
  capacity fields present in its input.
- Measure RSS separately and report instrumentation overhead.
- Add known proof allocation/reclamation probes with expected counts and
  high-water marks, and compare instrumented and uninstrumented proof output.
