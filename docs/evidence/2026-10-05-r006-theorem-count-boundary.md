# R-006 theorem count boundary — 2026-10-05

This focused regression covers the portable package theorem-count cap only. R-006 remains open.

## Source and product identity

- Isolated worktree: `/private/tmp/elisa-r006-count-cap`
- Branch: `codex/r006-count-cap`
- Exact base at worktree creation: `b7f5dd7483dce0b0e0774b35d390a49a19d5ba93`
- Test commits: `0c55cc303976493141f70b535294ba426d4434a7` and
  `1c10869f` (full commit `1c10869f` is recorded in Git; it only corrects the refusal summary
  assertion). The final evidence note is committed separately.
- Strict pinned O2 proof source revision embedded in both products:
  `0c55cc303976493141f70b535294ba426d4434a7`, source tree SHA-256
  `ab762c07a202b0dcdc4d5a51a02f027996d1e04b3e2274773174217c0a2b053d`, `source_dirty=false`.
- Build command: `ELISA_PROOF_PRODUCTS=all ELISA_PROOF_BUILD_JOBS=2 scripts/build.sh`
- Pair generation: `637b88407b6642da9168017be011da8d`
- Compiler: pinned frontend `7b27fa312c5af923f044f6ee0e5e1de4f811f595`, Stage1 source
  revision `bc8def2eadf41dd088adce22b4d3d9e74aadfee9`, Stage1 product SHA-256
  `96eca8200bb268ea5cc1635a66d6b0da0cd85611331319c3227362d9421c2947`, clean source;
  target `arm64-apple-darwin27.0.0`.
- `build/elisa-proof` SHA-256:
  `9300837426ae905c623d294f24fd14d7b419dc848dcb7e6c1474d9e102311507`.
- `build/elisa-proof-replay` SHA-256:
  `1eb870ab4cf6c63805d109bf0eff636ea3ff2ba0281f2130de398654181293ac`.
- Manifest SHA-256 values: proof `80e853221630317b9c3c97e428b0bd31e741911d8ba0d03d84298d8fb8b9e7de`;
  replay `d3cd8e2b42a8d91b2af533ec1139fcaf8c5596a7eabd04c5d4f73664fabccefa`.

## Regression and observed boundary

`scripts/tests/test_portable_package_theorem_budget.py` exports the committed `verified.elisa`
package, repeats its first theorem, serializes each input, and invokes the replay executable in a
fresh subprocess for each case:

- Exactly 65,536 theorem entries: exit 0, status `replayed`, and summary reports all 65,536 as
  replayed with zero not replayed.
- 65,537 theorem entries: exit 1, status `over-budget`, reason `theorem-budget`; theorem result
  list is empty, summary reports zero inspected/replayed/not-replayed, and the structured stdout
  is under 4,096 bytes. The reader rejects before any theorem is partially replayed.

The exact-limit process has a 180-second timeout. The one-over response size is explicitly
bounded by the regression; CPU/RSS stress near this count is not characterized by this test.

## Validation

Against the product pair above:

- `python3 scripts/test_portable_replay.py` passed: 16 positive packages, existing refusal
  corpus, 528 fresh bounded raw-byte decoder runs, and the structure-aware malformed-package
  cases all passed.
- `python3 scripts/tests/test_portable_package_theorem_budget.py` passed the exact-limit and
  one-over cases above.

This establishes one theorem-count boundary on the portable package reader/checker path. It does
not establish the rest of the decoder inventory, all other count/index/byte boundaries, parser plus
checker fuzzing, or worst-case resource behavior, and it does not complete R-006.
