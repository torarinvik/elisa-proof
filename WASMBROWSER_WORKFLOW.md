# WasmBrowser proof-assistant development

This is the `wasmbrowser-proof` worktree of `elisa-proof`, on
`codex/wasmbrowser-proof`. It starts at commit `162bd5d` with the primary
checkout's current source changes and non-ignored source fixtures carried over.
Those changes include ongoing work from other contributors as well as the
WasmBrowser arithmetic/replay and tactic-branch changes. They remain uncommitted;
do not attribute the entire starting diff to a new WasmBrowser feature.

The authoritative work queue is `../WasmBrowser/IMPLEMENTATION_PLAN.md`, with
product proofs and evidence in `../WasmBrowser/proofs/`. Write proofs alongside
each implementation. When production obligations reveal missing prover support,
implement it here, including independent replay support and nearby false-claim
controls, then rerun the original obligation and applicable product tests.
Keep the primary `../elisa-proof` checkout available for its other ongoing work.

The earlier blanket request to pull gains from other proof worktrees was
retracted. Do not import another worktree just because it is newer, and never
modify its checkout. If a specific external change becomes necessary, review it
as an independent candidate and validate its source identity, local build,
positive/negative controls and dependent product proof before accepting it.
Keep historical proof evidence unchanged.

Synchronization on 2026-09-28: primary `elisa-proof` at `162bd5d` supplied the
Bash 3.2-compatible optional contract-flag fix in `scripts/build.sh`.
`elisa-engine-proof` had the same HEAD and no unique dirty changes at inspection.
The historical baseline HEADs `06d1ee11` and `bf79754` are ancestors of the
current HEAD. The primary's safe-comparison replay refactor was imported from
its first coherent 112-line section, omitting duplicated in-flight follow-up
definitions. Local integration uses `extend` rather than redeclaring the module
and retains the integer-operator predicate needed by another replay caller.
The imported evaluator still refuses unsupported unary/shift operations and
compound results outside the nonnegative i8 range. Validation results must be
recorded before treating this combined source as accepted evidence.

Combined safe-comparison source SHA-256:
`05bf4a977acd3cf3966e3b7214f08abb706130f6df7a3e234fef8ad912e1e98f`.
Build-script SHA-256:
`f81d32b9e3be53c8d9a84b5200c8995d43d87282994eef61369057497fb876b2`.
`scripts/test_safe_constant_replay.py` preserves the matrix's safe arithmetic
replay and three unsigned-machine refusal controls as a focused sync gate.

Validation on 2026-09-28: the private-clean-bootstrap runtime-check build passed.
Source length, constant replay, guarded subtraction, nested branch controls and
the new unsigned-disjunction regression pass. The dependent production proof
exposed a disjunction-ordering limitation, repaired in both
`linear/model_and_congruence.elisa` and `kernel_replay/resource_model.elisa`.
Alternative introduction now precedes numerical guards; each alternative
recursively receives those guards, so an unsafe comparison cannot certify a
false disjunction. The browser evidence at
`../WasmBrowser/proofs/WB-PROOF-001/evidence/run-s8wyk5yj/manifest.json` records
the combined snapshot and 21/21 independently replayed production obligations.
This is focused validation, not a claim that the full prover matrix or strict
implementation-contract discharge has passed.

## Scalar-reference update support — 2026-09-28

The checker now models a tightly bounded case needed by the accounting proofs:
reading or mutating literal `reference[0]` when the formal is a typed primitive
scalar reference. Entry-state `old(reference[0])` is kept distinct from the
current pointee value. A write is admitted only for a direct mutable-reference
formal, plain assignment, and a pure supported RHS; the reference handle itself
is not rewritten. The resource pass treats that exact typed element read as a
copied scalar, not as a capability passed to a generated operator call. Other
offsets, shadowing locals, aggregate references, calls in write expressions,
and broader writes remain conservative. The nonzero-offset control is refused
during proposition formation, before it can become a proof goal.

The new `examples/scalar_reference_index.elisa` regression verifies the
zero-offset read, a guarded `value[0] <- value[0] + 1` update using
`old(value[0])`, and a module-qualified `u8` status disjunction around that
old-value postcondition; all 18 accepted certificates replay with no gaps, and
the index-one claim remains unproved. This confirms the minimal disjunctive
reference contract is admitted;
the larger transaction's remaining formation failure is specific to that
imported context. Five focused proof regressions pass. The
fresh production run is retained at
`../WasmBrowser/proofs/WB-PROOF-001/evidence/run-gd266jnx/manifest.json`:
21/21 accounting obligations replay, deterministically, with the rejection
control intact.

The larger `transaction_probe.elisa` remains incomplete: 94/103 obligations
are proven, nine remain unproven (resource-limit operator/summary support and
vector bounds), and one caller-side resource-safety certificate has a replay
gap. It is not accepted evidence for paired reservation rollback. A separate
call-through scalar-reference regression is deliberately refused with
`call-old-opaque` until call-entry reference snapshots can be independently
replayed; that refusal is tested. The full `scripts/test.sh` run passed
source-length, harness, full-source audit, overlap diagnostics and focused
proof regressions, but was stopped at its first long standalone compiler probe;
the full matrix is not claimed passed. The helper was split into
`operator_witnesses.elisa` to keep `declaration_checks.elisa` at its 600-line
limit.

Use the prover README's provenance checks and compiler snapshot workflow. The
first local development build uses a private clean Stage0 copy whose embedded
revision matches this worktree's `ELISA_STAGE0_REV`. The currently verified
copy is `build/elisac-stage0-a891`. Do not substitute
`../WasmBrowser/proofs/WB-PROOF-001/STAGE0_REV`: it pins a different compiler
build for product evidence. Explicit runtime-check compilation is only for
development; strict compilation remains the default, and report admission plus
certificate replay are required in either mode.

```sh
DEVELOPER_DIR=/Library/Developer/CommandLineTools \
ELISA_PROOF_COMPILE_MODE=runtime-checks \
ELISA_COMPILER_BIN="$PWD/build/elisac-stage0-a891" \
ELISA_STAGE0_REV_FILE="$PWD/ELISA_STAGE0_REV" \
bash scripts/build.sh
```

This command is for macOS from this worktree; other platforms need their own
compiler and target evidence. Build artifacts are local and must be recreated
if removed. Preserve compiler/prover/source identities in every accepted proof
run. Historical evidence must continue to name the checkout and binary actually
used rather than being rewritten to point at this worktree.
