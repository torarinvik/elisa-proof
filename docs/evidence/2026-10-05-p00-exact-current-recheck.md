# P-00 exact-current qualified-rewrite recheck — 2026-10-05

## Result

The historical qualified-constant crash is **not reproduced by the exact current Stage1 proof
product**. The retained historical binary still reproduces the old failure on the same input. No
cause or fix is established by this comparison.

## Input and products

The input is the existing
[`qualified_constant_return_crash_repro.elisa`](../../examples/qualified_constant_return_crash_repro.elisa),
byte-identical to `/private/tmp/p00-qualified-constant-min-20261005/short_no_final_newline.elisa`:
51 bytes, SHA-256
`3cf171b77ae3bd4d847a3f6c6fd1bb10f40978b189e121e1a1951f086fd94ea2`.

The exact-current product was `build/elisa-proof`, SHA-256
`6502ec0e8f4186ec3afce4ed87bf745dae9e6a9307e813c2821c362686ccde64`. Its adjacent
`build/elisa-proof.manifest.json` matches that binary hash; its manifest sidecar SHA-256 also
matches the manifest file. The manifest records strict O2, target `arm64-apple-darwin27.0.0`, proof
revision `e9d27ef62933944a08f5901f0d5524dfce1a5315`, and proof source-tree digest
`440d09fe92efd5e85788e923a0773c0b05941c4cd99192864b35f80492e928d7` (the tree was dirty because
unrelated concurrent changes were present). It records Stage1 compiler source revision
`e4a16fd24dacb2db54b7cc3aff2d19312ff2edf7`, compiler product SHA-256
`7bcb8590304617b61d1462f6b40c0bff006e3fbe537489d1ce867766e918bd39`, and frontend pin
`7b27fa312c5af923f044f6ee0e5e1de4f811f595` / tree
`ab8926f6080a13d21b06606af251e6f0027c2db5`. The installed `elisac-stage1` freshness check returned
`stage1 provenance: current (7b27fa312c5af923f044f6ee0e5e1de4f811f595)`. The compiler executable
and compiler product hashes were read from the proof product's build manifest; no rebuild was
performed during this diagnostic task.

The comparison binary `build/audit-20261005/elisa-proof-warm` has SHA-256
`74f49810b8988d2e53f38d6298a0e29536299c579363209d464ad2a7b789658a`; its adjacent manifest's
recorded binary hash matches. That manifest records strict O2, a dirty proof tree at revision
`13d686b2b1f863b19eabf53802a10a314f93cfd6`, and a dirty Stage1 source tree at revision
`4c479ad1981403c9f77f04a9ee5918f74713533e`. This is a retained historical crash product, **not**
the unavailable originally measured binary `d734fd75…`.

## Reproduction

Both invocations used `--json` and the exact 51-byte input above:

| Product | Exit | Output | Outcome |
| --- | ---: | --- | --- |
| Current `build/elisa-proof` | 0 | Complete JSON | `proved`; 1/1 obligations; 1/1 certificates replayed; 0 gaps |
| Retained `elisa-proof-warm` | -11 | No stdout or stderr | SIGSEGV |

The current product was run twice via the retained file and the byte-identical in-tree fixture;
both reported the same successful outcome. The historical binary was also run against both
paths and returned `-11` both times.

## What remains unknown

- The original measured binary `d734fd75…` is still unavailable, so its exact failure cannot be
  independently replayed.
- The retained crash binary was built from dirty proof/compiler source trees whose exact source
  contents are not identified by the manifest.
- The old LLDB trace localizes an invalid indexed write in generated code for
  `proof_qualified_body_rewrite`; it does not establish the source of the invalid index or array
  state.
- Current success does not prove a particular change fixed the old defect. No causal source edit,
  compiler regression, or fix is claimed here.
- Linux behavior remains untested.

P-00 therefore remains open. Next useful evidence would be a reproducible build of the historical
dirty compiler/proof trees or the original measured product, followed by a controlled source
bisect and supported-target regression. Do not infer causality from the differing outcomes alone.
