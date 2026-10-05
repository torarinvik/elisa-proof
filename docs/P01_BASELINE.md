# P-01 bounded baseline runner

Run `python3 scripts/p01_baseline.py --output /tmp/elisa-p01.json` after building the proof CLI. The runner never invokes a build. It runs three pinned repository fixtures serially: a small accepted real-code example, a refusal example, and the rejected symbolic-quantifier adversarial example. It records fixture and binary SHA-256 identities, platform/target, optional frontend-pin and runtime-object identities, wall time, sampled process RSS, declaration and obligation counts, and replay completeness.

Each fixture gets a fresh-process cold invocation, an identical fresh-process warm invocation, and a source copy with a comment-only edit. The warm invocation means the OS may have cached file pages; the CLI has no persistent proof session, so this does not claim a warm proof-cache hit. The small accepted fixture also gets a fixed `value == value + 0` body edit. These runs establish repeatable CLI measurements and source identities; they do not measure incremental declaration reuse.

Every report must be valid JSON, contain summary/replay objects, have zero replay gaps, and have equal replayed/certificate counts. A timeout, RSS cap, invalid JSON, truncated report, or replay gap fails the run without emitting a successful baseline. Default limits are 20 seconds and 1,500,000 KiB per child; both are configurable. The report schema is `elisa-proof-p01-baseline-v1`.

## Current counter coverage

The primary JSON `measurements` object serializes per-report goal-cache hits and misses, measured control-flow steps, and peak live facts. The bounded runner records these values for every cold, warm, no-op, and edit invocation and rejects reports where a counter is absent or invalid. Source import, parse, semantics, VC generation, search, replay, reporting timings and the other planned stage counters are still not instrumented; the manifest names these gaps explicitly and does not estimate counters from elapsed time.

The current runner's repeated CLI invocations cannot establish persistent warm-cache, no-op product-build, or incremental edit latency. Those require the P-03/P-05 build and session paths. Keep this result as a bounded correctness and cold-start baseline, not a speedup claim. One run per scenario is an initial baseline only; the plan's seven paired rounds and CPU time remain outstanding.
