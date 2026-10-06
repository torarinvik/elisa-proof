# P-01 semantic-shape cohort and artifact gates

This milestone advances the P-01 workload inventory without making timing or speedup claims.
The runner has been organized by responsibility: `p01_baseline.py` orchestrates the CLI,
`p01_manifest.py` validates the pinned cohort and build provenance, and `p01_measurements.py`
extracts report counters and enforces admission. All three implementation files are below the
600-line limit.

## Cohort extension

The pinned fixture set now includes positive/refusal pairs for transitive call summaries and value
matches, plus diagnostic workloads for loop invariants, malformed loop input, an include graph,
and high fact growth. The new rows bind path, SHA-256, byte length, source line count, workload
identity, and observed expected process/verdict class. They are marked `identity_only`: this
extends source/workload coverage but does not pretend to pin complete obligation-level semantics.
The older rows retain their full semantic expectations.

P-01 records exact CLI-emitted shape measures: expanded source bytes, source-map file count,
declarations, fact traces, certificate facts, certificates, kernel nodes, and kernel children.
Token count, AST nodes, branch/call/loop counts, and package nodes are explicitly unavailable
because the current proof CLI report does not emit them. No source-text heuristic is substituted.
The sentinel and result schemas were bumped to v4.

## Fail-closed checks

- The proof report must claim a complete whole-program source-obligation inventory. The current
  report implementation explicitly emits `coverage: partial` and `whole_program: false`, so its
  reports are not baseline-admissible even when their emitted goal rows match the manifest.
- Every run binds the cohort's semantic probe to the selected proof binary and verified build
  manifest, and requires the standalone replay artifact to have a verified manifest and coherent
  compiler/source/target provenance with the proof artifact.
- Replay gaps, missing/malformed shape fields, inconsistent cross-section counters, incomplete
  goal inventories, and changed fixture identities remain rejection conditions.

The current local artifact pair is deliberately rejected. At inspection, both manifests named
proof HEAD `ccbd3017ffeb331ff0a2506b563dfb60b0ffd690`, but the proof manifest recorded source-tree
SHA-256 `aa9809fc01bca26c7140760916a52db6110d10f4e5a82718e090c168f0e28a40` while the standalone
replay manifest recorded `f2de1c39f911552cb42bdb97bea3cae55dd9d6736c3969c083c9b7817dcfecf4`.
The proof and replay binary hashes at that inspection were respectively
`e39612966faac546190036bc175e58c66c86dbb8c52f1a5626144bad79f5f5b4` and
`e93b325688cc1f82e63938219893c680879d7079cd63da65cad36e7632f81d53`. The gate refuses this
pair before collecting samples; the prior sentinel pin is also not silently treated as matching.

## Validation

Focused validation passed:

```text
python3 scripts/test_p01_baseline.py
P-01 baseline: fixed identities, scenario labels and replay completeness enforced

python3 -m py_compile scripts/p01_baseline.py scripts/p01_manifest.py \
  scripts/p01_measurements.py scripts/test_p01_baseline.py
```

The focused tests include adversarial mutations for missing/altered metric schema, unavailable
metrics falsely supplied, malformed counters, partial/absent source inventory, mismatched proof
artifact fields, incoherent proof/replay source identities, replay gaps, and incomplete goal rows.
`git diff --check` passed for this milestone. `scripts/check_source_length.py` now reports the P-01
files within the limit; it still reports the unrelated existing
`scripts/test.d/02-regions-and-rewrites.sh` at 605 lines. No P-01 baseline timing run or speedup
claim is made: the local proof/replay pair and the current whole-program inventory gate are both
insufficient for admission.
