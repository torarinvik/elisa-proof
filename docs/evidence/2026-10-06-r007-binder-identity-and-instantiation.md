# R-007 binder identity and instantiation boundary audit

This focused audit starts from `docs/evidence/2026-10-05-r007-nested-binder-shadowing.md`.
It found no admitted false claim in the tested quantifier/replay paths, so the kernel semantics
remain deliberately conservative. The arena still uses source names rather than stable binder
IDs, and substitution beneath a differently named nested quantifier remains explicitly
unsupported; no alpha-equivalence or existential-introduction rule was added.

## Adversarial coverage added or rerun

- `examples/kernel_arena_runtime/quantifier_binder_identity.elisa` adds kernel-level controls:
  same-spelled nested finite binders independently replay; two alpha-equivalent one-element
  universals each independently replay, while structural equality refuses to identify them;
  a true outer/inner quantifier requiring substitution beneath a different binder is refused;
  and a universal's bound name cannot escape into a free outer goal.
- `examples/tactic_runtime.elisa` adds a positive bounded-universal instantiation plus assumption
  proof that passes independent tactic-certificate replay. Mutating the recorded trace's
  post-instantiation fact to `false` then makes certificate replay refuse. Existing tactic-runtime
  checks also exercise sibling fact-array mutation and reject attaching a child to its sibling's
  context.
- The existing JSON action attack
  `examples/tactic_script_source_bound_forged_instantiation.json` was rerun against
  `examples/source_bound_exists.elisa`; relabeling an existential source hypothesis as a
  universal instantiation remains rejected, with `certificate_replayed: false`.
- The portable package generated from `examples/quantifier.elisa` replayed in a fresh standalone
  `elisa-proof-replay` process: all 10 theorem records replayed, including bounded `forall` and
  `exists` records. `scripts/test_portable_replay.py` also passed (16 positive packages, structured
  package fuzz, and 512 raw-byte mutations; no crash or partial replay).

The trace-snapshot mutation is against the same state representation consumed by independent
tactic trace replay; this audit did not add a separate disk encoding/import format for tactic
transition snapshots. The JSON test covers the existing serialized action protocol, not a new
transport for internal snapshots.

## Exact validation identity

- Proof checkout base: `989e880d69888e63940b31066a50e6d0f1068c0f`; test changes are isolated on
  `codex/r007-binder-identity`.
- Stage1 revision: `72dff79aa6303fefde4ecafb2f4f45e82b381617`.
- Stage1 product: `/private/tmp/elisa-optional-enum-payload-import-fix/bin/elisac-stage1`,
  SHA-256 `0234f8b214e19149320d257b860f8031733b9a25aa9fc91d442b75e2355017e4`; provenance reports
  a clean source tree and the matching revision.
- Runtime object SHA-256:
  `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`.
- O2 proof/replay pair generation: `a1d7c631bc784147ac22a107684eba1d`; proof binary SHA-256
  `6a6212ea73dcbbe86aeeb2e10c185817d050e99afc507b9dc2e4bcc0498c9a27`; standalone replay binary
  SHA-256 `7453549d3eeb374a57bc327878281fdf921bc963cd98f44e22f8430357a4d111`.
- Both kernel arena and tactic runtime harnesses compiled at O0 with that exact Stage1 executable,
  linked to the matching runtime and profile hooks, and exited 0. The latest alpha-renaming positive
  control was recompiled and rerun after the snapshot refresh.
- Portable pair resolution and the portable replay mutation suite passed. `git diff --check`
  passed.

## Remaining work and unrun gates

Distinct, scope-stable binder IDs; alpha-equivalence; general capture-avoiding substitution;
existential introduction/eigenvariable side conditions; stale context IDs; and comprehensive
post-validation mutation coverage remain open. The nested-capture formula is true but returns
refusal because its instance would cross a distinct inner binder. The full `scripts/test.sh`, full
`scripts/dogfood.sh`, Stage0 parity for these new runtime cases, all tactic tree/import mutation
routes, and cross-request/concurrent context reuse were not run as part of this slice.

R-007 remains open. This evidence is a targeted regression result, not a binder-identity or
quantifier-soundness completion claim.
