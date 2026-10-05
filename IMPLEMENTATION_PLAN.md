# Elisa-Proof implementation plan

Status: proposed execution roadmap, grounded in the repository inspected on 2026-09-28. This document is a plan, not a statement that the planned features are implemented or verified. Existing uncommitted implementation work must be validated separately.

## 0A. Active execution priority — correctness and iteration speed (2026-10-05)

**Mandate:** eliminate avoidable compute until Elisa's development cycle is competitive with, and where measured better than, contemporary compilers and verification tools. Correctness remains an acceptance requirement. Fast, dependable iteration is infrastructure for finding correctness defects sooner. This program supersedes the scheduling in §0 and §20; it does not weaken §3, source admission, the trust ledger, or release gates. The older feature milestones remain active after the infrastructure they require is dependable. All work below is planned unless explicitly identified as observed evidence.

### Audit baseline and limits

The 2026-10-05 audit used proof HEAD `13d686b2`, frontend pin `4c479ad1`, and a strict O2 arm64 macOS binary whose recorded source digest matched the dirty working tree. Evidence is retained locally under `build/audit-20261005/`; that ignored directory is not a durable release record. Copy reviewed summaries and minimized regressions into tracked evidence when completing the corresponding task.

- `kernel_comparison_runtime.elisa` and mocap `src/tools/track.elisa` each produced SIGSEGV and no JSON in three ordinary runs. Debugger runs stopped at the same invalid write; a link map identifies `proof_qualified_body_rewrite`. This localizes the symptom, not whether the source, compiler lowering, or runtime is responsible.
- `field_equality_runtime.elisa` exceeded a 20-second audit bound. This is not a measured completion time or the product's configured timeout.
- Three actual object-cache-hit proof builds took 1.002, 0.844, and 0.897 seconds. The proof main's include closure contained 894 files, 15.83 MB, and 216,196 lines. Every `src/` file participates in each product's object key.
- Separate symbolic-quantifier CLI runs stayed around 0.32 seconds; pure unfolding stayed around 0.45 seconds. Decision-result caching is report-local, not persistent reuse between CLI requests. Test report prefetching is per-run orchestration.
- Current source-admission, pure-unfolding, and disjunction-domain/float-boundary tests passed. `kernel_core.elisa` proved 37/37 obligations; mocap balance proved 240/240; compiler lexer proved 110/326 with zero replay gaps on completed reports. These samples are not a current full-corpus coverage rate.
- Floats now use syntactic fact containment in affected functions, not general IEEE reasoning. Earlier claims that every float parameter is immediately refused, and that pure unfolding still fails, are historical. Older census and profiler results must retain their original revision/platform labels.

### Execution queue and acceptance evidence

Work P-00 and P-01 first; then P-02/P-03 establish safe cheap reuse, P-04/P-05 establish the incremental architecture, and P-06/P-07 remove measured residual costs. Land independently reviewable improvements rather than waiting for a wholesale rewrite. Coordinate compiler infrastructure through [the compiler plan](../Elisa-compiler/IMPLEMENTATION_PLAN.md), program C-00–C-07. No delegation or new infrastructure is required merely by this schedule.

| ID | Deliverable | Acceptance gate | Current evidence / remaining gate (2026-10-05) |
| --- | --- | --- | --- |
| P-00 | Minimize and fix the qualified-constant rewriting crashes; investigate array growth, region ownership and generated code with compiler C-00 | Both original inputs produce complete reports; a minimal regression covers the responsible defect at O0/O2 on macOS and Linux. Unsupported goals remain explicit. If it is a compiler defect, retain the compiler regression and fix there rather than masking it in proof code | **Open.** Bounded unsigned-comparison refactors are committed (`95daaea`, `45e7f01`); exact-current O2 typed-unsigned controls pass with 11 certificates replayed and zero gaps. The retained manifest-bound O2 binary (`74f498…`) reproduced SIGSEGV on both workloads, but it is not the executable named by the original measurement (`d734fd…`): the recorded `build/elisa-proof` path now contains a different binary and no matching copy was found. A 51-byte reproducer (`module M: const A:i64=1; def f()->i64: return M::A`, SHA-256 `3cf171…`) crashes that retained binary; module-constant-only, plain-literal-return, and unqualified-constant-return controls pass, while qualified uses in an ensure and local initializer also crash. The exact input is retained by `scripts/test_qualified_constants.py`; strict O2 product `549ae6…` and strict O0 product `1a1ea6…` both prove its sole obligation with one replay and zero gaps on macOS. This localizes a historical qualified-constant trigger but does not identify its cause or establish behavior of the unavailable measured `d734fd…` product. A fresh strict O0 product from source digest `1f273b…` emitted complete reports without crashing on both original workloads; replay/support gaps remain, and the kernel-comparison report took 55.6 seconds. A direct O0 kernel comparison runtime had also passed before the lifetime-only follow-up. Cause analysis, the responsible defect's source-level correction, Linux coverage, and reports from the unavailable original product remain open. The two unresolved `Slide.inner` conditional-return certificates remain explicitly refused. |
| P-01 | Establish a current correctness and cost baseline with stage counters | Versioned real-code and adversarial corpus; cold/warm/no-op/edit measurements; source, binary, frontend, runtime and target identities; obligation/declaration inventory; no concealed crashes, truncation, timeout, or replay gaps | **Partial.** Seven rounds after warm-up cover three pinned fixtures with complete replay and identities. Runner schema v3 preserves the full serialized report-measurements object and labels CLI wall/CPU separately from harness JSON decoding. The CLI's tokenize/parse, proof-check, replay and serialization boundaries are identified, but the proof/compiler sources expose no monotonic clock API; internal phase timers, broader corpus and session measurements remain open. |
| P-02 | Correct cache identities before extending reuse | Include all semantic decision inputs, audit `proof_float_mode`, and bind compiler-affecting environment in object keys. Mode-switch, target-switch, stale-product, corrupted-entry and dependency-mutation controls agree with uncached runs. A missing input found in inspection is a review item, not proof that a false theorem was admitted | **Partial.** Report and object keys bind recursive inputs, binary/toolchain/runtime/target/environment and implementation recipes; payload corruption, target switch, included-source `proof_float_mode` switch and fake-writer stale-product controls pass. Fresh strict O2 runs produced byte-identical cached and uncached reports for two real bounded fixtures; editing an included real constant changed the report identity/result and its cached report still matched a fresh run. The nested-missing-dependency test verifies that a failed report is invalidated when a transitive include appears, then matches a fresh proof report. A same-path replacement between real strict O2 products (`549ae6…` to `8c63c6…`) changed the report key and forced one verifier invocation; the new report matched a fresh run. Broader dependency-mutation controls remain open. |
| P-03 | Make build/test orchestration proportional to changed inputs | Separate main/replay dependency closures; preserve unchanged snapshot files; skip unchanged hooks/link/sign/manifest work only when every effective input and output digest matches. Identical no-op products and manifests; edits outside a product's closure do not rebuild it | **Partial.** A controlled strict O2 no-op preserved product/manifest hashes and metadata and invoked no compile/link/sign/write steps. The closure test now runs the real build orchestrator in an isolated fixture: editing a source outside both product closures preserves both binaries/manifests and triggers no compile, hook build, or link. Deterministic stub tools validate orchestration decisions, not compiler semantics; the strict O2 no-op is the real-toolchain evidence. Synthetic identity controls also confirm a transitive include changes only its affected closure. |
| P-04 | Introduce reusable immutable frontend and declaration verification artifacts | Parse/resolution/type artifacts bind to compiler C-04 identities; explicit per-declaration dependency graph; unrelated edits avoid rechecking unaffected declarations; cold and incremental admitted theorem sets, completeness states, and trust ledgers agree | **Partial.** A v1 envelope binds exact build/checker context, normalized declaration identity, source slice, ordered dependency IDs and payload digest. A bounded content-addressed store now publishes immutable entries atomically and rejects corrupt, oversized, missing, or stale source/dependency entries. Compiler frontend exports no resolved typed artifact bytes; dependency discovery, reverse invalidation and verifier/session reuse remain unimplemented. |
| P-05 | Persist certificates and offer an incremental local session | CLI and local session share admission code; source edits invalidate the affected reverse dependency closure; reused certificates undergo independent checking; restart recovers valid artifacts; canceled requests cannot publish stale results | **Partial.** Fresh-process package replay rejects forged theorem, source-authentication/trust upgrades, identity mismatches, and truncation. Packages still state `source.authenticated: false`; no incremental session, invalidation, cancellation, or generation-safe publication exists. |
| P-06 | Remove dominant replay, AST and fact-management costs | Profile current large successful and refused inputs; improve indexes, term sharing, state liveness and witness reuse. Paired uninstrumented measurements show repeatable improvements with identical semantic outcomes and complete replay | **Partial.** A coherent strict O2 product binds proof source digest `1f273b…`, matching frontend/Stage1 revision `7b27fa…`, and target `arm64-apple-darwin27.0.0`. Balance profiling completed 3/3 with 240/240 replay; the pinned lexer completed with 110/110 replay and zero gaps. Commit `013fa61` inlines parenthesis stripping in the negation candidate scan. Twelve alternating uninstrumented pairs on balance, kernel core and lexer preserved byte-identical full JSON output; medians changed from 74.021 to 72.377 ms on balance, 32.756 to 32.780 ms on kernel core, and 188.268 to 181.972 ms on lexer. The 3.34% lexer reduction had non-overlapping observed ranges; the other inputs were effectively unchanged. The focused contradiction-scan regression passed. Stack detail is partial at the capture limit, and broader profile-guided speedups remain open. |
| P-07 | Close the largest real-code support bottlenecks using the faster loop | Refresh the census; rank unresolved declarations by root cause and downstream impact; repair summaries, invariants, borrow/region modeling and expression coverage with source-correspondence and negative controls. Record coverage gains and latency together | **Partial.** The six-input census binds proof source `1f273b…`, frontend/Stage1 `7b27fa…`, and binary `ba640c47…`; all inputs were hash-stable. A narrow kernel replay rule now closes the simple conditional fallback disjunction: a fresh strict O2 targeted run proves the repaired obligation with zero gaps while the wrong-guard negative control stays unproved. `Slide.inner` still has two replay gaps; field equality times out at 120s; kernel comparison and lexer retain unsupported declarations with complete replay for admitted certificates. Broader census refresh and paired latency evidence remain open. |

