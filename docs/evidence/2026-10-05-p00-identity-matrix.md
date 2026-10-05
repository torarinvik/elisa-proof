# P-00 identity-bound O0/O2 matrix — 2026-10-05

This matrix checks the retained 51-byte qualified-constant reproducer and the two original
workloads against identified strict Stage1 products. It establishes current behavior on this
machine only; it does not reproduce or explain the historical crash.

## Products and inputs

Both products are strict Stage1 builds from proof source-tree digest
`1f273bf1ec466404c40a5d3f86f0654a6c42df0679541f0f1b1fd06366411ee9`, frontend/Stage1 revision
`7b27fa312c5af923f044f6ee0e5e1de4f811f595`, Stage1 compiler SHA-256
`f77278c716dea7f3dba8f4fcbcf76ecc473426ab3f163c95fea4e358f6337653`, runtime-object SHA-256
`b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`, and target
`arm64-apple-darwin27.0.0`.

| Optimization | Product SHA-256 | Manifest SHA-256 |
| --- | --- | --- |
| O0 | `1a1ea6eac860ffc3854f7bd209135f4513ce97780639853a0c1993b323ea2d8e` | `cf25f6bd4155207cbca7dba5734d7eb74c0c91758a25a167f196a522999990f6` |
| O2 | `549ae6fbae4e9a4d09373a537eec6c13f3701747d8a8d95ed8bce11d308e6d36` | `2fc62f277729d7b23b344a8cd4091bf62c03b143edbe734c172861257ca412bd` |

The 51-byte `qualified_constant_return_crash_repro.elisa` has SHA-256
`3cf171b77ae3bd4d847a3f6c6fd1bb10f40978b189e121e1a1951f086fd94ea2`. It contains the exact
`module M` / `M::A` minimized case retained by the focused suite. The kernel-comparison workload
was read from a clean archive of proof revision `b12b41fcab2bea735fa244e734a07744652655d0`,
whose source-tree digest matches both product manifests; its SHA-256 is
`905a041e2d2a517662a9707b25198f28856c285e6c46be43eeb7c510d1f2bc0a`. The mocap checkout was
clean at revision `30bceec4d69cec5bf85f11e338ab1d8d15276d80`; `src/tools/track.elisa` has SHA-256
`2723d053f74f17cf3776db4a5833f6f6439cb158b4bef58f0cd2e34f37e2aa22`.

## Results

All six invocations emitted complete JSON and zero stderr bytes. The exact minimized repro returned
0, proved its one obligation, replayed 1/1 certificates, and had zero replay gaps on both O0 and
O2. Thus the crash trigger does not reproduce on either identified current product.

| Workload | O0 result | O2 result |
| --- | --- | --- |
| `examples/kernel_comparison_runtime.elisa` | 56.04 s; 3,831 obligations, 2,575 proven; replay 2,575/2,575; 0 gaps; exit 1 (unsupported findings) | 14.69 s; 3,831 obligations, 2,575 proven; replay 2,575/2,575; 0 gaps; exit 1 (unsupported findings) |
| mocap `src/tools/track.elisa` | 17.91 s; 943 obligations, 926 proven; replay 926/928; 2 gaps; exit 1 | 3.82 s; 943 obligations, 926 proven; replay 926/928; 2 gaps; exit 1 |

The two track replay gaps remain the known `Slide.inner` conditional-return gaps described in the
proof-queue evidence. The `failed` report status and exit 1 for each large workload reflect
unsupported/unproven findings (and, for track, replay gaps), not a crash or incomplete JSON.
`scripts/test_qualified_constants.py` also passed with each product selected by
`ELISA_PROOF_BIN`, including the minimized regression and positive/negative qualified-constant
controls.

## Scope and limits

The initial exploratory workload invocation accidentally read four concurrently modified files
from the shared checkout and produced parse errors / a different census. Those outputs were
discarded. The kernel-comparison workload was rerun from the clean archived source revision named
above; track was rerun from its separately identified clean checkout. The minimized case has no
source imports and was invoked by its byte-identical hash above.

The original measured executable SHA-256 `d734fd75…` remains unavailable. The retained historical
binary `74f49810b8988d2e53f38d6298a0e29536299c579363209d464ad2a7b789658a` is not substituted for
it, and its earlier LLDB trace remains symptom evidence only. The retained Stage0 executable
`build/elisa-proof-stage0` (SHA-256 `1265bada7c68270516e46828231baf0eadd4c1cf7d7ead9bcc090febe078f4fa`)
has no adjacent build manifest or verifiable matching build procedure, so it was excluded from
the matrix. No Linux product was available. No source-backed cause or fix was identified.
