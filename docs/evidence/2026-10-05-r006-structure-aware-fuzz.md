# R-006 structure-aware portable-package fuzzing

## Scope

Added a distinct adversarial test module, `scripts/tests/portable_replay_structure_fuzz.py`,
and registered it in `scripts/test_portable_replay.py`. The test starts a fresh replay process for
each input, caps each invocation at 4 CPU seconds and 5 wall seconds, samples process RSS and kills
at 512 MiB, caps captured output at 4 MiB, checks structured trust/result consistency, and retains
unexpected inputs as content-addressed JSON seeds after up to 64 greedy schema-member/array-entry
deletions that preserve the same failure class. No failure was found, so no seed files were
produced and no decoder code changed.

The deterministic matrix exercised 28 malformed or adversarial inputs:

- One wrong-typed field at each of five JSON nesting depths: 32, 128, 512, 2,048, and 8,192.
- Eight theorem-root index encodings covering the exact JSON integer boundary and negative,
  fractional, Boolean, and null values.
- Five child-index encodings; four child-range/index combinations; and two out-of-arena node refs.
- Two reachable node cycles and one forward reference, each refused specifically as
  `arena-inadmissible` before any theorem result can be reported.
- One 8 MiB source-path string, rejected by the package string budget after parsing.

Every refusal was checked for a structured replay result, a consistent theorem summary, and no
`replayed` status. The full portable replay entry point also replayed all 16 positive packages and
ran the existing semantic/package attack matrices. Tests ran from fresh processes, not an in-process
decoder binding.

## Validation identity

- Committed baseline: `b579301922c46cc454b465e91fad79a69e85115a` (clean detached worktree).
- Compiler: fresh installed Stage1 snapshot, revision `7b27fa312c5af923f044f6ee0e5e1de4f811f595`;
  the Stage1 provenance guard reported `current` before both products were built.
- Compiler product SHA-256: `3e23836002e5b6035dba43185ea84a9ab5358707c1ee4148c4752cacb2f41a70`.
- Frontend source revision: `7b27fa312c5af923f044f6ee0e5e1de4f811f595`.
- Proof binary SHA-256: `7cc1f41d6513887b899822a7a559c2216ce2545535e33ac53d0eb6c32c2ff9ca`.
- Replay binary SHA-256: `ce1310d3893ed2414e57a9306c24b7c7dc44d8ab34ed7e3f4a29ba81e1061faa`.
- Both build manifests name the same proof HEAD/tree and frontend revision; products were built
  together in the isolated worktree and not written to shared `build/`.
- On the test host’s 8 MiB parser workload, peak sampled replay RSS was 26,492,928 bytes, peak
  observed CPU was 0.050 seconds, and peak wall time was 0.070 seconds. Limits were 512 MiB RSS,
  4 seconds CPU, and 5 seconds wall per fresh process.

## Remaining gaps

This is a deterministic mutation matrix, not coverage-guided fuzzing. It does not yet mutate raw
certificate bytes systematically, explore every JSON parser token/escape production, test maximal
valid package dimensions, or sustain memory pressure near the configured limits. RSS is sampled
while the child runs; the host’s macOS `RLIMIT_AS` hard limit cannot be lowered by this test process,
so RSS is actively monitored and exceeded runs are killed rather than relying on address-space
limiting. The test’s seed retention is exercised only if an actual failure occurs.

The repository-wide source-length check still reports the pre-existing `src/app/cli.elisa`
614-line limit violation; this unrelated finding was left outside the R-006 change.