### Incremental verification design

1. Separate source bytes/spans, resolved semantic identity, typed verification IR, proof-search state, certificates, and presentation. A line-number change may require remapping diagnostics without invalidating an unchanged semantic theorem. Never reuse an AST handle or borrowed source view across store lifetimes.
2. Record dependencies on types, constants, defaults, overload/protocol resolution, instantiated callees, bodies when unfolded, contracts, effects/frames, regions, termination, imported lemmas, kernel/checker versions and target ABI. A failed or unsupported declaration is still an invalidation dependency; adding a declaration can change previously failed name resolution.
3. Use canonical versioned artifact bytes and cryptographic content digests. Existing FNV source/goal/theorem fingerprints remain observational guards, not authoritative proof-cache identities. Preserve ordered facts where the bounded decision procedure is order-sensitive; do not alpha-normalize or reorder hypotheses without a justified semantic boundary.
4. Maintain reverse dependency edges and verify strongly connected components atomically where recursive summaries require them. Body-only changes may preserve caller artifacts only when the verified public summary and all recorded dependencies remain unchanged. Contract, type, operator, region, or termination changes invalidate consumers deliberately.
5. Keep search memoization separate from admitted proof artifacts. Persisting a search answer must not skip proposition formation, source binding or independent replay. Budget exhaustion stays `unknown`/`unsupported`; a failed search is not a proof of falsity. Include the decision semantics/mode and applicable limits in reusable search identities.
6. Reuse validated immutable DAG nodes and dependency certificates within a checking session, with exact context/version ownership. Initially independently replay persisted certificates after reload; optimize repeated replay only through an auditable checked DAG with established immutable dependencies. No trusted `proven` bit from disk.
7. Store artifacts atomically with schemas, payload digests, explicit dependencies and bounded decoding. Exercise corrupt/truncated entries, interrupted publication, incompatible versions, missing dependencies, concurrent requests, cycles and source edits during checking. Bound cache growth; expose eviction and miss reasons.
8. A local long-lived session may retain frontend stores and checked declaration state. Keep ordinary CLI operation supported; avoid making a network service or an external solver a prerequisite for the fast path. Goal, theorem, repair and JSON routes should consume the same current checked snapshot rather than independently verifying it for each query.

### Measurement contract and performance targets

Establish one documented reference machine per required platform and freeze workload sizes, toolchain, power mode, background load and concurrency. Measure isolated latency separately from throughput. At least seven paired rounds after warm-up are required for a speed claim; publish median/p95, CPU time, peak RSS and variance. Retain cold startup and cache-validation costs. Instrumentation locates work; uninstrumented runs establish speedups.

Measure: source import/expansion, lex/parse, semantics, summary scheduling, VC generation, search, certificate encoding, replay, reporting, cache validation, and build/link work. Expose hit/miss/uncacheable counts, invalidation reasons, declarations rechecked, nodes allocated/live, fact snapshots, replayed dependency nodes and serialized bytes. Existing goal-cache counters must become observable before claiming that cache is effective.

The following are initial engineering targets, not established capabilities or platform-independent promises. P-01 must assign each target a fixed fixture and reference machine. If a target is missed, report the cause and next task; do not silently weaken it.

| Path | Target |
| --- | --- |
| Unchanged proof product build | p95 ≤250 ms; zero compiler, hook-compiler or linker invocation |
| Cached local goal/theorem/report query | p95 ≤50 ms for a fixed small response, without rerunning source verification |
| One local declaration body edit, small dependency closure | p95 ≤200 ms for the pinned interactive fixture; recheck only affected declarations |
| Incremental real module | At least 5× less CPU than clean checking for the pinned small-edit fixture; retain complete source-admission and replay coverage |
| Large-input robustness | Every benchmark completes or returns a structured bounded failure; no crash, unbounded allocation or partial `proved` output |
| Memory retention | Repeated edit/query cycles reach a bounded steady state; no growth proportional to historical edits or number of completed queries |

For comparisons with Lean/Rocq and Dafny/Verus, define equivalent theorem/query and edit scenarios within the common supported fragment, record automation and replay differences, and include startup/session state. Compare latency, CPU, RSS, coverage and correctness outcomes; never claim a general victory from unmatched workloads. The program closes only with published evidence that Elisa meets or beats the selected contemporary baselines on the declared workload classes, not merely its own historical binary.

### Remove recurring overhead without losing evidence

- No complete rebuild for an unrelated source change; no repeated whole-file checking just to render another query; no repeated linear declaration/fact scans where a measured index is warranted.
- No copy/rewrite of unchanged snapshots or artifacts; no duplicated mandatory parse/check pass inside one request; no ever-growing AST/report retention; no blanket budget increases presented as optimization.
- Partition tests by actual dependencies and reuse results only under exact binary/input/environment identities. Provide rapid focused correctness checks on every change and full source-admission, adversarial, replay, differential and dogfood qualification at integration/release checkpoints. A cached full gate applies only to its exact identity; broad correctness changes trigger the full affected gate.
- Preserve negative cases, coverage, unsupported classifications, trusted-boundary records and required declaration inventories. Timing improvements bought by checking fewer required paths are rejected.
- Promote compact reproducible benchmark summaries and regressions to tracked evidence; keep raw large captures as identified artifacts. Record incomplete validation explicitly. Do not turn this plan into another append-only performance diary.

