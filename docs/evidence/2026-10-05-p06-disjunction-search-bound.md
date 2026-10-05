# P-06 bounded disjunction search evidence

## Build identity

The integrated proof and portable replay products were built at O2 from the proof source tree digest `dc795bfe1c27a531bd5d19029338c12bd3ddcd6143fbc3fc2ac2fc2da1c674f0` with the pinned Stage1 compiler revision `7b27fa312c5af923f044f6ee0e5e1de4f811f595`, Stage1 binary SHA-256 `f77278c716dea7f3dba8f4fcbcf76ecc473426ab3f163c95fea4e358f6337653`, and target `arm64-apple-darwin27.0.0`.

- Proof binary SHA-256: `9d4c4e21e50136996a84f5401adc305f5d8c18d89048ceb22588c2a12f259e63`
- Portable replay binary SHA-256: `50d61888366f0039e934c3e120a807e0009262ef2c8cd9d2bbdc40211d5ab78f`
- The build manifests are `build/elisa-proof.manifest.json` and `build/elisa-proof-replay.manifest.json`; the generated files are ignored build output, so the identities above are recorded here.

## Change and focused checks

The producer and kernel replay now classify disjunction premises as directly relevant to a goal, fully refuted, or unrelated. The bounded entailment scan skips unrelated premises and keeps fully refuted premises eligible for the existing contradiction check. Both sides use the same limit of eight failed, directly relevant candidates.

`scripts/test_disjunction_search_bounds.py` passes. It checks irrelevant premises before a late relevant fact, eight and nine relevant but inconclusive candidates, a later proof through disjunctive syllogism, and a contradiction premise whose alternatives are all refuted. `scripts/test_disjunction_domain.py` also passes. The selected unsigned, correlated, chained, and conditional disjunction regressions pass on the same O2 proof product; every admitted goal replays and the reports have zero replay gaps.

## Limits

After eight relevant candidates fail, additional directly relevant premises are not searched in that pass; the regression expects an `unknown` result for this budget boundary. The later syllogism path remains available and is covered separately. No paired uninstrumented timing was taken, so this change is not recorded as a measured speedup. The proof source and binary remain local measurements; Linux coverage is still open.
