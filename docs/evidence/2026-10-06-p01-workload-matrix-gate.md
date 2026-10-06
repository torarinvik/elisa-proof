# P-01 closed workload identity gate

This milestone closes one narrow P1.1/P1.2 inventory-integrity gap. Every fixture in the current
11-entry P-01 cohort now names one workload record, and every workload record explicitly names its
members, shape, and source relation. The loader rejects workload records that are missing, orphaned,
duplicated, refer to an unknown fixture, or disagree with the fixture's workload name. The fixture
rows continue to pin source path, digest, bytes, lines, expected result status, obligation identity
and details, trusted assumptions, and certificate/replay totals. A workload label does not make a
fixture measurement-eligible: the existing admission checks still reject incomplete obligation
inventory and replay gaps.

## Focused adversarial validation

`python3 scripts/test_p01_baseline.py` passes. Its manifest mutation controls reject:

- omitted fixture and workload records;
- missing, stale, or changed source identity;
- missing/contradictory expected status or semantic expectations;
- omitted obligation/assumption rows and inconsistent replay totals;
- unknown or duplicate workload members and fixture/workload identity disagreement.

The current manifest deliberately assigns `adversarial` a partial 78-obligation/77-row inventory and
retains the branch-join and qualified-constant replay-gap cases as diagnostic workloads. Neither
those entries nor a valid identity map makes them admissible timing samples.

## Fresh exact-product check

The guarded `./scripts/build.sh` Stage1 build completed from the current proof tree. The new
`quantifier_success` cohort member was then run through that exact binary and checked against its
manifest semantic expectation using the P-01 report validator; the post-run fixture and binary
identities were rechecked.

- Proof commit: `dfa9ee9226a28fa57a38d3d1f520ee2d611bbdbc` (source tree marked dirty; exact tree
  digest is recorded below)
- Proof source tree SHA-256: `0fecb41651fe5c860d21de10c9241b4440cbe515fbf13682a5e7f998cde81748`
- P-01 fixture: `quantifier_success`, `examples/quantifier.elisa`
- Fixture SHA-256: `1ac3c5e4f2a1b09586396a02cd2a19b9a28b4c766d50b080075b233aeb2bd655` (480 bytes,
  20 lines)
- Semantic parity: expected/observed `proved`; 10/10 obligations proved; 0 trusted assumptions;
  3 boundary facts; 10 proof certificates, all 10 replayed, 0 replay gaps; pinned obligation and
  trust details match
- Build identity: `651e854e4bb734744840b746fd65c851dcfa14322d1405b4c64656f35682c66c`
- Stage1 product SHA-256: `65a9308c53b510365aa69644a0bcaa9a071ea2006683dad6bf2ec12fc394f6b3`
- Compiler source revision: `6b475d894331f0a81c3112167ef7fcf5c642a424`
- Frontend tree identity: `401bd5368e7909168e9500c872ab122ae421750c`
- Runtime object SHA-256: `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`
- Target/configuration: `arm64-apple-darwin27.0.0`, strict, O2

This was a semantic identity/parity check, not a timing sample. The checked-in `semantic_probe`
still records its earlier multi-fixture probe, and this milestone does not claim a refreshed
cohort-wide probe or performance baseline.

## Still missing for P1.1/P1.2

The cohort is not yet the canonical operation matrix from §23.24.4: cold/warm/no-op and edit/build
operations are not all pinned as independent workload identities; malformed and unsupported
fixtures, package import/replay, high-fact stress, and additional call/branch/loop/ADT shapes remain
to be added. AST-node and structural size bands (declarations, facts, branches, calls, package nodes,
and certificate DAG size) are also not inventoried. Therefore the P1 baseline exit remains unmet.