## 0. Earlier priority override (2026-10-01): attack the big weaknesses first

A frank assessment on 2026-10-01 put the assistant at roughly 30/100 against industrial verifiers (Dafny, F*, Why3, Verus). That score is a historical qualitative assessment, not a measured contemporary benchmark. Group **W** in [BACKLOG.md](BACKLOG.md) retains the feature goals below; §0A now controls execution order, including promoting safe incremental reuse ahead of expanding automation. The rules in §3 still bind: the solver is an untrusted oracle, and every answer it gives comes back as a certificate that the Elisa kernel rechecks.

| Weakness | Why it caps the score | Gate that retires it |
| --- | --- | --- |
| W1. No SMT backend | Hand-built procedures with tight budgets return "unknown" on routine goals | Z3 (later cvc5) runs as an opt-in oracle. Its linear answers replay as Farkas certificates, and its quantifier and array answers replay as instantiation lists. The census gain is recorded with the oracle on and off, and nothing proves differently without the solver once hints are stored |
| W2. Quantifiers only over constant ranges | No loop over an array of unknown length can carry a useful invariant | Symbolic-range `forall`/`exists` with cover, extend-by-one and triggered-instance rules in the checker and the kernel. The fill, prefix-sorted, linear-search and max examples prove, and trigger-free symbolic quantifiers are refused with a message |
| W3. No array or collection theory | One element write throws away almost every fact | Read-over-write and extent preservation for `xs[k] <- v`, `push`, `pop`, `swap` and slices, with the frame lemma rechecked by the kernel. Sort- and partition-style loops keep their invariants |
| W4. Weak automation | Users must spell out intermediate facts | Oracle-guided lemma search and invariant suggestions (Houdini-style candidate pruning) whose output is ordinary checked source. Each unproven goal's near-miss names the missing fact |
| W5. Thin coverage of real code | Examples prove; real modules mostly do not | The A-05 corpus census runs on compiler and Elisa-core modules. The proved fraction of real functions is tracked per commit, and it must rise every week |
| W6. Unproven scale | Large files exhaust budgets or time | Per-function time and node budgets with incremental reuse (I-group). A 5k-line module verifies in under a minute, and the census never times out |

Progress against these gates is reported in AUDIT.md under a "Weakness program" heading with census numbers, not adjectives.

## 1. Mission and definition of success

Build an Elisa-native proof assistant that lets people and AI agents specify, prove, inspect, repair, and independently replay useful claims about real Elisa programs. Soundness takes precedence over proof coverage, speed, convenience, and feature count. Preserve useful existing behavior through incremental changes rather than replacing the system wholesale.

The intended user experience is: import a program, state a precise property, receive small actionable obligations, construct a compact editable proof, and replay it without the original AI or search process. A successful result must identify the exact program semantics, theorem, assumptions, dependencies, and checking rules that justify it.

“World class” is an engineering target with evidence gates, not a claim made after a fixed number of features. We need all of the following:

- A documented, deterministic logical foundation with an auditable implementation and explicit trust boundaries.
- Faithful verification of a declared Elisa subset, with unsupported constructs rejected or isolated rather than approximated unsoundly.
- Useful automation for routine proofs, without making automation part of the trusted proof decision.
- A stable structured agent interface and a readable proof language that humans can maintain.
- Reproducible builds, portable replay artifacts, dependency-aware reuse, and predictable resource consumption.
- Adversarial testing, independent review, and increasingly substantial machine-checked implementation properties.
- Representative end-to-end verified programs and compiler components, not only small arithmetic examples.

Initial non-goals: implement every feature of Lean, Rocq, F*, Iris, and TLA+; introduce dependent types into Elisa; claim whole-compiler correctness from example tests; or verify arbitrary unsafe/concurrent programs before defining their semantics. Borrow useful methods from these systems, but integrate them into one coherent Elisa model.

## 2. Current baseline and immediate constraints

### 2.1 What exists

The current executable is written in Elisa. [src/main.elisa](src/main.elisa) imports compiler infrastructure and connects focused proof and application modules. [README.md](README.md) describes the CLI and supported surface; [DESIGN.md](DESIGN.md) records admission and trust rules; [AUDIT.md](AUDIT.md) records historical fixes and test evidence. These are starting evidence, not substitutes for rerunning current tests.

| Area | Existing foundation | Limitation to close |
| --- | --- | --- |
| Compiler reuse | Pinned frontend export, stage1-first build, stage0 provenance checks | Binary, frontend, runtime, target, and build mode need one reproducible evidence manifest |
| Kernel | AST-free core, arena validation, typed proposition admission, replay modules | Small core does not imply the entire trusted replay and source-admission path is small or proved |
| Program checking | Contracts, call summaries, scheduling, frames, loops, termination checks | Coverage and source correspondence vary by construct and certificate family |
| Resources | Places, aliases, borrows, regions, sview tracking, resource traces | Exact provenance across some returned calls remains deliberately unsupported |
| Automation | Arithmetic, congruence, bounded reasoning, tactics, bounded repair | Typed arithmetic and independent replay need further consolidation |
| Agent surface | JSON reports, goal/theorem queries, suggestions, scripts, repair, dependency index | Stable protocol evolution, compact state transport, durable proof artifacts, and repair isolation need work |
| Dogfooding | Kernel harnesses, standalone audits, required verified helper declarations | Partial replay coverage is not complete kernel or assistant self-verification |

### 2.2 Known work that must not be hidden by the roadmap

The repository is dirty with ongoing implementation changes. The checked-in proof HEAD observed during planning is `162bd5d`; the working compiler frontend pin is `1c948fd4`. These identifiers describe this planning snapshot, not a permanent requirement to remain on those revisions.

The preceding audit run reported 1,896 obligations, 1,003 proven obligations, and zero replay gaps, but an overall unsupported/failed result. Its validator rejected missing verification of `proof_kernel_replay_constant_comparison` and `proof_kernel_replay_direct_literal_comparison`. A new recursive comparison helper exceeded a fact snapshot limit and had an unproven recursive-call precondition. These are prior-run observations to reproduce, not a freshly certified baseline. Finding counts are not interchangeable with unique obligation counts.

That audit also approached its configured memory ceiling: approximately 1,468,353 KB against 1,500,000 KB. Memory units, sampling method, completeness, and exit reason must accompany future measurements. Optimizing report materialization and fact retention is important, but must not suppress obligations or witnesses.

Recent soundness work exposes three especially important patterns:

1. Integer payloads represented through `i64` can lose the meaning of unsigned high-bit values and fixed-width operations unless type metadata participates in every relevant rule.
2. A certificate can replay successfully while its source adapter supplied a false initial fact. Earlier alias-extent and sview return-provenance bugs demonstrated this. Zero replay gaps alone is not sufficient evidence of source correctness.
3. Compiler freshness and compiler correctness are different properties. A fresh product can still miscompile valid Elisa; a stale product can make a correct prover change appear broken.

The first implementation milestone therefore closes current regressions and records a reproducible baseline. Do not declare the baseline green by removing required declarations, weakening negative tests, reducing imported source, or accepting fewer obligations without a reviewed semantic reason.

## 3. Non-negotiable engineering and soundness rules

