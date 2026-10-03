# mocap-cleaner refusal census

Source: `torarinvik/mocap-cleaner` `main` at `ff1699d`, read-only. Prover: this branch
(`agent/mocap-unsupported`, based on `mocap-cleaner-proofs` `7571dfa`).

**How this was produced.** Every number below comes from `build/elisa-proof --json` runs on
2026-10-03. Two builds were compared:

- the base commit `7571dfa`;
- this branch.

Both were built with the stage1 compiler at the pinned `ELISA_COMPILER_REV` `d8b5d30`, seeded from
the pinned stage0 `0b21b7b`, on Linux with LLVM 20. The `../../../elisa-engine-mocap` includes
resolved to an `elisa-engine` checkout.

An earlier, static-only version of this census guessed several causes. Where the reports
disagreed with it, the reports win. The corrections are listed in §3.

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

**B. Calls inside an if-expression (certain; fixed on this branch).**
`proof_expr_supported` admits `A if c else B` only when every call in `c`, `A` and `B` is an
integer conversion (`pattern_support.elisa`, `Ast::Expr.If` arm). Any other call makes the statement
fail `proof_statement_expressions_supported`, which raises `expression-unsupported` at
`statement_checks.elisa:530`. Sites in the listed files whose if-expression itself contains a call:

| File | Lines | Form | Covered by the fix? |
| --- | --- | --- | --- |
| `src/tools/track.elisa` | 34, 97, 98 | declaration | yes |
| `src/ops/stack.elisa` | 65, 70, 74 | declaration, rebind | yes |
| `src/ops/stack.elisa` | 76 | nested in `out.push(...)`, call-free condition | yes (nested split) |
| `src/ops/rig_stack.elisa` | 200, 202, 204, 566, 589, 591, 603, 606 | declaration | yes |
| `src/physics/rig_physics.elisa` | 290, 398, 460 | declaration, return | yes |
| `src/physics/rig_physics.elisa` | 423 | nested in `out.push(...)`, call-free condition | yes (nested split) |
| `src/io/rig.elisa` | 139, 267 | declaration, call in the condition | yes |
| `src/tools/limb.elisa` | 68 | declaration | yes |
| `src/cli/main.elisa` | 319 | declaration, call in the condition | yes |

The first version of this census also listed `rig_stack` 206/387/419 and `rig_physics`
150/151/173/388. Those if-expressions hold no call (`Roles::LEFT_FOOT if side == 0 else
Roles::RIGHT_FOOT` is constants; the call wraps the if-expression), so they were never refused.

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

## 3. Per file (measured)

"In the file itself" means findings whose source position is in that file. "Via includes"
means findings from functions in included files, which still count against the file.

