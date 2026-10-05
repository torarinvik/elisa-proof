# R-008 certificate producer privacy check

## Scope

On 2026-10-05, branch `codex/r008-private-producers` was created in an isolated worktree from
committed `main` at `1a6554f3c91c88776108921ab831e7b486df32b0`. The shared checkout was left
untouched. Source inspection found five functions that append a `ProofGoalCertificate`:

- `proof_add_goal_attempt`
- `proof_add_resource_goal_attempt`
- `proof_add_effect_goal_attempt`
- `proof_add_structural_goal_attempt`
- `proof_reuse_goal_attempt`

The four specialized admission and reuse functions already belonged to `private:` sections.
`proof_add_goal_attempt` in `src/proof/model/report_recording.elisa` was the only producer under
`public:`. Its callers are in `src/proof/check/returns/contracts.elisa`,
`src/proof/check/index_checks.elisa`, and `src/proof/check/bounds_and_facts.elisa`. Moving its
definition under `private:` preserves those in-module calls and removes the public producer.

Commit `7334c8228a487bd5d6b5a308adcc6bffd7a04b4a` makes that change and adds a static check to
`scripts/test_kernel_inventory.py`. The check enumerates all certificate producers and fails if
any producer is in a public visibility section.

## Validation and identity

- `python3 scripts/test_kernel_inventory.py`: passed; 10 tables and 169 entries match source.
- Strict optimized proof build: passed using Stage1, `-O2`, target `arm64-apple-darwin27.0.0`.
- Quantifier tactic runtime: passed on `examples/verified.elisa` with
  `examples/tactic_script_quantifier.json`; tactic valid and solved, kernel trace replayed,
  kernel replayed, and certificate replayed.
- Build identity: `0b827dae0f2a80b4b3090c4d054b606d14c577ac1e0567a8e4604161d3a1be32`.
- Executable SHA-256: `695567e2a1873259b913164ccbc2c026c1be07d7ee0b1327df95425a2ff09ef3`.
- Proof source HEAD: `7334c8228a487bd5d6b5a308adcc6bffd7a04b4a`; source was clean at build.
- Compiler Stage1 source revision: `bc8def2eadf41dd088adce22b4d3d9e74aadfee9`.
- Pinned frontend revision/tree: `7b27fa312c5af923f044f6ee0e5e1de4f811f595` /
  `ab8926f6080a13d21b06606af251e6f0027c2db5`.

The system Bash 3.2 build invocation stopped at the script's empty-array expansion under `set -u`.
Repeating the same build with installed Bash 5.2 passed; no build-script source was changed.

## Limits

This closes only the explicit source-visibility gate for currently discovered
`ProofGoalCertificate` appenders. The inventory scan does not prove Elisa's privacy enforcement,
prevent public code from mutating report storage through other APIs, or establish producer
soundness. It does not cover other certificate-like data, theorem constructors outside this
struct, every transitive trust dependency, or formal soundness of any rule. R-008 remains open.