- Keep the proof implementation in Elisa. Shell/Python may orchestrate builds, tests, fuzzing, and artifact inspection, but must not become an undocumented proof oracle.
- Use real Elisa syntax and semantics. Prefer pattern matching for variant dispatch, ML-style value blocks where clearer, and named constants for semantic limits, protocol tags, widths, and budgets. Do not invent a dereference operator or work around a compiler defect with invalid source.
- Keep implementation files at most 600 lines. Organize by responsibility and public/private boundaries, not numbered fragments. Apply the same discipline when splitting large test scripts; preserve test inventory and behavior.
- Add minimal regression cases before or alongside fixes. Every new proof capability needs valid acceptance cases, false-claim rejection cases, malformed-certificate cases, and budget-exhaustion cases.
- A producer's `proven` or tactic `solved` flag is never proof authority. Admission requires formation, source binding where applicable, dependency checks, and successful certificate checking.
- Distinguish sound conservative rejection from a supported proof. Restore lost expressiveness with evidence, not by weakening a rejection guard.
- Compiler bugs encountered during this work receive minimized stage0/stage1 cases and compiler fixes. Do not hide them in the prover. Keep unrelated compiler changes out of scoped commits.
- Commit each completed, validated gain. Record what was tested and what remains unverified. Do not commit exploratory scratch fixtures as supported functionality.
- Linux and macOS are required acceptance targets. Windows work is deferred, not an
  excuse to introduce platform-dependent proof semantics. Native ABI-dependent terms must
  carry checked width identity; cross-ABI packages must reject rather than reinterpret it.
- Run full matrices and censuses from immutable committed snapshots with matching binaries.
  Do not edit the source tree being audited. A source-digest mismatch invalidates the census,
  even when earlier focused tests passed; it is not a proof-coverage regression to bless.
- Bind every direct compiler probe to the freshness-guarded checkout explicitly. Record
  frontend, product and runtime identities. An explicit missing checkout is an error, not
  authorization to fall back to an unrelated PATH compiler or bootstrap.
- Classify failures by the failing assertion and exact obligation, not the test's headline.
  An imported-library replay gap can fail an otherwise correctly rejected adversarial fixture.
  Preserve whole-report replay gates and fix the underlying gap rather than exempting it.
- Keep performance comparisons paired on source, compiler, target, optimization mode and
  workload; compare obligations and replay coverage as well as time/instructions/memory.
  Stable profiler function identities must remain distinct through export, not just JSON capture.

## 4. Target architecture and trust model

### 4.1 Layers and responsibilities

```text
Elisa sources + specifications + compiler/target manifest
    -> checked source adapter and semantic evidence
    -> typed verification IR and explicit obligations
    -> untrusted elaboration / tactics / search / solver portfolio
    -> versioned proof terms and certificates
    -> formation + dependency + source-binding checks
    -> deterministic kernel replay
    -> admitted theorem + complete trust/dependency record
```

Use existing module boundaries as migration points: `src/proof/kernel_core.elisa`, `src/proof/kernel_replay/`, `src/proof/check/`, `src/proof/resources/`, `src/proof/replay/`, `src/proof/tactics/`, and `src/app/`. Proposed new modules below are responsibilities, not instructions to create empty scaffolding.

The target kernel should accept immutable declarations, a typed context, a proposition, and evidence; it should return checked success or a structured rejection. It must not depend on compiler AST mutation, report formatting, an AI response, solver availability, ambient filesystem state, or the order of unrelated declarations.

Keep specialized certificate checkers auditable. Where practical, translate specialized evidence into the small logical core. Where a dedicated arithmetic/resource checker remains trusted, count and document it as part of the trusted computing base rather than calling it untrusted because it is in another module.

### 4.2 Trust ledger

Every admitted result carries the transitive closure of its relevant dependencies:

| Boundary | Evidence to record | Direction of improvement |
| --- | --- | --- |
| Logic and inference | Kernel version, rule identifiers, declared logical axioms | Formalize rule soundness and audit implementation |
| Source correspondence | Resolved declarations, typed translation, source mapping | Checked translation witnesses and correspondence lemmas |
| Compiler frontend | Exact revision, semantic options, feature coverage | Verify selected checks and cross-check semantic projections |
| Compiler/backend | Compiler product, optimization level, target ABI | Differential execution, translation validation, verified passes |
| Runtime/FFI | Runtime revision, external contracts, unsafe assumptions | Verify selected runtime primitives; isolate remaining assumptions |
| Libraries | Theorem/definition identities and proof dependencies | Replay dependency closure without search |
| External solver | Solver query and certificate format/checker | Solver search untrusted; independently check certificates |
| Environment | Platform and scheduling/memory model assumptions | Explicit, reviewable model contracts |

The ledger separates mathematical axioms, source-adapter boundary facts, compiler/runtime trust, and user assumptions. A theorem proved under assumptions is useful, but must not be displayed as an unconditional program guarantee. No mutable report counter may be the sole authority for trust status.

### 4.3 Threat model and invariants

Treat source files, proof scripts, certificates, caches, solver output, imported theorem packages, and agent requests as untrusted. Cover accidental bugs and deliberately malformed inputs. The host OS/hardware remains an explicit execution assumption; this project does not promise to survive a compromised host.

Core invariants: well-formed typed terms; scoped binders; authenticated declaration identity; exact context membership; no unauthorized assumptions; checked substitution; well-founded recursive reasoning; coherent state versions; resource conservation; finite deterministic replay; and fail-closed aggregation. A partially checked program cannot acquire a whole-program `proved` status.

## 5. Milestone M0 — establish a reproducible, honest baseline

Dependencies: none. Priority: immediate. Main owners by responsibility: build scripts, audit harness, arithmetic replay, tactic branch state.

1. Inventory dirty changes and scratch files. Classify each as completed fix, regression fixture, investigation, or unrelated change. Preserve existing work; split gains into independently reviewable commits.
2. Reproduce the missing standalone verified declarations. Capture the first causative obligation, recursive precondition, fact snapshot, and dependency cascade instead of tuning from aggregate counts.
3. Diagnose fact growth with named measurements: live hypotheses, duplicated facts, branch contexts, source nodes, generated obligations, and serialized bytes. Check whether pruning is a sound weakening or accidentally deletes needed provenance.
4. Close the comparison-helper issue without restoring ambiguous signed/unsigned folding. Do not solve it merely by reducing arithmetic expressiveness or increasing every global budget.
5. Validate pending branch-scratch changes on nested `split`/`cases`, independent siblings, failing branches, depth exhaustion, and reentrant use. Ensure a child cannot mutate or borrow a sibling's state through the whole scratch container.
6. Recheck unsigned subtraction and overflow regressions across source checking, direct replay, `decide`, `simp`, repair, and certificate reuse. All entry points must agree on admissibility.
7. Produce one build manifest covering frontend source revision/tree, compiler executable digest, stage, runtime object digest, target, optimization, compile mode, and relevant flags. Verify freshness before testing; never silently bypass a stale-product guard.
8. Run focused regressions, the full test suite, dogfood, standalone validators, and optimized replay. Use the latest validated clean compiler; when concurrent development moves the source, export an immutable revision and report it explicitly.
9. Record required declaration sets and obligation inventory. Retain audit artifacts with schema/version information and compact summaries so large JSON does not become the normal debugging interface.

Positive tests: existing valid constant proofs, branch scripts, resource examples, and required standalone helper contracts. Negative tests: `u64.max < 0`, false `u8` overflow claims, invalid shifts, stale pre-call facts, wrong sview backing arguments, and sibling branch contamination.

Exit gate: every expected suite outcome is reproduced with exact provenance; required standalone declarations remain verified; no replay gaps in admitted goals; no new false acceptance; negative corpora remain negative for the intended reason. A deliberately failing corpus may pass its validator. Publish unresolved limitations separately rather than labeling the whole assistant self-verified.

## 6. Milestone M1 — typed semantic terms and source identity

Dependencies: M0. Priority: highest foundational investment. Extend existing proposition typing instead of discarding it.