| File | Base `7571dfa` | This branch | Proven (base → now) | Unsupported findings in the file itself (top kinds) | Unsupported via includes |
| --- | --- | --- | --- | --- | --- |
| `src/cli/main.elisa` | unsupported | **unsupported** | 1548/2426 → 1566/2449 | `function-summary-unverified` 76, `contract-proposition-type` 50, `borrow-call-opaque` 31 | `contract-expression-unsupported` 160, `contract-proposition-type` 72 |
| `src/io/console.elisa` | unsupported | **unsupported** | 4/12 → 4/12 | `contract-proposition-type` 1, `borrow-call-opaque` 1, `function-summary-unverified` 1 | none |
| `src/io/folder.elisa` | unsupported | **unsupported** | 19/27 → 19/27 | `contract-proposition-type` 7 | none |
| `src/io/glb_tracks.elisa` | unsupported | **unsupported** | 821/1181 → 839/1204 | `contract-expression-unsupported` 5, `contract-proposition-type` 2, `control-flow-analysis-budget` 1 | `contract-expression-unsupported` 84, `function-summary-unverified` 37 |
| `src/io/ops_file.elisa` | unsupported | **unsupported** | 1112/1623 → 1130/1647 | `borrow-call-opaque` 7, `function-summary-unverified` 5, `borrow-call-summary-unsupported` 3 | `contract-expression-unsupported` 136, `contract-proposition-type` 56 |
| `src/io/report.elisa` | unsupported | **unsupported** | 8/39 → 8/39 | `function-summary-unverified` 22, `contract-proposition-type` 2, `borrow-call-opaque` 2 | none |
| `src/io/rig.elisa` | unsupported | **unsupported** | 216/450 → 216/450 | `contract-expression-unsupported` 19, `contract-proposition-type` 7, `control-flow-analysis-budget` 1 | `contract-expression-unsupported` 103, `function-summary-unverified` 14 |
| `src/io/rig_map.elisa` | unsupported | **unsupported** | 213/399 → 213/399 | `function-summary-unverified` 3, `contract-expression-unsupported` 2, `contract-proposition-type` 1 | `contract-expression-unsupported` 82, `function-summary-unverified` 11 |
| `src/ops/corrections.elisa` | unsupported | **unsupported** | 857/1222 → 875/1245 | `contract-expression-unsupported` 3, `contract-proposition-type` 1, `control-flow-analysis-budget` 1 | `contract-expression-unsupported` 89, `function-summary-unverified` 37 |
| `src/ops/presets.elisa` | unsupported | **unsupported** | 1126/1602 → 1144/1625 | `control-flow-analysis-budget` 1 | `contract-expression-unsupported` 142, `contract-proposition-type` 40 |
| `src/ops/rig_stack.elisa` | unsupported | **unsupported** | 1010/1426 → 1028/1450 | `contract-expression-unsupported` 15, `contract-proposition-type` 11, `index-bounds-opaque` 3 | `contract-expression-unsupported` 127, `contract-proposition-type` 29 |
| `src/ops/stack.elisa` | unsupported | **unsupported** | 608/775 → 626/798 | `function-summary-unverified` 12, `borrow-call-opaque` 9, `expression-unsupported` 3 | `index-bounds-opaque` 19, `function-summary-unverified` 11 |
| `src/physics/rig_physics.elisa` | unsupported | **unsupported** | 1271/1781 → 1289/1805 | `contract-expression-unsupported` 19, `contract-proposition-type` 5, `expression-unsupported` 4 | `contract-expression-unsupported` 142, `contract-proposition-type` 40 |
| `src/tools/limb.elisa` | unsupported | **unsupported** | 438/687 → 438/687 | `contract-expression-unsupported` 4, `contract-proposition-type` 3, `control-flow-analysis-budget` 1 | `contract-expression-unsupported` 123, `contract-proposition-type` 26 |
| `src/tools/track.elisa` | unsupported | **unsupported** | 495/615 → 513/639 | `index-bounds-opaque` 19, `function-summary-unverified` 11, `expression-unsupported` 2 | none |
| `src/core/key_weight.elisa` | unknown | **proved** | 36/36 → 36/36 | none | none |
| `proof/key_weight_laws.elisa` | unknown | **proved** | 60/60 → 60/60 | none | none |

`src/io/report_diff.elisa`, `src/io/workers.elisa`, `src/ops/retime_apply.elisa` and
`src/ops/rig_cache.elisa` are not on mocap `main` at `ff1699d` or on any pushed branch.

What the reports show:

- **`key_weight` and `key_weight_laws` were `unknown` because of replay gaps, not open goals.**
  All 36 and 60 obligations were proven, but 6 and 9 certificates failed independent replay.
  - The producer reads `not (frame < key)` beside `not (frame == key)` as `frame > key`. The
    replay kernel's negated-comparison path lacked that step.
  - Fixed in `src/proof/kernel_replay/difference_constraints.elisa`. Both files are now
    `proved`, and `corrections` loses its 6 gaps.
- **The floating-point parameter boundary dominates.** It accounts for 1255 of the
  unsupported findings across these files, almost all of it via includes, as §2.A says. It is
  deliberately kept.
