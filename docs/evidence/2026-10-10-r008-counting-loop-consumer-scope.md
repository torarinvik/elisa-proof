# R-008 counting-loop consumer scope qualification (2026-10-10)

## Result

The focused counting-loop consumer-scope candidate passed direct-API qualification and the
loop-invariants regression. The full portable replay suite remains open: its existing dynamic-array
early-return example has one unreplayed `index-upper` obligation, which makes the exported source
inadmissible. That gap also reproduces with the prior matched generation `c58ba02114fe40fe8f303815855cafbd`.

## Compiler and products

- Fresh Stage1 checkout: `../local-compiler-optimization-20261009/parser-effect-template-working`
- Compiler revision: `8f2023ce8a7d52358b733a0e812ff46293d45f10`
- `bash scripts/assert_stage1_fresh.sh bin/elisac-stage1`: passed.
- Build: strict O2, matched proof/replay generation `83c85e661cf9470daefc04f1fc3a68f7`.
- Proof binary SHA-256: `278dcf85563c1f185609109e3b0fc486f226da91fd1da9ff81fbd2e22de37372`.
- Replay binary SHA-256: `5a56274507ff4ec397f04975bb92f95dbce458b4f2cb38752f0b09f6101f2572`.
- Compiler Stage1 product SHA-256: `2faf57f2dca6914d3f500c6b4532fb993349208ff556459de0a6af025688c644`.
- Proof source tree hash at build: `aae8279b5465d4eabaa3373b92fa2e6d9878721e687c815ac01e764f47771b32`.
- Both immutable generation manifests identify the same Stage1 revision, O2 mode, and generation.

The consumer check requires a unique matching certificate attempt with the same owner, line,
proposition, and complete source span, then verifies the proposition is within the source loop body.
It rejects absent or partial consumer context, loop-header consumers, post-loop uses, and an attack
that moves both certificate and attempt to the loop-body line. The AST visitor is checked against
all 13 statement variants in the pinned parser snapshot. The local unsigned while-loop self-update
also replays without gaps after its type witness is authenticated against a live local binding.

## Checks

- `python3 -m py_compile scripts/source_binding_harness_support.py scripts/test_direct_api_semantic_admission.py`: passed.
- `python3 scripts/check_source_length.py`: passed.
- `git diff --check`: passed.
- `python3 scripts/verify_product_pair.py resolve --generation-root build/elisa-proof-generations`: resolved both products to generation `83c85e661cf9470daefc04f1fc3a68f7`.
- `python3 scripts/test_direct_api_semantic_admission.py` with `ELISA_COMPILER_ROOT` set to the fresh Stage1 checkout: passed. Output covered source-goal identity, loop-binder scope, Global grants, source-bound refinements, and reused-state clearing.
- `python3 scripts/test_loop_invariants_compile.py` with the matched pair and pinned frontend: passed its targeted source-bound replay controls. Its fixture retained three unrelated replay gaps, which this focused test permits.

## Remaining broad-suite gap

`python3 scripts/test_portable_replay.py` stopped at the positive-package admissibility assertion for
`early_return_index_guard`. The proof CLI reports `proved_with_replay_gaps`; its three obligations
are resource-safety (replayed), `index-lower` (replayed), and `index-upper` (gap). Because source
replay does not accept every obligation, package export correctly marks the source inadmissible.
The next focused task is to authenticate the dynamic-array `.count` upper bound through the
early-return branch and add a refusal control for a nearby or unrelated forged bound. Do not mark the
portable suite green until this example and all subsequent positive and refusal cases pass.

This qualification closes only the counting-loop consumer-scope subgate. It does not qualify the
broader type-bound provenance ledger, the fixed-array candidate, or the complete portable replay
suite.