1. Inventory all kernel node kinds, semantic metadata, type-environment entries, producer sites, and consumers. For every field, specify whether it is syntax, semantic identity, a type, or evidence. Eliminate meaning that depends on unrelated mutable report state.
2. Preserve width, signedness, target-sized integer meaning, Boolean distinction, literal representation, and operator semantics through lowering, substitution, serialization, normalization, and replay. Represent mathematical integers separately from machine integers.
3. Give declarations stable module-qualified identities; distinguish a builtin from a user function with the same spelling. Bind generic instantiations, constructor identities, field projections, and overloaded operator witnesses to resolved declarations.
4. Define binder identity and capture-avoiding substitution. Use explicit binder IDs or a carefully specified index representation, not raw display names. Check alpha-renaming, shadowing, nested quantifiers, and substituted type parameters.
5. Define type constructors for products, records, ADTs, functions, containers, references, views, regions, effects, and resource modes as needed by supported verification. Do not force all compiler types into the trusted kernel immediately: unsupported cases remain explicit.
6. Validate terms on entry. Check arity, child spans, index arithmetic overflow, node kind/type consistency, declaration signatures, acyclicity where required, and limits. A supplied Boolean marker is not evidence that an arbitrary source expression is Boolean.
7. Introduce a versioned migration path. Keep the current frontend working while adding typed evidence to one certificate family at a time. Replay both representations on a regression corpus where meaningful; discrepancies block migration.
8. Freeze checked environments or version them immutably. A certificate checked against one declaration context must not remain valid after in-place metadata changes.

Acceptance tests: identical numeric payloads with different widths/signedness stay distinct; argument permutation and shadowed builtins do not inherit facts; alpha-renamed valid proofs survive; malformed types and forged environments cannot authorize source-bound proofs. Legacy certificates never acquire new semantics silently.

Exit gate: all supported arithmetic and proposition rules obtain necessary type information from checked terms/environment; unsupported metadata fails closed; source identity is carried end to end; migration preserves the existing valid corpus or documents and tests a necessary soundness correction.

## 7. Milestone M2 — auditable proof calculus and portable checking

Dependencies: M1; kernel inventory can begin during M0. Choose the smallest expressive foundation justified by actual examples.

### 7.1 Logical foundation

Start from the existing typed propositional/equality machinery. Specify a simply typed, polymorphic logical layer with functions, propositions, equality, quantifiers, and algebraic data types as the target; dependent types are not a prerequisite. Decide constructivity versus classical reasoning explicitly. Classical principles, extensionality, choice, and quotient principles must be either derived, explicitly admitted, or unavailable—not implicit behavior of tactics.

Define judgments for term formation, proposition formation, theorem derivability, definitional reduction, and declaration acceptance. Specify assumption introduction/discharge, implication, conjunction/disjunction, equality congruence/substitution, quantifier introduction/elimination, and case analysis. Every rule gets a small executable acceptance/rejection test and a mathematical soundness argument relative to the selected semantics.

Definitions must not create inconsistency through arbitrary recursion, recursive types, or axioms disguised as implementation details. Check positivity for admitted inductive declarations, constructor distinctness/injectivity, and termination for executable logical reduction. Keep partial program functions separate from total logical functions.

### 7.2 Proof objects and checking

- Specify a versioned proof DAG format with rule tags, explicit premises, typed conclusions, binder context, and declaration dependencies. Share repeated subproofs without allowing cycles or mutable cross-context references.
- Make every checked theorem constructor private to the admission boundary. A public record, deserialized `verified` field, or integer certificate index must not manufacture a theorem.
- Separate raw abstract-logic replay from typed source-bound admission, preserving the useful distinction already documented in DESIGN.md.
- Extract a minimal replay executable or library using existing AST-free boundaries. It must consume complete proof packages without the search engine, AI, or source parser when the theorem is explicitly an abstract theorem.
- For a program-correctness claim, require source/IR correspondence evidence or list the adapter as trusted. A standalone checker for abstract terms does not automatically authenticate the original program.
- Bound all parsing and replay work. Resource exhaustion returns an explicit non-proof outcome; no partial prefix may be promoted to a theorem.

Adversarial tests: wrong premise order, forged context membership, escaping eigenvariables, circular proof DAGs, recursive definition loops, malformed inductives, mismatched theorem statements, stale declaration versions, and mutation after validation.

Exit gate: complete rule inventory and TCB map; documented soundness obligations per rule; minimal independent replay package works; kernel acceptance does not consult tactic success flags or solver claims; all existing supported certificates have an explicit checked path.

## 8. Milestone M3 — source-faithful verification conditions and summaries

Dependencies: M1 and the relevant M2 rules. Build on `src/proof/check/`, not a parallel undocumented verifier.

1. Specify a typed verification IR with explicit evaluation order, state versions, calls, branches, pattern bindings, exits, and effects. Include source locations for diagnostics, but do not use locations as semantic identity.
2. Define the operational semantics of the supported Elisa subset. Document trap/error behavior, overflow modes, allocation, cleanup, and observation boundaries. Resolve discrepancies with the compiler before accepting proofs about them.
3. Implement or consolidate weakest-precondition generation. Each construct has a rule, side conditions, and a correspondence obligation. A checked transformation witness is preferred; until available, its generator remains in the explicit source-correctness TCB.
4. Model normal return, error return, panic/abort, break, continue, and divergence separately. A proof of partial correctness is not a proof of termination or absence of runtime failure.
5. Check contracts at declarations and calls. Bind named/default arguments once in source evaluation order; handle nested calls and side effects before consuming outer postconditions. Keep `old` values tied to the correct entry state.
6. Preserve the existing dependency-order/SCC scheduling discipline. A failed body invalidates its summary and downstream callers. Provisional recursive summaries require checked induction/termination premises and must not leak outside their verification unit.
7. Treat loop invariants as three obligations: initialization, preservation, and use at exit. Track frame/resource/effect invariants too. A loop bound used for exploration is not an inductive invariant.
8. Implement precise SSA/state-version joins and conservative fact invalidation across writes/calls. Projection disjointness must be proven; by-value aggregates containing references are not automatically local storage.
9. Create a feature coverage matrix: compiler syntax accepted; typing imported; logical semantics modeled; certificate emitted; replay checked; source correspondence established. “Parses” is not “verified.”

Tests: short-circuit expressions, value blocks, early exits, nested calls, changed defaults, mutable globals, branch-local hypotheses, unreachable code with and without a valid contradiction, cleanup on errors, and failed summaries in mutual call graphs.

Exit gate: every claimed supported construct has an explicit semantics and test family; no omitted path authorizes a whole-function summary; source-order changes preserve results where semantics are unchanged; unknown constructs produce localized unsupported obligations.

## 9. Milestone M4 — machine arithmetic and dependable decision procedures

Dependencies: M1, M2. Develop in parallel with M3 once typed terms are stable.

- Define exact arithmetic domains: mathematical integers/naturals, fixed-width signed/unsigned values, target-sized values, and later floating point. Never transfer an integer theorem to modular arithmetic without checked side conditions.
- Implement checked literal parsing and normalization, including full unsigned ranges. Avoid representing a valid `u64` only by a signed interpretation that later rules mistake for a negative number.
- Specify addition/subtraction/multiplication, division/remainder, casts, shifts, comparisons, and bitwise operators from Elisa semantics. Cover division by zero, signed minimum divided by minus one, negative remainder conventions, and oversized shifts.
- Use explicit evidence for arithmetic simplification: typed evaluation traces, checked identities, linear combinations, difference paths, or bit-level certificates. Producer and checker must not share a single opaque Boolean “solver succeeded” routine.
- Keep lightweight normalization, congruence, and difference reasoning cheap. Add linear integer reasoning with checked coefficients and side conditions; distinguish integer and rational feasibility.
- Add SAT/bit-vector search only with a selected certificate strategy: checked bit-blasting plus propositional evidence, or a narrowly specified native certificate checker. Translation itself must be checked or counted as trusted until verified.
- Make model validation independent of solver status. A proposed counterexample must satisfy source hypotheses and violate the property under the actual width and execution semantics.
- Treat floating point conservatively until NaN, infinity, signed zero, rounding, and conversions have explicit semantics and checked rules. Do not substitute real arithmetic implicitly.

Tests: exhaustive small-width models, all boundary values, cast round trips, mixed widths, wrapping intermediate expressions, signed/unsigned ordering, invalid shifts, false nonlinear identities, and adversarial arithmetic inside otherwise trivially equal expressions.

