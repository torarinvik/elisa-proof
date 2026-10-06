# Q0.11 call-boundary experiment — 2026-10-06

## Outcome

This experiment narrows the historical qualified-constant crash to state already
present in `proof_qualified_body_rewrite` before the expression-rewrite call. It
rules out two narrower candidates for this captured execution: clobbering of the
index register by `ctx_aos_store_record`, and clobbering by
`proof_qualified_constant_rewrite`. It does **not** distinguish a historical
source-level rewrite-state error from compiler lowering/register-allocation of
the enclosing rewrite, and it does not establish a fix.

The old fault reproduces only on the retained historical executable whose
manifest records dirty, unrecoverable proof and compiler source trees. On the
provenance-validated current O0 and O2 pairs, the exact minimized input proves
and replays without a crash. Therefore the old crash cannot be causally
reproduced from a known source revision at this time.

## Isolated workspaces and product identity

The experiment used clean detached worktrees, leaving the primary checkouts
untouched:

- Proof source: `/private/tmp/elisa-proof-q011-abi-experiment-20261006`, HEAD
  `989e880d69888e63940b31066a50e6d0f1068c0f`.
- Compiler source: `/private/tmp/elisa-compiler-q011-4c479-20261006`, HEAD
  `4c479ad1981403c9f77f04a9ee5918f74713533e`.
- Current reproducibility/control products are the previously provenance-
  validated immutable O0/O2 pairs in
  `/private/tmp/elisa-proof-q011-causal-20261006/build/elisa-proof-generations/`.
  `verify_product_pair.py resolve` resolved O2 generation
  `1b7e6197822d48c392914c9b13fd127e`; the prior causal audit records the
  independently resolved O0 generation `2b51c9b519834366a679dc916ebb4623`.
- Both current pairs bind proof source tree
  `8a39f00830a2ce3d5e5378de5fee2056a4e3d962ccd18acb6bdf825d317d56b1`, clean
  compiler source revision `3778d8fd7ec8679371199458dacb9ff414d73a0c`, target
  `arm64-apple-darwin27.0.0`, and the recorded runtime object. O0/O2 proof
  executable hashes remain `d38dc988…8762d22` and `458061ab…e1230e1`;
  replay executable hashes remain `b268f484…1c02` and `595f0db1…d78a`.
- The retained historical executable was copied read-only to
  `/private/tmp/q011-live-abi.pe4Q7Y/historical-proof` before debugger use.
  Its SHA-256 is `74f49810b8988d2e53f38d6298a0e29536299c579363209d464ad2a7b789658a`;
  its copied 51-byte input SHA-256 is
  `3cf171b77ae3bd4d847a3f6c6fd1bb10f40978b189e121e1a1951f086fd94ea2`.
  The historical manifest is **not** a reproducible source provenance record:
  it says `source_dirty: true` for both proof and compiler. Its hashes identify
  the retained binaries only.

The repo-local Elisa debugger has no built executable in its available
worktree, and its documented native postmortem support is not wired. LLDB was
used for this live-process native inspection; no claim is made that the Elisa
debugger diagnosed the fault.

## Bounded LLDB experiment

The historical binary was launched under LLDB with the exact minimized input.
The following instruction boundaries were observed in the failing call path:

1. Immediately before `bl _ctx_aos_store_record` at `0x10046b678`, `x24` was
   `0x16fdfa030`. Immediately after return at `0x10046b67c`, `x24` was still
   `0x16fdfa030`. Memory at that address began with a data pointer, count `1`,
   and capacity `8`, i.e. the descriptor-shaped value recorded in the original
   crash audit. Thus the runtime record lookup did not introduce this value in
   this run; it was already present before that runtime call.
2. Immediately before `bl proof_qualified_constant_rewrite` at
   `0x10046bed8`, `x24` was still `0x16fdfa030`. At callee entry
   (`0x10046a904`, return address `0x10046bedc`) it was unchanged; stepping out
   to `0x10046bedc` showed the same `x24`. The callee prologue/epilogue also
   saves and restores `x24`. This rules out this callee as the source of the
   observed register corruption in this execution.
3. Continuing reached the original failure at
   `str w23, [x19, x24, lsl #2]` (`0x10046b654`), with `x24` still the
   descriptor address and the same descriptor-shaped memory. The effective
   address therefore fails because the caller supplies a non-index value.

LLDB was initially run with unresolved address breakpoints before target
startup; those did not stop at the requested sites. The successful trace used
`process launch --stop-at-entry`, then installed the breakpoints after image
addresses were resolved. This detail is recorded to make the capture
reproducible and avoid treating the earlier unsuccessful breakpoint setup as
evidence.

## Known-product rerun

In the clean proof worktree, `python3 scripts/verify_product_pair.py resolve
--generation-root build/elisa-proof-generations` resolved the immutable O2
pair. The exact minimized input was then run directly against both exact
provenance-validated proof products:

| Product | Result | Obligations | Replayed certificates | Gaps |
| --- | --- | ---: | ---: | ---: |
| O0 `2b51c9b519834366a679dc916ebb4623` | proved | 1/1 | 1/1 | 0 |
| O2 `1b7e6197822d48c392914c9b13fd127e` | proved | 1/1 | 1/1 | 0 |

These are current no-crash controls, not a reproduction of the historical
fault. The independent replay binary is present in each resolved product
pair; this experiment made no proof-side semantic change requiring a new
consumer regression.

## Causal boundary and next experiment

The new observation weakens the runtime-call and nested-expression-callee
hypotheses, and strengthens the hypothesis that the enclosing body rewrite
already has an invalid append/index state before expression rewriting. It
still cannot attribute that state to source or compiler: the historical source
trees were dirty and unavailable, and the current clean products do not fail.

The next discriminating experiment should compile a minimized body-rewrite
probe with a known compiler product while preserving source shape, then compare
generated code for the append/index before and after the nested rewrite call.
If that compiler/source pair keeps the index initialized and both calls
preserve it, the evidence points back toward unrecoverable historical source
state; if the minimized caller emits the descriptor as its append index, the
compiler lowering is implicated. Until such a source-correlated differential
exists, Q0.11 remains unresolved and no implementation fix is justified.
