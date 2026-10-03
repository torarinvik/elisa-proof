# mocap-cleaner refusal census

Source: `torarinvik/mocap-cleaner` `main` at `ff1699d`, read-only. Prover: this branch
(`agent/mocap-unsupported`, based on `mocap-cleaner-proofs` `7571dfa`).

**How this was produced.** The prover could not be built in the session that wrote this, so
every row is a static reading of the mocap source against the prover's refusal gates, not a
captured `--json` report. Each row says how sure it is:

- **certain**: the gate fires on a syntactic shape that is present, with no state dependence.
- **likely**: the shape is present and the gate normally fires on it, but whether it does
  depends on facts the checker has at that point.
- **open**: no gate could be pinned down statically. Run `build/elisa-proof --json` and read the
  `findings` array to settle it.

Before relying on a row, re-run `scripts/proof_status.py` (mocap) with this prover build.

## 1. Where `unsupported` / `unknown` come from

`verification_state` (`src/app/report_output.elisa:14`, `proof_report_verification_state`) is
derived only from the findings list:

| State | Rule |
| --- | --- |
| `disproved` | any finding whose status is `disproved` |
| `unsupported` | otherwise, any finding whose kind maps to `unsupported` |
| `unknown` | otherwise, any `unknown` finding, unresolved front-end checks (semantic errors or a failed import), or an unreplayed certificate |

The kind→status table is `proof_finding_status` in `src/proof/model/report_recording.elisa:62`.
Any kind not listed there is `unknown`: the `*-unproven` goal failures, `function-summary-unverified`,
`index-bounds-opaque`, `loop-invariant-missing`, `region-call-opaque`, `borrow-call-alias`,
`resource-write-readonly` and so on. Findings from **included** files count against the file
being checked, so one refusal in a shared include marks every file that includes it.

The `unsupported` kinds that can apply to mocap code, and where each is raised:

| Kind | Raised at | Trigger |
| --- | --- | --- |
| `contract-expression-unsupported` (float) | `src/proof/check/declaration_checks.elisa:205` | a parameter whose type may contain `f32`/`f64` (directly or through a struct, array or alias), on **any** function, contracts or not |
| `contract-expression-unsupported` (alias) | `declaration_checks.elisa:188,196`; `returns/declarations.elisa:101`; `refinement_contracts.elisa:46,55,63` | a numeric type alias that cannot be resolved uniquely |
| `expression-unsupported` (runtime) | `src/proof/check/statement_checks.elisa:530` (before this branch) | a statement whose expression fails `proof_expr_supported` (`src/proof/expr/pattern_support.elisa:274`): an if-expression with a non-conversion call, a lambda, a `catch`/get-else expression in nested position, `new[r]`, a captured value block, etc. |
| `expression-unsupported` (operator) | `statement_checks.elisa:522`; `call_and_branch_state.elisa:100`; `returns/matches.elisa:24,80`; `statement_checks.elisa:215,258,266,278` | a source-overloaded operator, or an unmodeled match scrutinee, guard or arm |
| `statement-unsupported` | `returns/matches.elisa:202,213`; `resources/statement_checker.elisa:557` | an invalid or unrecognized statement form |
| `control-flow-unsupported` | `returns/matches.elisa:183,192`; `statement_checks.elisa:469` | a labelled `break`/`continue` outside a modeled loop, or nesting past `PROOF_CONTROL_FLOW_DEPTH_LIMIT` |
| `captured-block-unsupported` | `statement_checks.elisa:424` | a captured block (`|a, b|:`) that is not exactly one loop |
| `pattern-unsupported` / `catch-arm-unsupported` | `statement_checks.elisa:173,178,234,249`; `returns/matches.elisa:55` | catch or value-match pattern bindings, or catch arms that are not exactly one expression |
| `borrow-call-opaque` | `src/proof/resources/expression_checker.elisa:91` (method receiver) and `:126` (no callee summary) | a method call on a place that is not a modeled collection builtin (`push`, `extend`, `clear`, `resize`, `pop`, `truncate`) or a width conversion; a resource-carrying argument with no converged callee summary |
| `borrow-call-summary-unsupported`, `borrow-source-opaque`, `borrow-escape` | `src/proof/resources/*` | resource and borrow transitions without an exact summary |
| `region-alias-unsupported`, `region-expression-unsupported`, `region-store-escape`, `region-*` | `src/proof/resources/*` | `sview`/region values without a directly tracked live backing region |
| `contract-call-unsupported` | `declaration_checks.elisa:226,236`; `contracts_and_frames.elisa:262` | a contract calls something other than a verified, total, pure function (mocap G27) |
| `effect-call-opaque` / `effect-row-abstract` | `declaration_checks.elisa:424,414` | only for a function that **declares** `can[...]`: a callee with no effect row, or an effect variable in the row |
| `import-error` | `src/app/cli.elisa:264` | an `include` that cannot be read |
| `control-flow-analysis-budget`, `resource-analysis-budget`, `frame-analysis-budget`, `kernel-arena-budget`, `semantic-analysis-depth`, `resource-expression-depth` | budget sites in `check/` and `resources/` | bounded analysis ran out |
| `recursive-summary-unsupported`, `lemma-*`, `proof-*`, `loop-*`, `frame-*`, `parallel-*` | `check/` | constructs mocap does not use in the listed files |