- **Corrections to the static census:**
  - `function-summary-unverified` (447) and `index-bounds-opaque` (248) are `unsupported` in this
    build.
  - `contract-proposition-type` (398, "kernel proposition formation rejected the term or
    operator") is the second most common cause, and the static reading missed it.
  - `console`, `folder` and `report` are refused mainly by `contract-proposition-type`,
    unverified summaries and `borrow-call-opaque`, not by region rules. No
    `region-alias-unsupported` finding came from those three files.
- **`track` and `stack`** have no float or include cause left. Their remaining refusals are:
  - `index-bounds-opaque` in `odd_sample`, `sample` and `lock`, where an index is `x.usize()`
    of a signed value whose bound reaches the index only through a conversion;
  - unverified callee summaries;
  - two `expression-unsupported` findings, which are a `while` condition indexing `window[j - 1]`
    in `median`.
  These are the next candidates, and each needs its own soundness argument.
- **Obligations rise by 18 to 25 per file with if-expression sites.** The arms of formerly
  refused statements are now checked. Most of the new goals prove. Some arm goals open as
  ordinary unproven findings, which is why finding counts rise slightly while no file loses a
  proof.

## 4. What this branch changes

Construct B is fixed. Code: `src/proof/check/returns/conditional_values.elisa`, called from
`proof_check_returns` in `src/proof/check/statement_checks.elisa`.

1. **Whole-statement value.** `x: T = A if c else B`, `t <- A if c else B` (with `t` a bare name),
   `return A if c else B` (which includes a tail expression, because the parser lowers it to
   `return`) and an expression statement are rewritten to the control flow they denote:

       S[A if c else B]; rest   ==>   if c: S[A]; rest   else: S[B]; rest

2. **Nested value.** `S[C[A if c else B]]` becomes `if c: S[C[A]]; rest else: S[C[B]]; rest` when
   all of the following hold:
   - `c` is call-free (integer conversions aside);
   - every subterm evaluated before the if-expression is call-free;
   - the path to it passes only through strict nodes: calls, parentheses, fields, indexes,
     tuples, unary operators and arithmetic, comparison or bitwise binary operators.

   `c` is then evaluated on exactly the paths that evaluated it before, and nothing that could
   change what `c` reads runs before it. Under `and`, `or` or `|>`, inside another
   if-expression, a match, a block or a lambda, the if-expression is not split, and the
   statement still meets the gate.

Fixtures:

- `examples/conditional_call_arms.elisa` must prove.
- `examples/rejected_conditional_call_arms.elisa` must still fail with:
  - `call-requires-unproven` for `wrong_guard` and `nested_wrong_guard`;
  - `ensure-unproven` for `skipped_arm`;
  - `expression-unsupported` for the three forms that are not split: `called_nested_condition`,
    `call_before_arm` and `short_circuit_path`.
- `rejected_conditional_conversions` `counted` (a tail `return`) is now checked as an `if`.
- `rejected_nested_call_value` keeps its refusal with a call evaluated before the conditional.

## 5. Other findings, and why they are not changed

- **A, float parameters:** kept on purpose. Admitting them soundly needs IEEE semantics (NaN,
  rounding) in the kernel, or a proof that no fact or goal mentions a float term. Weakening the
  gate would make `x == x` provable for a NaN `x`. This keeps the float-reaching files
  `unsupported`, which matches mocap's own design choice (G9: proof-critical logic is fixed
  point).
- **Extern effect rows:** not a hit. `effect-call-opaque` only fires for a function that declares
  `can[...]` and calls something with no row. The only such function, `main`, calls no extern
  directly, and the extern AST node carries no effect row to import anyway.
- **C, I/O files (`console`, `folder`, `report`):** the reports show `contract-proposition-type`,
  unverified summaries and `borrow-call-opaque`, not region rules. Each is a separate kernel or
  resource-model extension, with its own soundness argument, and none is attempted here.
- **`key_weight` / `key_weight_laws`:** fixed. They were replay gaps, not open goals (see §3). Both are now
  `proved`.
- **Missing engine checkout:** the `../../../elisa-engine-mocap` includes only resolve with that
  sibling worktree. Without it every including file also gets `import-error`. This is an
  environment issue, not a prover issue.

## 6. Test status of this branch

The build used stage1 from `d8b5d30`, seeded from stage0 `0b21b7b`, on Linux with LLVM 20.

- **`scripts/test.sh`:** every check passes except the final `scripts/census_diff.py`. That
  compares against the committed `docs/census` baseline and reports
  `typed_unsigned_literals` (a new `no-rule` gate) and `unknown_widened_borrow_write`
  (9 → 6 proven). Both behave identically on base `7571dfa`, so the baseline is stale. Whether
  the second is an upstream regression or an intended change is for the owners to decide before
  re-baselining.
- **`scripts/dogfood.sh`:** passes. This branch also repairs four failures already present on
  the base commit:
  - the standalone replay self-audit was one fact over budget;
  - two expectation sets were stale;
  - two native harnesses still built `ProofFactTrace` without `owner_line`;
  - the lemma-summary harness restored a hard-coded binding.
- **Performance:** a sampling profile of a `-g` build put `proof_disjunct_modus_ponens` in 22 of
  30 stacks on `main.elisa`. The redundant survivor-branch search it triggered is now skipped.
  - mocap `main`, `track` and `rig_physics` together: 66.1 s -> 55.6 s (16% faster), with the
    same 3368/4893 obligations proven.
  - Over all 781 examples: status, proven counts and findings are identical, and replay gaps are
    0 wherever base has 0.
  - Before that change the branch was level with base: 28.0 s / 880 MB vs 28.0 s / 885 MB on
    `main.elisa`.
- **Census baseline:** `docs/census` was regenerated with `scripts/refusal_census.py` on this
  branch (19543/26924 proven across 783 examples), so `scripts/census_diff.py` passes and
  `scripts/test.sh` is green. The old baseline (2026-10-01) predated the base commit. The three
  entries it flagged give identical results on base `7571dfa`:
  - `unknown_widened_borrow_write`: proven 9 -> 6, obligations 11 -> 7. This change is upstream;
    check it before treating it as intended.
  - `typed_unsigned_literals` and `rejected_unsigned_constant_overflow`: a new `no-rule` gate.
