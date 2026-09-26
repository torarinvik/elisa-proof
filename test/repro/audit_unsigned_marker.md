# Unsigned-marker self-verification memory regression

This diagnostic isolates the replay unsigned-marker decoder and its dependencies.
It is not an expected-pass proof fixture. Its purpose is to reproduce excessive
verification memory use without importing the entire replay implementation.

Run from the repository root after building:

```sh
ELISA_FULL_AUDIT_SOURCE=test/repro/audit_unsigned_marker.elisa scripts/audit_full_source.sh
```

Observed on 2026-09-26 with Stage0 revision
`45ea9245a5e3e5143fea58fa1ae59d7589249d4d`, frontend revision
`303557a87627dfd37f1281510beea85c7bca4991`, and proof revision `03ddaf7`
plus the working-tree index-certificate memoization experiment:

- The isolated decoder exceeds the unchanged 1,500,000 KB physical-footprint
  watchdog in approximately one second, before emitting a report.
- A source prefix ending before the decoder (through line 402 of
  `src/proof/kernel_replay/term_arithmetic.elisa`) finishes around 340 MB.
- Extending that prefix through the decoder's `first_index`/`second_index`
  bindings and bounds guard finishes around 366 MB.
- Adding the `argument_nodes_valid` initializer raises that to about 993 MB.
- Adding its following conditional return exceeds the watchdog.
- Replacing the six conjuncts with equivalent individual early-return guards
  lets the extended prefix finish around 1,029 MB. Its result is **unsupported**,
  not proved; certificate replay has zero gaps.
- Splitting the earlier `marker_call_valid` condition alone does not help.

These are localization measurements, not a root-cause diagnosis or a fix. Peaks
are sampled and machine-dependent. Do not encode them as exact assertions or
raise the memory limit to turn the failure green. Investigate expression/fact
copying and repeated checking at the initializer and conditional-return boundary.
The permanent fix must preserve all marker-shape checks and independent replay.

## Allocation fix and remaining work

The live native sample showed repeated marker decoding during scalar-witness
scans. Unrelated facts caused the parsers to allocate fresh `Invalid` AST nodes
in the long-lived source store. A callee-name prefilter now skips those misses;
matching candidates still undergo the same full parser validation. Hypothetical
field comparisons also no longer construct temporary AST field nodes.

With those changes, this unchanged reproducer completed in 2.71 seconds at a
sampled peak of 236,576 KB, with zero replay gaps. It still correctly reports
unsupported work (untracked string-view provenance, an unmodeled operator, and
a symbolic fact-state budget). This is not a proof of the decoder.

The 45 scalar/indexed/overloaded/unsigned fixture reports were unchanged, including
findings and replay counts. The native field-comparison test checks equivalence
against constructed-field equality at malformed and depth-limit boundaries, and
checks that the marker filter retains every recognized marker in its corpus.

The full standalone replay and main-source audits still exceed the unchanged
1,500,000 KB limit. This fixes the isolated allocation regression, not all
self-verification scalability problems. The test matrix now runs this reproducer
as a watchdog-completion regression without requiring a proved verdict.