## 2. Shared causes

Three shapes account for most of the 21 files. Everything else is per-file.

**A. Floating-point parameters (certain).** `declaration_checks.elisa:205` refuses any function
with a float-typed parameter, since erasing a float to an untyped term would make `x == x` a theorem
under NaN. mocap reaches it in two ways:

- its own code: `Rig`, `RigOps`, `RigPhysics`, `Limb`, `GlbTracks::to_fixed(value: f32)`;
- the engine includes (`../../../elisa-engine-mocap/src/assets/glb_document.elisa`,
  `animation/motion_quat.elisa`, `animation/ik.elisa`, and `math/geometry.elisa` through them),
  for example `GlbDocument::float_bits(value: f32)` and `vec3_member(..., fallback: Geometry::Vec3)`.

Every file whose include closure reaches `glb_document.elisa` or `motion_quat.elisa` is therefore
`unsupported` whatever its own code does: `rig_map`, `glb_tracks`, `rig`, `corrections`,
`limb`, `rig_stack`, `presets`, `ops_file`, `rig_physics`, `main`.

This is a deliberate soundness boundary (mocap G9, "design choice"), **not** fixed here. Admitting
float parameters needs an IEEE model in the kernel, or a proof that no fact or goal mentions the
float term. Neither is a small change.

**B. Calls inside an if-expression (certain; fixed on this branch for whole-statement values).**
`proof_expr_supported` admits `A if c else B` only when every call in `c`, `A` and `B` is an
integer conversion (`pattern_support.elisa`, `Ast::Expr.If` arm). Any other call makes the statement
fail `proof_statement_expressions_supported`, which raises `expression-unsupported` at
`statement_checks.elisa:530`. Occurrences in the listed files:

| File | Lines | Covered by the fix? |
| --- | --- | --- |
| `src/tools/track.elisa` | 34, 97, 98 | yes (declarations) |
| `src/ops/stack.elisa` | 65, 70, 74 | yes (declarations, rebind) |
| `src/ops/stack.elisa` | 76 | **no**: nested in a `push(...)` argument |
| `src/ops/rig_stack.elisa` | 200, 202, 204, 566, 589, 591, 603, 606 | yes (declarations) |
| `src/ops/rig_stack.elisa` | 206, 387, 419 | **no**: nested in a call argument |
| `src/physics/rig_physics.elisa` | 290, 398, 460 | yes |
| `src/physics/rig_physics.elisa` | 150, 151, 173, 388, 423 | **no**: nested in a call argument |
| `src/io/rig.elisa` | 139, 267 | yes (the call is in the condition) |
| `src/tools/limb.elisa` | 68 | yes |
| `src/cli/main.elisa` | 319 | yes |

`presets`, `ops_file` and `main` also inherit these through `stack`/`rig_stack`.

**C. Impure I/O (likely).** `console`, `folder` and `report` call `extern` C functions
(`putchar`, directory and file calls) and loop over `cstr`/`sview` data:

- `for c in s` over an `sview` parameter, and `while s[i] != 0` over a `cstr`, have no tracked
  backing region or extent. That gives `region-alias-unsupported` (unsupported) and
  `index-bounds-opaque` (unknown).
- `_ = c_putchar(...)`: an extern has no row in the function table, so no executable summary is
  applied. Facts are cleared and nothing is refused outright; it only matters for files that
  declare `can[...]` on a calling function (`effect-call-opaque`).

`main` inherits all three through its includes.

## 3. Per file

"Own" means a construct in the file itself; "via" means it comes from an include.