Exit gate: all existing arithmetic entry points share the same typed semantics; false fixed-width claims fail in source checking, tactics, repair, and replay; positive coverage expands beyond temporary conservative literal restrictions; solver-free certificate replay is demonstrated.

## 10. Milestone M5 — ownership, regions, permissions, and framing

Dependencies: M1–M3. Highest priority expressiveness recovery: exact sview call-return provenance.

### 10.1 Places and lifetimes

Use canonical allocation/place identities with projection paths, state versions, and region identities. Distinguish alias equality, proven disjointness, and unknown overlap. Normalize caller/callee place mappings without confusing a forwarded reference with a new allocation.

Represent `sview` as a valid view into live backing storage, not an implicitly optional pointer. An empty view is still valid according to the chosen representation. Track backing allocation, offset/length, and lifetime constraints; require the backing storage to outlive all uses. Account for mutation and reallocation, not only lexical region exit. Optionality belongs in an explicit optional type when needed.

Implement source-bound call-return witnesses: selected callee result relation, instantiated formal-to-actual mapping, exact backing place, region inequalities, and write/borrow restrictions. Replay must reject wrong-argument permutations, unrelated reads, and witnesses from another call. Recover currently unsupported direct named-call returns only after these checks exist.

### 10.2 Resource algebra and frame rules

- Specify owned, affine, linear, shared-borrow, exclusive-borrow, and capability states. Track resource identity and quantity separately from ordinary Boolean facts.
- Add a small permission algebra. If fractional sharing is introduced, use exact arithmetic and checked conservation; two full writers must never arise from splitting one permission.
- Define frame inference as untrusted search for a checked decomposition: consumed resources, produced resources, and unchanged disjoint remainder. Unknown aliasing blocks preservation, not the entire diagnostic pipeline.
- Model moves, partial moves, container elements, reference-bearing aggregates, returned borrows, reborrows, allocation, deallocation, and exceptional cleanup. Linear resources require consumption; affine resources allow only their specified discard behavior.
- Check allocation into `new[r]` against actual region `@r` and its lifetime constraints. Compiler and prover must agree on legality rather than inventing a separate region interpretation.
- Specify trusted FFI contracts, including `cstr` termination and accessible length. Null termination and lifetime validity are distinct obligations; a terminator does not make dangling storage safe.

Tests: forwarded by-reference indexed frames, nested aliases, disjoint fields, unknown indices, collection reallocation with a live view, return from a shorter region, escape through aggregates/callbacks, duplicate ownership, missing release, use after move, and forged permission arithmetic.

Exit gate: precise call-return sview examples prove and wrong-backing variants fail; no name-based or “last read” provenance heuristic authorizes a resource fact; frame certificates account for all consumed/produced resources; unsupported escapes remain explicit.

## 11. Milestone M6 — ADTs, quantifiers, induction, and totality

Dependencies: M2, M3, typed ADT declarations from M1.

1. Import ADT declarations and checked pattern typing, including module/generic identity. Derive constructor discriminators, injectivity, and exhaustive cases from declarations, not display names.
2. Support general logical quantifiers beyond finite enumeration. Check instantiation types, freshness of introduced variables, and capture avoidance. A finite-range decision procedure must never silently stand in for an unrestricted quantifier.
3. Provide structural induction with explicit motives, constructor cases, and strictly smaller recursive fields. Keep the link between matched source binders and actual ADT subterms in checked evidence.
4. Extend existing termination support with checked lexicographic measures and mutual SCC reasoning. Measures must use a well-founded domain; wrapping machine arithmetic is not automatically a natural-number ranking.
5. Separate partial correctness, total correctness, and logical definitional reduction. Divergent executable code cannot establish a theorem by circularly assuming its own postcondition.
6. Add refinement predicates over existing types as specifications, without making the Elisa compiler depend on a general dependent type system. Elaborate refinement checks into ordinary obligations.
7. Introduce ghost values and lemma functions with explicit erasure and purity rules. Ghost computation must not influence runtime behavior through hidden effects, exceptions, ownership transfer, or unsafe access.

Positive demonstrations: list/tree invariants, parser structure preservation, lexicographic recursive algorithms, quantified collection properties. Negative tests: invalid induction hypotheses, nondecreasing mutual recursion, wrong constructor identity, quantifier scope leaks, and ghost writes influencing execution.

Exit gate: reusable human-written inductive proofs replay; termination claims identify checked measures; structural correspondence no longer relies on unaudited binder-name conventions for the supported ADT subset.

## 12. Milestone M7 — effects, handlers, errors, and modular specifications

Dependencies: M3, M5, M6 where recursive specifications are involved.

- Model effects/capabilities as resolved identities and explicit rows, not strings that happen to resemble builtins. Check effect containment at every call and overloaded operation.
- Define effect-indexed specifications with normal/error postconditions, resource transfer, permitted writes, and termination behavior. Composition must account for both control flow and resource state.
- Model handlers according to Elisa continuation semantics. Specify whether a continuation may resume zero, one, or multiple times and how resources/capabilities move on resume. Reject unsupported resumption shapes.
- Make exception/error cleanup and destructor effects visible. A pure-looking expression can still allocate, panic, invoke a user operator, or release a resource.
- Add abstraction boundaries for modules: public contracts and opaque implementation details. Private proofs may justify a public summary without exposing mutable internal facts.

Tests: omitted effects, same-spelling foreign capability, nested handlers, duplicated linear continuations, error-only leaks, cleanup effects, and falsely pure operator implementations.

Exit gate: verified composition across supported effects and errors; handler rules have operational justification; unsupported effects are reported at the responsible operation; logical ghost/specification code cannot smuggle runtime effects.

## 13. Milestone M8 — automation, solver portfolios, and reconstruction

Dependencies: M2 and the domain-specific rules used by each engine. Do not wait for every language feature to improve automation.

Order engines from cheap to expensive: assumptions and typed normalization; congruence; interval/difference reasoning; linear arithmetic; datatype reasoning; bounded quantifier instantiation; bit-vectors; lemma search; induction hints; external solvers. Scheduling is a performance policy, not a proof rule.

Each engine implements a common result contract: applicability, budget consumed, attempted transformations, proof candidate or model candidate, and a precise non-success reason. Every success proposal passes ordinary kernel admission. Record seeds and solver options; replay must not rerun search.

Implement deterministic theorem indexing by typed conclusion shape, declaration identity, and relevant premises. Search only uses admitted theorems; unverified declarations remain visible as repair targets, never silently usable lemmas. Preserve exact instantiation and premise proofs in `apply` certificates.

Choose one external solver/certificate integration first. Evaluate certificate availability, checker complexity, unsupported steps, resource usage, and translation faithfulness before expanding the portfolio. An uncheckable `unsat` answer is a solver outcome, not a proved theorem. An external model is not a disproval until validated.

Add rewrite/simplification sets with orientation, conditions, and termination control. Detect loops and expose the exact rewrite chain. Conditional rewrites must discharge their conditions in the current context without circular use of the goal.

Exit gate: automated proofs replay with solvers and AI absent; deliberately lying/mock solvers cannot cause acceptance; timeouts and unsupported certificate steps remain non-proofs; representative proofs become materially shorter without enlarging hidden trust.

## 14. Milestone M9 — human proof language and stable agent API

Dependencies: build incrementally on existing tactics/CLI; type and certificate schemas depend on M1/M2.

