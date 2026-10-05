# R-015 dogfood kernel-package consumer

The dogfood kernel self-audit now resolves the published product pair once with
`verify_product_pair.py resolve`, then exports both `kernel_core` packages with
the resolved proof binary and replays them with the resolved replay binary. The
focused static regression requires one pair resolution in this section and
rejects fallback use of the legacy proof/replay filenames.

## Evidence

- Integration commits: `afd822d7` (pair-pinned export/replay) and `e5b841bf`
  (static regression wired into the test suite).
- Focused command: `python3 scripts/tests/test_dogfood_package_pair_resolution.py`.
- Result: passed (`dogfood portable package: one generation-pinned proof/replay resolution`).
- Shell syntax and whitespace checks passed in the agent branch.

This is wiring evidence only. The full dogfood suite was not run here, so this
note does not claim that the packages were exported and replayed successfully
against a real published pair, nor does it validate the proof semantics of the
kernel package.