| File | Status | Triggering construct(s) | Prover location | Confidence |
| --- | --- | --- | --- | --- |
| `src/cli/main.elisa` | unsupported | via A (glb_tracks, rig_physics, ops_file); via B (stack, rig_stack, rig_physics); via C (console, report, folder); own: `catch` value forms (3), if-expression with a call (319), get-else recovery (10) | `declaration_checks.elisa:205`; `statement_checks.elisa:530`; `statement_checks.elisa:173,178` | A, B certain; catch likely |
| `src/io/console.elisa` | unsupported | own: `for c in s` over an `sview` parameter; `while s[i] != 0` over a `cstr`; extern `c_putchar` | resources region checks (`region-alias-unsupported`); `index_checks.elisa:234` | likely |
| `src/io/folder.elisa` | unsupported | own: 8 extern declarations with `can[...]` rows, `cstr`/`sview` buffers, `while` loops over C strings | resources region checks; `index_checks.elisa:234`; `declaration_checks.elisa:424` if a caller declares `can` | likely |
| `src/io/glb_tracks.elisa` | unsupported | own A: `to_fixed(value: f32)`; via A: `glb_document.elisa`; lambdas/captured value blocks (5) | `declaration_checks.elisa:205`; `pattern_support.elisa` `Lambda` → `statement_checks.elisa:530` | A certain |
| `src/io/ops_file.elisa` | unsupported | via A and B (rig_stack); via C (report); own: extern file I/O | as above | A certain |
| `src/io/report.elisa` | unsupported | own C: 6 externs, `push_text(out, s: sview)` iterating an `sview`; get-else (5) | resources region checks; `runtime_support_and_calls.elisa:339` | likely |
| `src/io/rig.elisa` | unsupported | own A: `f64`/`MotionQuat` parameters throughout; via A: motion_quat, glb_document; own B: 139, 267; `catch` (1) | `declaration_checks.elisa:205`; `statement_checks.elisa:530` | certain |
| `src/io/rig_map.elisa` | unsupported | via A only (`glb_document.elisa`, through `GlbDocument` parameters); no float of its own | `declaration_checks.elisa:205` | certain |
| `src/ops/corrections.elisa` | unsupported | via A (glb_tracks, glb_document); own: `catch` forms (10), float locals and struct fields, a lambda | `declaration_checks.elisa:205`; `statement_checks.elisa:173,178,530` | A certain |
| `src/ops/presets.elisa` | unsupported | via A and B (rig_stack, stack); own code is enum `match` plus `push` (supported) | as above | certain via includes |
| `src/ops/rig_stack.elisa` | unsupported | own A (MotionQuat/f64 parameters); via A (limb, motion_quat, ik); own B (eleven sites, see §2) | `declaration_checks.elisa:205`; `statement_checks.elisa:530` | certain |
| `src/ops/stack.elisa` | unsupported | own B (65, 70, 74 fixed; 76 not); `cache: mutable Cache&` field and index writes (`cache.results[at] <- ...`); via `track.elisa` | `statement_checks.elisa:530`; possibly `borrow-source-opaque` in `src/proof/resources/` | B certain; borrow likely |
| `src/physics/rig_physics.elisa` | unsupported | own A (f64 / `MotionQuat::V` parameters, `.sqrt()`); via A; own B (eight sites) | `declaration_checks.elisa:205`; `statement_checks.elisa:530` | certain |
| `src/tools/limb.elisa` | unsupported | own A; via A (ik, motion_quat, rig); own B (68); `catch` (3) | `declaration_checks.elisa:205`; `statement_checks.elisa:530` | certain |
| `src/tools/track.elisa` | unsupported | own B: 34, 97, 98, all fixed. Remaining candidates: indexed writes through a mutable local (`window[j] <- ...`, `out[i] <- ...`); `current <- next` whole-container rebind inside a captured `while` | `statement_checks.elisa:530` (B); resource and borrow checks in `src/proof/resources/` | B certain; the rest open |
| `src/core/key_weight.elisa` | unknown | no unsupported construct. Most likely an unproven goal in `ramp`: the wrap guard on `part * FULL` needs `part <= whole <= 2 * MAX_FRAMES` through a module constant, and `v: i64 = part * FULL / whole` is a division local (mocap G25). Could also be `requires frame >= -MAX_FRAMES` (a negated constant, mocap G19/G21 family) | goal failures (`*-unproven`, status unknown) via `report_recording.elisa:67` | open |
| `proof/key_weight_laws.elisa` | unknown | inherits `key_weight.elisa`'s open goal through `include`; its own calls only need preconditions that the laws state directly | as above | likely (inherited) |
| `src/io/report_diff.elisa` | n/a | **not in mocap `main` at ff1699d** (neither is it on any branch) | — | — |
| `src/io/workers.elisa` | n/a | **not in mocap `main` at ff1699d** | — | — |
| `src/ops/retime_apply.elisa` | n/a | **not in mocap `main` at ff1699d** | — | — |
| `src/ops/rig_cache.elisa` | n/a | **not in mocap `main` at ff1699d** | — | — |

The four missing files are probably newer local work that was never pushed. Re-run the census on
them once they are pushed.

## 4. What this branch changes

Construct B is fixed for whole-statement values: `x: T = A if c else B`, `t <- A if c else B`
(where `t` is a bare name) and `return A if c else B`, which includes a tail expression because
the parser lowers it to `return`. Such a statement is rewritten to the control flow it denotes:

    S[A if c else B]; rest   ==>   if c: S[A]; rest   else: S[B]; rest

Code: `proof_split_conditional_value` in `src/proof/check/returns/contracts.elisa`, called from
`proof_check_returns` in `src/proof/check/statement_checks.elisa`.

Fixtures:

- `examples/conditional_call_arms.elisa` must prove.
- `examples/rejected_conditional_call_arms.elisa` must fail with `call-requires-unproven`
  (`wrong_guard`), `ensure-unproven` (`skipped_arm`) and `expression-unsupported`
  (`nested_arm`, the uncovered nested form).

`examples/rejected_conditional_conversions.elisa` `counted` is a tail `return` with a
state-writing call in one arm. It is now checked as an `if` and no longer produces
`expression-unsupported`. Its expectation was updated in `scripts/test.sh` and `scripts/dogfood.sh`.

Fixing B alone does not flip any of the 21 files to `proved`. Most also hit A, and `track` and
`stack` have the open items listed in §3. What it does remove is the most frequent refusal that
has a sound fix.