1. Specify a versioned protocol for goals, hypotheses, definitions, theorem discovery, tactic actions, partial proofs, counterexamples, budgets, dependencies, and errors. Preserve compatibility through explicit capability negotiation, not undocumented field changes.
2. Separate stable semantic IDs from report sequence numbers and source locations. Actions carry the expected proof-state version; stale actions fail without mutating the state.
3. Make transitions transactional. Failed `rewrite`, `apply`, `split`, or `cases` cannot leave admitted facts or half-committed children. Independent branches have distinct contexts and resource ownership.
4. Extend readable Elisa-like scripts with nested branches, explicit lemma arguments, intermediate claims, and local names. The current canonical-block comparison command is not itself a general proof elaborator; document the distinction from executable scripts.
5. Keep parser/elaborator output untrusted. Store both human source and elaborated certificates; render unsupported terms explicitly rather than printing misleading executable-looking text.
6. Provide compact goal queries and paginated/streamed traces, avoiding full arena dumps for normal agent interaction. Offer exact source locations, causal failure chains, and relevant hypotheses.
7. For repair, expose changed definitions, invalidated obligations, and downstream consumers. Bound candidates and cost; replay the winning proof; never auto-weaken a user property or add an assumption to make repair succeed.
8. Report a small relevant unresolved core where feasible. Do not promise global minimality for expensive minimization; label whether the reported core is proven minimal or merely reduced.

Status design: distinguish `proved`, `disproved` with validated witness, `unknown`, `timeout`, `unsupported`, and trusted-assumption/conditional results. Keep malformed input/internal error separate from mathematical failure. Whole-program status must account for every required obligation and import/admission failure; bounded success must include its scope.

Exit gate: an external agent can inspect, prove, repair, and replay a representative example entirely through documented structured interfaces; a human can edit its proof; malformed/stale requests cannot change trust; output remains deterministic apart from explicitly separated timing telemetry.

## 15. Milestone M10 — dependencies, incremental checking, and proof packages

Dependencies: M1/M2 identity and versioning, M3 summary dependencies; can progress alongside M9. **Scheduling update 2026-10-05:** §0A P-02–P-05 promotes the safe incremental slices of this milestone into the active execution queue. Implement the necessary identity/dependency foundations with those slices rather than waiting for all earlier feature milestones to finish.

- Track dependencies on source declarations, types, contracts, bodies where needed, frame/effect summaries, termination measures, imported lemmas, compiler semantics, target ABI, and kernel rules.
- Separate statement identity from proof identity and source artifact identity. A theorem with the same text under a different type/region environment is not automatically the same theorem.
- Replace observational non-cryptographic hashes as authoritative cache identities. Use canonical bytes with an appropriate content digest, and still validate context and replay evidence. A hash match is never a proof.
- Invalidate the reverse transitive closure when semantics change; preserve unaffected certificates. Contract weakening/strengthening and effect/frame changes need deliberate invalidation rules, not text-only comparison.
- Make cache writes atomic and corruption-detecting. Reject truncated artifacts, conflicting versions, cycles, missing dependencies, and proof objects from another target or semantics version.
- Package source/IR bindings, declarations, proof DAGs, assumptions, and build/checker manifests for offline replay. Explicitly distinguish a package proving an abstract statement from a package proving correspondence to executable source.

Tests: unrelated line edits preserve valid reuse; changed constants/types/defaults/operators/regions invalidate exactly affected proofs; deliberate digest collisions in a test backend do not bypass equality/admission checks; missing assumptions and corrupted dependencies reject.

Exit gate: clean full checking and incremental checking produce identical admitted theorem sets and trust ledgers across a mutation corpus; offline replay does not require AI, solver processes, or a mutable compiler checkout.

## 16. Milestone M11 — bounded checking and concrete counterexamples

Dependencies: typed machine semantics, M3 execution model, M4 certificate/model checking.

Implement explicit bounded exploration over loops, recursion, inputs, and eventually schedules. Include exact bounds in every result. Prove a finite bounded claim only when the explored domain and its coverage are checked; absence of a counterexample is not an unbounded program proof.

Generate concrete witnesses with inputs, branch decisions, relevant heap/resource state, and the failed property. Validate witnesses in a small semantic interpreter or checked execution trace. Where execution is safe and appropriate, replay the example against a compiled program as additional diagnostic evidence, not the sole logical check.

Report whether a bound was exhausted and whether a model came from an over-approximation. Abstract/spurious counterexamples remain candidates until refined and validated. Distinguish a real source runtime failure from an unsupported abstract operation.

Exit gate: small exhaustive domains agree with reference enumeration; off-by-one bounds and truncated schedules never produce unbounded claims; concrete counterexamples are reproducible and use the same arithmetic and error semantics as proof generation.

## 17. Milestone M12 — concurrency, protocols, and temporal reasoning

Dependencies: mature M3/M5/M7 foundations. This is a later program, not a prerequisite for useful sequential verification.

### 17.1 Concurrent safety

First specify supported execution and memory models. Begin with a clearly delimited sequentially consistent concurrent subset if appropriate; do not apply its results to relaxed atomics. Identify thread creation/join, shared storage, locks, atomics, and capability transfer.

Add checked resource transfer between threads, shared invariants, exact invariant opening/closing rules, and atomic-operation specifications. Ghost resources must satisfy explicit algebraic laws. Prevent ownership duplication and invariant use across forbidden non-atomic steps.

Support protocol state machines for channels and shared objects. Prove allowed transitions, ownership transfer, and invariant preservation. Add linearization-point proofs only with a defined observational/refinement relation.

Tests: data races, double writers, missing acquire/release conditions, invariant escape, duplicated ghost ownership, double unlock, invalid channel transitions, and incorrect atomicity claims.

### 17.2 Deadlock and liveness

Keep deadlock freedom, termination, lock freedom, starvation freedom, and temporal liveness distinct. Start with lock-order/resource-dependency proofs for a supported subset and finite-state protocol checks with explicit scope.

Define transition systems and temporal operators, then make fairness assumptions explicit in the theorem. Add ranking/progress certificates and checked state-space coverage where feasible. A bounded schedule search cannot establish general eventual progress.

Tests: unfair schedules, circular waits, disabled transitions, vacuous liveness premises, infinite stuttering, and finite-prefix traces incorrectly advertised as infinite-run evidence.

Exit gate: at least one nontrivial shared-state protocol has independently replayed safety evidence; deadlock/liveness results state their memory model, scheduler/fairness assumptions, and finite or unbounded scope; unsupported relaxed-memory behaviors remain rejected.

## 18. Milestone M13 — dogfood the assistant and compiler without circular claims

Dependencies: starts at M0 and expands with each foundation. Self-verification is a ladder, not a final Boolean flag.

| Level | Target properties | Required evidence |
| --- | --- | --- |
| D0 | Kernel helper bounds, arithmetic preconditions, arena access safety | Existing standalone contracts plus checked required-declaration coverage |
| D1 | Arena formation, DAG acyclicity, substitution scope/type preservation | General contracts, inductive proofs, malformed-input regression corpus |
| D2 | Each inference and specialized certificate rule preserves validity | Mathematical model, rule lemmas, executable checker refinement properties |
| D3 | Replay implementation implements the modeled judgment | Functional correctness contracts covering success and rejection paths |
| D4 | WP/resource/effect translation preserves source semantics | Checked transformation rules and source-correspondence theorems |
| D5 | Selected compiler frontend/backend/runtime components | Precise pass/primitives specifications and replayable correctness proofs |
| D6 | Larger end-to-end compilation/verification chains | Composed refinement theorems with explicit remaining platform assumptions |

Begin compiler dogfood with bounded, high-value components: literal parsing, symbol identity, builtin recognition, bounds/noalias fact provenance, region-escape checks, and selected constant folding. Then verify selected IR transformations and runtime buffer/view operations. Prioritize defects that could invalidate proof execution or the source model.

For each discovered compiler bug: minimize valid/invalid Elisa input, establish intended semantics, compare fresh stage0 and stage1, inspect debugger evidence, patch the responsible compiler, add differential and optimization-level tests, rebuild clean products, rerun affected prover suites, and commit scoped changes. If both compilers agree incorrectly, differential agreement is not correctness evidence.

