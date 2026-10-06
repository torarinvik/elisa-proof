# Q0.11 qualified-constant crash: causal-source audit — 2026-10-06

## Finding

The exact minimized input still reproduces the historical fault on the retained historical
executable, but it does not fault on the current pinned Stage1 proof products at either O0 or O2.
The historical trace confirms an invalid array-index register in generated code; it does not
identify how that register acquired its value. The historical executable's dirty proof/compiler
source state cannot be reconstructed. Therefore the causal source/compiler defect remains
unresolved, and no implementation change is justified by the available evidence.

## Exact inputs and products

The minimized input is 51 bytes, SHA-256
`3cf171b77ae3bd4d847a3f6c6fd1bb10f40978b189e121e1a1951f086fd94ea2`, identical in the proof
checkout as `examples/qualified_constant_return_crash_repro.elisa` and the retained
`/private/tmp/p00-qualified-constant-min-20261005/short_no_final_newline.elisa`.

The isolated proof worktree is `/private/tmp/elisa-proof-q011-causal-20261006`, clean at
`1f9f8ab9d5ab122d17f4490ed70ce2a706a0b486`. Its source-tree SHA-256 is
`8a39f00830a2ce3d5e5378de5fee2056a4e3d962ccd18acb6bdf825d317d56b1`.

Both strict products used Stage1/compiler/frontend revision
`3778d8fd7ec8679371199458dacb9ff414d73a0c`; the source checkout was clean and the provenance
check reported `stage1 provenance: current`. Stage1 executable SHA-256 is
`0039ed6e37cf12f327b49916a59ac6fa139d4e1a5b4dc105b1b8c73ba1e38999`; runtime-object SHA-256 is
`b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`. Target:
`arm64-apple-darwin27.0.0`.

| Optimization | Pair generation | Proof executable SHA-256 | Replay executable SHA-256 |
| --- | --- | --- | --- |
| O0 | `2b51c9b519834366a679dc916ebb4623` | `d38dc988ab1f23b43a7e46edbaf38f6518755dfea0569cd628b23255e8762d22` | `b268f484573753d18473c8fa6025ee5827f62d1b2b324da2d56e93b4f5212c02` |
| O2 | `1b7e6197822d48c392914c9b13fd127e` | `458061aba80a62f313a5730d88c3223b6d130386aeaa90c5e5b7624dee1230e1` | `595f0db1ef248bf57298667a9947450e369685219707ae51de74e308cd63d78a` |

Both proof manifests bind proof HEAD/source digest, compiler product/source revision, runtime, flags,
and target; `scripts/verify_product_pair.py resolve --generation-root build/elisa-proof-generations`
resolved each immutable pair. The manifests say `stage1_revision: null` because this pinned
compiler checkout is not an installed `SNAPSHOT` tree; the compiler's own clean source revision,
provenance guard, and executable hash above provide the available exact identity.

## Reproduction and controls

For each pair, the exact minimized file and six retained neighboring controls were run with
`--json`: module constant only, plain return, bare return, qualified return, qualified contract,
and qualified assignment. Every invocation exited 0, emitted JSON with no stderr, and had zero
replay gaps. The minimized case reported one obligation, one proof, and one replayed certificate.
The exact input was also run under LLDB against both current proof executables; both processes
exited normally. This demonstrates current behavior for these exact products and inputs only.

On O0, `ELISA_PROOF_BIN=<O0 proof product> python3 scripts/test_qualified_constants.py` executes
the minimized crash regression successfully, then exits at the existing
`qualified_constants_body.elisa` expectation. Its actual report is
`proved_with_replay_gaps`, 4 obligations, 3 proven/replayed certificates, and 1 gap. O2 has the
same direct body result. This independent replay/status gap is not a crash and must not be used to
weaken the focused crash regression or to claim that the complete qualified-constant suite passed.

