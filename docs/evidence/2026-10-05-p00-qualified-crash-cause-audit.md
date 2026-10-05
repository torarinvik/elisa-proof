# P-00 qualified-constant crash cause audit — 2026-10-05

This follow-up checks the retained historical O2 product and the source changes around its
qualified-constant body rewrite. It narrows the triggering path but does not establish a source
or compiler defect.

## Reproduction and controls

The retained product is
`build/audit-20261005/elisa-proof-warm`, SHA-256
`74f49810b8988d2e53f38d6298a0e29536299c579363209d464ad2a7b789658a`. Its manifest identifies
strict O2, arm64 macOS, proof HEAD `13d686b2`, a dirty proof tree, and a dirty Stage1 compiler
checkout at revision `4c479ad1981403c9f77f04a9ee5918f74713533e`. It is not the unavailable measured
product `d734fd75…`.

I reran every retained `*.elisa` control in
`/private/tmp/p00-qualified-constant-min-20261005/` with that binary and `--json`. The exact
51-byte input (`short_no_final_newline.elisa`, SHA-256
`3cf171b77ae3bd4d847a3f6c6fd1bb10f40978b189e121e1a1951f086fd94ea2`) exited `-11` with no
stdout or stderr. Qualified returns, a qualified contract, and qualified assignment also exited
with signals and no output. Module-constant-only, plain-literal return, bare unqualified constant
return, and bare return controls completed with JSON. Results varied between SIGSEGV (`-11`) and
SIGBUS (`-10`) among qualified-use controls; the shared symptom is process failure before JSON.

The retained LLDB trace for the exact 51-byte input stops in the generated code for
`proof_qualified_body_rewrite`, at an indexed store into its rewritten-statement array. The base
points into arena storage while the index register contains a stack address
(`0x16fdfa010`), causing the invalid write. The trace is consistent with invalid append/index
state; it does not identify how that state was produced.

## Source history inspected

At proof commit `e110a2a1`, body replacement was changed to build a rewritten array and copy it
element by element, following stricter compiler region checks. At `e22f33d3`, the expression
rewriter gained a borrowed `storage_body` parameter threaded through recursive expression and
statement rewriting, and the body rewrite was called with `function_body` as both `body` and
`storage_body`. The original minimized case reaches the `Ast::Stmt.Return` branch. These edits
make region/borrow handling a plausible area for compiler-level investigation, but history plus
the crash trace is correlation only: no experiment isolated either edit as the cause, and the
historical binary's dirty source tree cannot be reconstructed from its manifest.

## Current-product control and remaining work

The identified strict O0 and O2 products in
[`2026-10-05-p00-identity-matrix.md`](2026-10-05-p00-identity-matrix.md) pass
`scripts/test_qualified_constants.py`, including the exact minimized fixture, with one obligation
proved, one certificate replayed, and zero gaps. This is a current-product control, not evidence
that the historical defect is fixed.

No source correction was made because the cause is unproven. The original measured binary remains
unavailable, its dirty source tree cannot be reconstructed, and no Linux product is available.
P-00 still needs a source/compiler-level isolation and fix with a regression on supported targets.