Use the Elisa debugger for crashes, invalid region access, and suspicious lowering. Improve missing diagnostics with a minimal case. Use the Elisa profiler to identify measured hot paths, fact duplication, arena allocation, and report serialization costs; profiling hooks must not silently alter proof semantics or linking behavior.

Avoid circular trust claims: a checker proving some of its own contracts still relies on its execution/compiler and any assumed semantics. Seek an independently implemented small checker or an external formal model for cross-checking critical artifacts. Cross-checking is additional evidence, not an automatic foundational proof. Document exactly what D-level has been achieved for each component.

Exit gate per level: enumerate proved declarations/properties, assumptions, checked artifacts, and uncovered code paths; rerun under clean toolchains; retain adversarial tests. Never summarize partial helper verification as “the proof assistant is proved correct.”

## 19. Testing, performance, and release gates

### 19.1 Test layers

- Unit: each formation/inference/resource rule, valid and invalid applications, boundary arithmetic, and exact rejection reasons.
- Metamorphic: alpha-renaming, unrelated declarations, equivalent module qualification, branch reordering where semantically valid, and formatting changes preserve appropriate results.
- Mutation: alter a premise, width, declaration ID, region, callee mapping, branch state, or certificate edge; ensure the intended invariant is actually exercised.
- Differential: stage0/stage1 and optimization levels, full versus incremental checking, direct proof versus tactic-generated proof, reference evaluation versus normalization.
- Fuzz: typed and malformed terms, proof DAGs, JSON/scripts, imports, and dependency packages. Minimize failures and retain seeds/artifacts.
- Integration: existing source matrix, standalone validators, optimized replay, dogfood, CLI/protocol schemas, and offline packages.
- Independent review: logic rules, source adapters, unsafe boundaries, and newly trusted specialized checkers receive focused review before release.

False acceptance is a release blocker. Rejection of a formerly valid proof is either a documented soundness correction or an expressiveness regression to fix. Crashes, incomplete outputs, and timeouts must not be accepted merely because a subprocess produced some proof-shaped JSON.

### 19.2 Performance discipline

Establish a versioned benchmark corpus: small interactive goals; medium contract-heavy modules; ADT proofs; resource-heavy code; standalone kernel audit; and adversarial depth/size cases. Record cold/warm time, peak memory, generated obligations, proof bytes, replay time, and verified declaration coverage.

Set explicit latency/memory targets after baseline measurement and publish them per benchmark machine. First remove current audit headroom risk. Prefer compact immutable arenas, shared proof DAGs, liveness-aware fact storage, incremental summaries, and streamed reporting only when profiling supports them. No optimization may omit a required path or turn exhaustion into success.

Expose named configurable budgets with measured `observed`, `limit`, stage, and reason. Check arithmetic used in budgeting for overflow. Keep budget changes separate from logical feature changes so a regression cannot be hidden by a larger ceiling.

### 19.3 Release evidence

A release requires: clean reproducible compiler/runtime provenance; passing expected regression gates; no known false-acceptance bug in the supported subset; complete replay for admitted claims; required dogfood coverage; documented assumptions and unsupported features; schema migration tests; and benchmark results. Full tests must run on the exact commit being released.

Maintain a soundness incident procedure: preserve reproducer, contain the affected rule, identify affected artifact versions, invalidate or require replay of impacted caches, fix both producer/checker boundaries as necessary, add positive and adversarial regressions, and publish the limitation. Never silently retain “proved” labels on artifacts known to be affected.

## 20. Execution order and first actionable backlog

**Superseded ordering:** §0A P-00–P-07 controls execution. Group W remains the feature backlog after reliability and safe incremental infrastructure. The original ordering follows for reference.

The critical path is M0 → M1 → M2/M3/M4 → M5/M6/M7. M8–M10 grow alongside these foundations. M11 follows faithful execution semantics. M12 follows mature resource/effect support. M13 is continuous. Do not defer all user-facing improvements until the final milestone, and do not expand concurrency before the sequential source model is dependable.

| ID | Next deliverable | Depends on | Completion evidence |
| --- | --- | --- | --- |
| P0-01 | Reproduce current audit/helper failures and classify dirty work | None | Exact build manifest, first failing obligation, scoped change inventory |
| P0-02 | Close typed-comparison helper verification without unsound folding | P0-01 | Required declarations restored; arithmetic negative/positive suites pass |
| P0-03 | Validate tactic branch ownership and pending subtraction changes | P0-01 | Nested/adversarial fixtures and fresh compiler matrix |
| P0-04 | Full baseline and scoped implementation commits | P0-02/03 | Main suite, dogfood, validators, optimized replay; retained logs |
| P1-01 | Inventory kernel terms, rule families, source boundary facts | P0-04 | Reviewed schema/rule/TCB table linked to implementation |
| P1-02 | Typed integer identity through constant comparison and replay | P1-01 | High-bit unsigned and mixed-width tests; versioned migration |
| P1-03 | Exact sview returned-call witness design and implementation | P1-01, M1 identity | Valid wrapper calls prove; wrong-argument/region variants reject |
| P1-04 | Compact measured audit diagnostics and fact-growth fix | P0-04 | Same required proof coverage with safe memory headroom |
| P1-05 | Complete source-admission gate matrix | P1-01 | Every CLI/tactic/repair/reuse route tested against malformed source |
| P2-01 | Portable minimal replay package for a supported certificate slice | M2 slice | Replay without compiler AST, AI, or solver; explicit source trust |
| P2-02 | Checked WP/state correspondence for a small sequential subset | M3 slice | Assignment, branch, call, and loop examples plus mutation tests |
| P2-03 | First substantive ADT/inductive proof library | M6 slice | Reusable parser/tree/list proofs with totality evidence |

For each backlog item, use this execution loop: inspect current code and failures; state the invariant; create positive and adversarial tests; implement the smallest coherent change; run focused then full relevant gates; inspect trust and coverage deltas; document remaining limitations; commit the validated gain. A compiler defect discovered in the loop becomes a linked prerequisite, not an excuse to suppress the failing proof test.

The detailed task backlog, ranked by return on investment, lives in [BACKLOG.md](BACKLOG.md): 74 tasks with IDs, rationale and completion evidence. It starts with a refusal census (A-01), so each later task is chosen by measured impact.

## 21. Decisions that need evidence before commitment

- Logical core: prototype representative polymorphic, quantified, and inductive proofs. Select the smallest calculus that supports them with a tractable soundness argument; record explicit axiom choices.
- Proof representation: compare current arenas with typed proof DAGs on memory, checker complexity, and serialization stability. Migrate only with demonstrated benefits and compatibility checks.
- Solver certificates: prototype one realistic arithmetic/bit-vector workload and one adversarial malformed certificate. Reject an integration whose translation/checker trust cost exceeds its value.
- Permission model: begin with actual Elisa ownership/borrow requirements; introduce fractions or richer ghost algebras only when a concrete shared-state proof requires them.
- Source semantics: settle ambiguities in overflow, pointer/FFI behavior, handlers, and concurrency jointly with compiler specifications. Until settled, decline the affected guarantee explicitly.
- Self-verification scope: choose small meaningful functional properties before expanding source coverage. General replay soundness is a stronger target than proving individual array accesses safe.

Each investigation must produce a runnable experiment, recorded alternatives, explicit success/failure criteria, and a decision. Avoid open-ended infrastructure rewrites or empty interfaces for hypothetical engines.

## 22. Definition of done for every capability

A capability is done only when its semantics and supported subset are documented; its producer and checker responsibilities are explicit; its trust dependencies are exposed; positive and adversarial tests pass; budget failures are honest; source, tactic, repair, and reuse entry points agree; proof artifacts replay deterministically; relevant full suites remain green; and the change is committed with evidence.

The final measure is not “how many goals say proved.” It is how much useful Elisa code can be verified under precise, reviewable assumptions, with compact proofs that an independent checker can replay—and how reliably the system refuses false or unsupported claims.
