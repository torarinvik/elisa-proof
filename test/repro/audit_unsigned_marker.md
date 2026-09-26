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

### General marker dispatch

The same failure-node allocation pattern also occurred in marker classification,
root lookup, signed-width lookup, and scalar-name lookup. Those queries now select
the applicable parser by the exact bare callee name. The unsigned classifier still
checks both its identifier and place forms; no width, arity, or argument-name
validation was removed. Dispatch is not itself evidence that a marker is valid.

After this change the decoder regression completed at 66,384 KB. An eight-module
replay prefix that previously hit the watchdog completed at 717,601 KB, with zero
replay gaps and an unsupported verdict. The full standalone replay and main-source
audits still hit the memory watchdog (about 15 and 17 seconds respectively).

`examples/marker_dispatch_runtime.elisa` preserves the old queries as test oracles.
It compares classification, root identity, and signed-width selection over 1,521
facts, including malformed arities, inconsistent argument-name counts, invalid
widths, non-place terms, and parenthesized callees. Width lookup is checked both
against the complete fact list and every singleton, so an early matching marker
cannot mask later cases. This native test passed, the 45 earlier fixture reports
were unchanged, and eight additional signed/difference/overflow fixtures retained
their expected verdicts with complete certificate replay.

### Operator-witness and type-bound scans

Exact-name filtering now also covers operator-witness queries, retained type-bound
names, signed-context classification, and signed-bound collection. The read-only
operator queries live in the private `check/operator_witness_queries.elisa` module;
witness construction remains in `operator_witnesses.elisa`, keeping both under the
600-line source limit. The differential oracle corpus includes builtin, untrusted,
and indexed operator markers, including malformed protocol arguments.

The complete standalone replay audit now finishes under the unchanged watchdog:
38.45 seconds, sampled peak 1,179,697 KB, 1,807 obligations, 860 proved obligations,
and zero replay gaps. **Completion is not verification of the replay system.** Its
top-level verdict is `failed` / `disproved`: there are 1,065 findings, dominated by
unsupported borrow/call summaries and analysis budgets, plus 29 resource-violation
findings. Those findings need source-level investigation; they are not yet
independently confirmed bugs. In particular, inspect region-use findings in
`proof_kernel_replay_resource_lend` and borrow-write findings in
`proof_kernel_replay_arena_valid_with_workspace` and
`proof_kernel_replay_resource_parameters`.

The main-source audit still exceeds 1,500,000 KB. The expanded native query oracle
passed, 45 earlier fixture reports were unchanged, 20 additional arithmetic,
operator-effect, and string-view fixtures had their expected verdicts and complete
replay, and all nine watchdog tests passed.

### Resource diagnostic follow-up

The 29 apparent violations above were diagnostic classification bugs, not
demonstrated resource violations. Unsupported aggregate-copy provenance reused a
false region-liveness bit; reads and writes mistook that unknown lifetime for
proven destruction. Opaque mutable-reference write targets likewise became
definite borrow conflicts without a tracked place. Explicit destruction evidence
now distinguishes the former, and opaque writes report unsupported provenance.
Neither change admits a new proof or weakens certificate replay.

The rerun completed in 36.99 seconds at 1,179,761 KB, with the same 1,807
obligations, 860 proven obligations and zero replay gaps. Its verdict is now
`failed` / `unsupported`, with no `disproved` findings. This is still not
self-verification: unsupported summaries and analysis limits remain unresolved.
Three new regression fixtures cover both unsupported cases and actual destruction
followed by a branch-local write. All 45 baseline reports were unchanged, and 22
additional region/string-view fixtures retained their expected verdicts and
complete replay.
