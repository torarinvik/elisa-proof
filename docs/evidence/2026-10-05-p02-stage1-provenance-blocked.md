# P0.2 Stage1 provenance recheck (2026-10-05)

The proof build was not started with the adjacent Stage1 product because its provenance check
fails closed against the compiler checkout's current source tree.

Command:

```sh
python3 ../Elisa-compiler/scripts/stage1_provenance.py check \
  ../Elisa-compiler ../Elisa-compiler/bin/elisac-stage1
```

Observed result: exit status 2, `stage1 product is stale: provenance mismatch in source_tree_sha256`.

## Identities at the check

- Compiler checkout HEAD: `ecd26eb776ef72e6c25bb0cec7129344acf0f2fd`.
- Current `src` + `elisacore_std` tree SHA-256: `e1d9337bb114df7e853a6bfa6b88a9e4d423204e8c48f87b57a22345492cda7c`.
- Stage1 sidecar's recorded source revision/tree: `ecd26eb776ef72e6c25bb0cec7129344acf0f2fd` /
  `ccbf9946e812abe364a9fa7ceae091ce61d70b662ed0a1c596ed958fc23e299d`.
- Stage1 binary SHA-256: `5b9effba69daeee0d7e87d7c7ba7142e386542b4b8f1ca4f8e1074d5e35ed7bb`.
- Build-recipe SHA-256 matches the sidecar: `a1fbbac38ae3c1dd91798f751f7b6960391e2173979faa54046535c7f5416c1c`.

The source revision is unchanged but the working source tree is not. The compiler checkout has
uncommitted and untracked parser, lowering, semantic, and fixture changes. An attempted Stage1
seed was also stopped by the Stage0 freshness guard because compiler source files were uncommitted;
no stale-oracle bypass was used and no compiler files were changed by this proof-side check.

The proof/replay generations available for nearby checks use the older pinned Stage1 identity;
they cannot establish a matched strict O2 pair for the integrated proof HEAD. After the compiler
source changes have a stable intended snapshot, rebuild Stage0/Stage1 through the compiler's
normal freshness path, recheck provenance, and then run the proof/replay pair gate from an
immutable proof snapshot. P0.2 and P0.3 remain open.
