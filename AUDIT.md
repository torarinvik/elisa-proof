# Full implementation audit — in progress

Passing the current suites is regression evidence, not completion of the full audit.
The objective covers all existing implementation code, scripts, proof fixtures, and their
assumptions about the compiler. No module below is yet certified as fully audited.

## Contained defect; full repair open: unsigned local substitution

Reproducer: `examples/rejected_unsigned_local.elisa`.

```
./build/elisa-proof examples/rejected_unsigned_local.elisa
```

Observed at revision `8f3dfbf`: exit 0, three proven obligations, three replayed certificates,
zero replay gaps. The proof is false: after `x: u8 = 255`, `x + 1 > x` fails under wrapping
unsigned arithmetic. The current preflight rejects functions containing explicit unsigned local
declarations before publishing logical obligations or summaries. The fixture is now in dogfood,
along with rebinding, compound assignment, branch, shadowing, loop, and bounded-safe cases.
The tests require zero proven obligations and zero certificates, not just a nonzero exit status.

This is conservative containment, not completed type preservation: even bounded-safe unsigned
locals are temporarily unsupported. The core `add_node` helper is affected; six obligations in
the remaining core and nineteen in its call-site fixture still prove and independently replay.
Tests explicitly require that the only finding in those two fixtures belongs to `add_node`.
The standalone replay audit also loses verification of `proof_kernel_replay_difference_query`,
which has unsigned locals. Its test now requires the explicit type-erasure finding while keeping
the other nine previously required verified helpers and all certificate replay checks.

The declaration path in `proof_check_returns` substitutes the initializer into its value table.
It records the unsigned type marker against the original local name, but subsequent expression
substitution replaces that name with an untyped `IntLit`. Both the producer and replay kernel
then reason about signed mathematical `255 + 1` instead of the source's u8 operation.

Required repair must preserve arithmetic type through substitution, not only attach more facts
to a name that disappears. Check declarations, rebindings, compound assignments, shadowing,
branch joins, loop state, and instantiated function summaries. Regression requirements include
rejection of wrapping operations, acceptance of bounded safe operations, and direct kernel replay
that cannot admit a certificate after the arithmetic type has been removed or changed.

## Coverage still required

### Repaired: unsigned assumptions entering signed decision procedures

`examples/rejected_unsigned_fact_explosion.elisa` originally certified `x == 0` from
`x: u8 == 255`, `y: u8 == 0`, and `y == x + 1`. These premises describe a real wrapping
execution, but the signed arithmetic tiers treated them as excluding that execution.
The producer and independent replay now check arithmetic safety of premises, not just goals,
before using signed decision procedures. Direct assumption reuse remains admissible.
Subtraction safety uses only plain scalar order facts, so an unchecked modular arithmetic
premise cannot establish its own non-wrapping interpretation.

Regressions cover false-source-goal rejection, bounded-safe arithmetic premises, direct reuse
of a wrapping premise, and direct hostile arena replay without the producer. This repair does
not add modular arithmetic or resolve the separately tracked typed-binding work.

Validation used an isolated copy with both the stage1 compiler and included front end from the
installed snapshot at revision `3c8924aa`. The shared compiler worktree was concurrently edited;
normal builds during this fix encountered parser mutability errors there. Those unrelated edits
were not changed. Snapshot validation does not establish that the moving shared-front-end build
is currently working.

| Code | Required audit coverage |
| --- | --- |
| `src/main.elisa` | Source import, diagnostics, every CLI admission gate, serialization, fingerprints, target repair |
| `src/proof/import.elisa` | Compiler-compatible include expansion, failures, cycles, path identity |
| `src/proof/model.elisa` | Report invariants, source provenance, certificate and side-table ownership |
| `src/proof/check.elisa` | Typed symbolic execution, state changes, contracts, calls, frames, loops, termination |
| `src/proof/expr.elisa` | Substitution, binding and capture, equality, numeric semantics, unsupported forms |
| `src/proof/linear.elisa` | Arithmetic soundness, bounds, overflow, case splits, quantified reasoning |
| `src/proof/kernel_core.elisa` | Primitive bounds, arithmetic, arena operations and formalized contracts |
| `src/proof/kernel.elisa` | Meaning-preserving lowering and complete type information |
| `src/proof/kernel_replay.elisa` | All public admission APIs and inference rules, malformed arenas, numeric and resource semantics |
| `src/proof/replay.elisa` | Source/arena agreement, provenance, summary dependencies, legacy replay paths |
| `src/proof/resources.elisa` | Ownership, aliasing, region lifetime, frames, indexing and state joins |
| `src/proof/tactics.elisa` | Every transition, substitutions, branches and source binding |
| `src/proof/tactic_json.elisa` | Exact parsing, schema validation, tree replay and source binding |
| `scripts/build.sh`, `scripts/test.sh`, `scripts/dogfood.sh` | Compiler/runtime selection, exit-status handling, actual test coverage and reproducibility |
| Existing examples and design documentation | Expected verdicts, adversarial coverage, supported-fragment claims and trust assumptions |

Recent commits provide targeted evidence for quantifier kind preservation, exact source tactic
binding, rejection of lossy JSON integers, floating-point exclusions, and unsigned alias and
refinement widths. They do not establish type preservation through every symbolic transformation.

Completion requires coverage of the full table and resolution of every confirmed open defect.