The retained historical executable
`build/audit-20261005/elisa-proof-warm` was re-hashed as
`74f49810b8988d2e53f38d6298a0e29536299c579363209d464ad2a7b789658a`. LLDB rerunning the exact
51-byte file stopped with `EXC_BAD_ACCESS` at
`0x10046b654`, instruction `str w23, [x19, x24, lsl #2]`, inside the generated function previously
identified as `proof_qualified_body_rewrite +384`. At the stop, `x19` was
`0x000000010504b0a0` (array base) and `x24` was `0x000000016fdfa030` (stack-address-shaped index);
`x26` was 0 and `x27` was 1. This reconfirms the bad-index symptom for that retained executable.
It does not name the source-level value intended for `x24` or prove where the bad register state
originated.

## Source/history inspection and causal boundary

The current implementation is `src/proof/check/qualified_constants.elisa`, especially
`proof_qualified_body_rewrite` and its caller `proof_qualified_constants_collect`. The rewrite
allocates a result array in region `@r`, iterates the source body, pushes one rewritten statement
per source statement, then the caller clears and repopulates the original body. The exact minimal
input reaches the `Ast::Stmt.Return` arm.

History shows `e110a2a1` changed body replacement to build a rewritten array and copy statements
element-wise, while `e22f33d3` threaded a borrowed `storage_body` through recursive rewrite calls
and passed `function_body` as both `body` and `storage_body`. Those edits correlate with the area
where the historical fault occurs. They do not establish a source defect: the old executable was
built from dirty, unrecoverable proof/compiler trees, and current clean O0/O2 products pass. A
borrow/region interaction, incorrect compiler lowering of a captured loop variable or dynamic-array
push, and a runtime/ABI defect remain hypotheses—not findings. No historical compiler differential
was possible, and no code change was made.

The sibling `elisa-debugger` support matrix says native postmortem/core inspection is not wired.
LLDB was therefore used on the live historical fault and current no-fault controls. No claim is made
that the custom debugger diagnosed this native issue.

## Commands

Fresh strict builds, run from the isolated worktree, used the same source/compiler identity for
each optimization level:

```sh
ELISA_COMPILER_SRC=/private/tmp/elisa-optional-enum-payload-import-fix \
ELISA_COMPILER_REV=3778d8fd7ec8679371199458dacb9ff414d73a0c \
ELISA_COMPILER_BIN=/private/tmp/elisa-optional-enum-payload-import-fix/scripts/elisac_stage1.sh \
ELISA_STAGE1_BIN=/private/tmp/elisa-optional-enum-payload-import-fix/bin/elisac-stage1 \
ELISA_STAGE1_ROOT=/private/tmp/elisa-optional-enum-payload-import-fix \
ELISA_RUNTIME_OBJ=/private/tmp/elisa-optional-enum-payload-import-fix/build/runtime/elisacore_runtime.o \
ELISA_PROOF_PRODUCTS=all ELISA_PROOF_BUILD_JOBS=2 ELISA_PROOF_OBJECT_CACHE=0 \
ELISA_OPT_LEVEL=O0 bash scripts/build.sh

# Repeat with ELISA_OPT_LEVEL=O2.
python3 scripts/verify_product_pair.py resolve --generation-root build/elisa-proof-generations
<immutable-generation>/elisa-proof --json \
  /private/tmp/p00-qualified-constant-min-20261005/short_no_final_newline.elisa
lldb --batch -o run -- <immutable-generation>/elisa-proof --json \
  /private/tmp/p00-qualified-constant-min-20261005/short_no_final_newline.elisa
```

Historical fault capture:

```sh
shasum -a 256 build/audit-20261005/elisa-proof-warm
lldb --batch -o run -k 'register read x19 x21 x24 x26 x27 pc' \
  -k 'disassemble -f -c 6' -- build/audit-20261005/elisa-proof-warm --json \
  /private/tmp/p00-qualified-constant-min-20261005/short_no_final_newline.elisa
```

**Next causal step:** recover the exact historical compiler/proof source and build recipe, or
produce a source-level minimized case that fails on a pinned compiler revision. Then bisect the
source change and inspect generated code at the first failing revision before changing either
proof code or compiler lowering.
