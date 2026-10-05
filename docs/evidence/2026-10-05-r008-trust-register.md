# R-008 starting trust register

This is a source review and starting register for R-008, not a complete trusted-code-base audit.
It identifies visible theorem admission paths and report/package trust labels so follow-up audits
can be scoped. The implementation plan's gate (“Every admitted root exposes its transitive trust
dependencies”) is not demonstrated here, and R-008 remains open.

## Construction and admission paths

| Path | Implementation evidence | What is visible at the boundary | Follow-up needed |
|---|---|---|---|
| Expression lowering into source-neutral terms | `src/proof/kernel.elisa`: `proof_kernel_encode_expression` and `proof_kernel_add_node`; `src/proof/kernel_core.elisa`: `ProofKernelNode` | Source AST expressions are lowered into a shared arena. The AST-free core defines the node format and resource limits. | Inventory all encoder call sites and every accepted node kind against replay and source typing; this note does not prove the lowering is semantics preserving. |
| Ordinary logical goal certificates | `src/proof/replay/certificate_validation.elisa`; `src/proof/replay/fact_trace_validation.elisa`; `src/proof/certificate_admission.elisa` | A certificate root, its kernel facts, and fact-trace provenance are replayed. The report is produced by a source adapter that selects the goal and premises. | Trace every premise kind to source derivation, including declaration globals, call summaries, constants, and effects; prove complete transitive closure. |
| Quantifier, checked-index, checked-get, and ordinary goal dispatch | `src/proof/kernel_replay/api.elisa`; `src/proof/kernel_replay/reporters.elisa`; report dispatcher in `src/proof/replay/fact_trace_validation.elisa` | Public replay entry points perform arena validation and route into private specialized implementations. | Map each specialized implementation to its formal rule specification, edge cases, and tests; verify all dispatchers stay in sync. |
| Resource-safety certificates | `src/proof/certificate_admission.elisa`; `src/proof/resources/*.elisa`; `src/proof/kernel_replay/resource_*.elisa`; `src/proof/kernel_replay/reporters.elisa` | A dedicated root carries a transition trace; admission uses an inert `true` source mirror and no proposition facts. The source checker creates the events and the replay checker validates them. | Audit each source event producer against replay transition semantics and compiler/runtime memory/borrow assumptions. |
| Effect-containment certificates | `src/proof/check/effect_containment.elisa`; `src/proof/certificate_admission.elisa`; effect replay in `src/proof/kernel_replay/reporters.elisa` | The root includes declared and resolved callee effect rows; it is admitted with no proposition facts. | Trace callee resolution, extern summaries, primitive/runtime effects, and row completeness end to end. |
| Structural-safety certificates | `src/proof/check/flow_and_type_model.elisa`; `src/proof/certificate_admission.elisa`; structural replay in `src/proof/kernel_replay/reporters.elisa` | The source checker selects typed match binders and emits a ranking relation; the kernel checks serialized descent structure. | Audit that source typing/pattern identity and all possible recursive calls correspond to the serialized ranking relation. |
| Tactic proof-state construction | `src/proof/tactics.elisa`; `src/proof/tactics/kernel_replay.elisa`; `src/proof/kernel_replay/tactic_replay.elisa`; report action protocol in `src/app/report_output_integrated_helpers.elisa` | Advertised actions include assumption, exact, decide, intro, apply, simp, have, instantiate, rewrite, split, left, right, and cases; state changes are described as kernel-backed. | Audit operation-by-operation state transitions, script import and optional source binding; prove no successful search result bypasses final replay. |
| Portable package import and theorem dispatch | `src/portable/package_reader.elisa`; `src/portable/package_checker.elisa`; `src/replay_main.elisa` | Reader enforces exact schemas and bounded fields; checker admits arena shape and replays each theorem from its supplied hypotheses. The package is source-neutral and does not authenticate those hypotheses or bind them to source obligations. | Enumerate every trusted decoder/runtime/compiler dependency, all statement identity assumptions, and source-adapter relation. |

These rows are a path register, not a complete list of construction call sites or an exhaustive
inventory of inference families. In particular, every exported `proof_kernel_add_node` producer
and every path that records `ProofGoalCertificate` still needs mechanical discovery and review.

## Trust labels currently emitted

`src/app/report_output_integrated_helpers.elisa` emits `trust.trusted_boundary_facts` and a
`boundary_facts` list containing `kind`, `owner`, `line`, and `kernel_root`. It emits
`trusted_assumptions: []`, with a code comment that no trusted assumptions are currently accepted
by the proof language. These fields are a report ledger; this review has not proved the ledger is
complete or that each boundary root's dependencies are transitively summarized.

`src/app/package_output.elisa` exports package trust fields
`hypotheses: "adapter"`, `source_correspondence: "adapter"`, and
`fingerprints: "identity-hint"`; it labels source authentication false. The package checker
(`src/portable/package_checker.elisa`) reports `kernel: "checked"`,
`package_reader: "trusted"`, the same adapter/identity-hint labels, and
`source_authenticated: false`. `src/portable/package_reader.elisa` accepts only the fixed
adapter/identity-hint trust schema and refuses authenticated source claims. Those labels
accurately signal that successful portable replay checks the supplied theorem under the kernel,
but does not establish its hypotheses from source. “Kernel checked” does not imply the compiler,
runtime, source frontend, package decoder, or source adapter are outside the TCB.

## Focused test evidence

- `scripts/test_portable_replay.py` tests positive packages covering the listed portable rule
  families and forgeries with resealed statements/fingerprints. It checks the exact portable result
  trust object and confirms source authentication is false. It does not establish source-to-package
  correspondence or enumerate every core inference constructor.
- `scripts/test.d/01b-proof-report-and-tactic-boundaries.sh` checks the ordinary report trust
  fields, the boundary fact shape, `trusted_assumptions == []`, zero replay gaps, and the advertised
  tactic protocol for `examples/verified.elisa`.
- `scripts/test_kernel_inventory.py` checks the declared kernel inventory. Its existence is useful
  as an inventory guard; it does not by itself constitute a proof of each rule or of transitive
  dependencies.
- `scripts/test_replay_dependency_row.py` exercises replay dependency rows. This is relevant to
  certificate-to-certificate dependencies, but does not establish the source adapter's complete
  premise derivation.

This register was prepared by source inspection only; no build or test execution is claimed here.

## Explicit unknowns and next audit work

1. No complete graph links each admitted root through certificate dependencies, kernel facts,
   trusted boundary facts, declaration typing, source adapters, compiler/runtime behavior, and
   platform assumptions.
2. No exhaustive mapping yet relates each kernel node/rule family to a written specification,
   proof argument, specialized checker implementation, adversarial regressions, and unresolved
   assumptions.
3. The empty trusted-assumptions list describes the current proof language surface, not proof that
   every imported premise is derived from source or that no unlabelled axiom-like path exists.
4. The portable package's `kernel: checked` result still depends on `package_reader: trusted` and
   on the correctness of the checker binary/runtime. Package fingerprints are identity hints, not
   authentication.
5. Resource, effect, and structural roots are specialized checkers outside a single generic
   propositional rule dispatcher and therefore need separate TCB review.
6. Test presence and positive/negative fixtures are evidence of exercised paths only; neither
   source review nor these tests constitute a soundness proof.

R-008 should remain open until a machine-checkable or reviewable dependency register covers every
admitted root and each register entry has its rule specification, implementation, relevant tests,
and explicit assumptions.
