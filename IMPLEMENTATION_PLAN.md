# Elisa-Proof implementation plan

Status: updated execution roadmap, initially inspected on 2026-10-05 at clean proof HEAD `cd42c89c`. Section 23 defines the next high-ROI execution order; [BACKLOG.md](BACKLOG.md) retains the themed feature inventory and completion records. Sections 0A and 5–22 retain implementation evidence and architectural requirements. This is a plan, not a claim that every preceding milestone is complete or that the current full suite has been rerun. Historical measurements apply only to their recorded products.

## 0A. Active execution priority — correctness and iteration speed (2026-10-05)

Scheduling update: §23 now carries the next ordered backlog. The P-00–P-07 evidence and incomplete acceptance gates below remain binding; this historical queue is not a declaration that those tasks are finished.

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
| P-00 | Minimize and fix the qualified-constant rewriting crashes; investigate array growth, region ownership and generated code with compiler C-00 | Both original inputs produce complete reports; a minimal regression covers the responsible defect at O0/O2 on macOS and Linux. Unsupported goals remain explicit. If it is a compiler defect, retain the compiler regression and fix there rather than masking it in proof code | **Open.** Bounded unsigned-comparison refactors are committed (`95daaea`, `45e7f01`); exact-current O2 typed-unsigned controls pass with 11 certificates replayed and zero gaps. The retained manifest-bound O2 binary (`74f498…`) reproduced SIGSEGV on both workloads, but it is not the executable named by the original measurement (`d734fd…`): the recorded `build/elisa-proof` path now contains a different binary and no matching copy was found. A 51-byte reproducer (`module M: const A:i64=1; def f()->i64: return M::A`, SHA-256 `3cf171…`) crashes that retained binary; module-constant-only, plain-literal-return, and unqualified-constant-return controls pass, while qualified uses in an ensure and local initializer also crash. LLDB on the retained repro stops at `proof_qualified_body_rewrite +384` with a stack address used as the rewritten-array index; this narrows the symptom to invalid append state, while a borrow/region cause remains a hypothesis (details in `docs/evidence/2026-10-05-proof-queue.md`). The exact input is retained by `scripts/test_qualified_constants.py`; strict O2 product `549ae6…` and strict O0 product `1a1ea6…` both prove its sole obligation with one replay and zero gaps on macOS; the full `scripts/test_qualified_constants.py` suite passes on both products. This localizes a historical qualified-constant trigger but does not identify its cause or establish behavior of the unavailable measured `d734fd…` product. A fresh strict O0 product from source digest `1f273b…` emitted complete reports without crashing on both original workloads; replay/support gaps remain, and the kernel-comparison report took 55.6 seconds. A direct O0 kernel comparison runtime had also passed before the lifetime-only follow-up. Cause analysis, the responsible defect's source-level correction, Linux coverage, and reports from the unavailable original product remain open. The exact-product O0/O2 matrix, including both original workloads and the minimized fixture, is recorded in [`docs/evidence/2026-10-05-p00-identity-matrix.md`](docs/evidence/2026-10-05-p00-identity-matrix.md); it confirms current products pass the minimized case but does not resolve the historical cause. A follow-up audit reran historical binary controls and inspected the rewrite source history; the indexed-store trace narrows the symptom, but no causal edit was isolated ([`docs/evidence/2026-10-05-p00-qualified-crash-cause-audit.md`](docs/evidence/2026-10-05-p00-qualified-crash-cause-audit.md)). The two unresolved `Slide.inner` conditional-return certificates remain explicitly refused. |
| P-01 | Establish a current correctness and cost baseline with stage counters | Versioned real-code and adversarial corpus; cold/warm/no-op/edit measurements; source, binary, frontend, runtime and target identities; obligation/declaration inventory; no concealed crashes, truncation, timeout, or replay gaps | **Partial.** Seven rounds after warm-up cover six pinned fixtures with complete replay and build/source identities: acceptance, refusal, the adversarial case, qualified-constant acceptance/refusal, and `src/proof/kernel_core.elisa` itself (37/37 obligations proved/replayed; zero gaps). The kernel-core run records cold/warm/comment-only medians and p95 with binary, frontend, runtime, source and target identities in [`docs/evidence/2026-10-05-p01-kernel-core.md`](docs/evidence/2026-10-05-p01-kernel-core.md). Runner schema v3 preserves the full serialized report-measurements object and labels CLI wall/CPU separately from harness JSON decoding. The CLI's tokenize/parse, proof-check, replay and serialization boundaries are identified, but the proof/compiler sources expose no monotonic clock API; broader real-code corpus, internal phase timers and session measurements remain open. |
| P-02 | Correct cache identities before extending reuse | Include all semantic decision inputs, audit `proof_float_mode`, and bind compiler-affecting environment in object keys. Mode-switch, target-switch, stale-product, corrupted-entry and dependency-mutation controls agree with uncached runs. A missing input found in inspection is a review item, not proof that a false theorem was admitted | **Partial.** Report and object keys bind recursive inputs, binary/toolchain/runtime/target/environment and implementation recipes; payload corruption, target switch, included-source `proof_float_mode` switch and fake-writer stale-product controls pass. Fresh strict O2 runs produced byte-identical cached and uncached reports for two real bounded fixtures; editing an included real constant changed the report identity/result and its cached report still matched a fresh run. The nested-missing-dependency test verifies that a failed report is invalidated when a transitive include appears, then matches a fresh proof report. A same-path replacement between real strict O2 products (`549ae6…` to `8c63c6…`) changed the report key and forced one verifier invocation; a durable regression in `scripts/test_report_cache_executable_swap.py` now checks the changed key, exactly one verifier invocation, a subsequent cache hit, and cached/uncached report equality. A symlink-retarget regression now keeps the source's include spelling fixed while changing the resolved dependency, requires a new key and one verifier call, verifies the old cache entry remains intact, and matches a fresh uncached report. A new nested-leaf edit regression keeps include directives fixed, requires a new key and exactly one verifier call, preserves the prior cache entry, and matches cached and fresh reports. Broader dependency-mutation controls remain open. |
| P-03 | Make build/test orchestration proportional to changed inputs | Separate main/replay dependency closures; preserve unchanged snapshot files; skip unchanged hooks/link/sign/manifest work only when every effective input and output digest matches. Identical no-op products and manifests; edits outside a product's closure do not rebuild it | **Partial.** A controlled strict O2 no-op preserved product/manifest hashes and metadata and invoked no compile/link/sign/write steps. The closure test now runs the real build orchestrator in an isolated fixture: editing a source outside both product closures preserves both binaries/manifests and triggers no compile, hook build, or link. A focused real-validator test confirms an intact build-manifest checksum sidecar permits reuse, corruption causes a miss, and restoring it permits a hit; it uses synthetic product files and does not demonstrate a full rebuild after corruption. Deterministic stub tools validate orchestration decisions, not compiler semantics; the strict O2 no-op is the real-toolchain evidence. Synthetic identity controls also confirm a transitive include changes only its affected closure. |
| P-04 | Introduce reusable immutable frontend and declaration verification artifacts | Parse/resolution/type artifacts bind to compiler C-04 identities; explicit per-declaration dependency graph; unrelated edits avoid rechecking unaffected declarations; cold and incremental admitted theorem sets, completeness states, and trust ledgers agree | **Partial.** The v2 envelope binds exact build/checker context, normalized declaration identity, source-slice bytes, ordered dependency IDs and payload digest. A collision-backend regression confirms that distinct source slices remain distinct even when both the source digest and outer artifact address collide. A bounded content-addressed store publishes immutable entries atomically and rejects corrupt, oversized, missing, or stale source/dependency entries. An eight-thread same-process race test confirms idempotent concurrent publication converges on one valid immutable entry and removes temporary files; cross-process publication is not tested. Compiler frontend exports no resolved typed artifact bytes; dependency discovery, reverse invalidation and verifier/session reuse remain unimplemented. |
| P-05 | Persist certificates and offer an incremental local session | CLI and local session share admission code; source edits invalidate the affected reverse dependency closure; reused certificates undergo independent checking; restart recovers valid artifacts; canceled requests cannot publish stale results | **Partial.** Fresh-process package replay rejects forged theorem, source-authentication/trust upgrades, identity mismatches, and truncation. Packages still state `source.authenticated: false`; no incremental session, invalidation, cancellation, or generation-safe publication exists. |
| P-06 | Remove dominant replay, AST and fact-management costs | Profile current large successful and refused inputs; improve indexes, term sharing, state liveness and witness reuse. Paired uninstrumented measurements show repeatable improvements with identical semantic outcomes and complete replay | **Partial.** A coherent strict O2 product binds proof source digest `1f273b…`, matching frontend/Stage1 revision `7b27fa…`, and target `arm64-apple-darwin27.0.0`. Balance profiling completed 3/3 with 240/240 replay; the pinned lexer completed with 110/110 replay and zero gaps. Commit `013fa61` inlines parenthesis stripping in the negation candidate scan. Twelve alternating uninstrumented pairs on balance, kernel core and lexer preserved byte-identical full JSON output; medians changed from 74.021 to 72.377 ms on balance, 32.756 to 32.780 ms on kernel core, and 188.268 to 181.972 ms on lexer. The 3.34% lexer reduction had non-overlapping observed ranges; the other inputs were effectively unchanged. The focused contradiction-scan regression passed. A conservative eligibility gate now skips temporary comparison-node construction for non-constant disjunction operands; its focused Boolean/integer/unsigned/constant/chain/indexed denial suites pass. This change has no paired performance measurement yet and is not counted as a measured speedup. A paired scoped-constant boundary fixture confirms that work below the mirrored bounded-model cap proves and an over-budget frame reports `unknown`/`budget`, no model and zero replay gaps. A bounded disjunction-entailment scan now counts only candidates that can match a goal disjunct or are fully refuted; producer and independent replay agree. `scripts/test_disjunction_search_bounds.py` covers irrelevant facts before a late relevant premise, eight/nine exhausted relevant candidates, contradiction by refuted alternatives, a later disjunctive-syllogism proof, and the high-fact pure-call domain regression. The strict O2 pinned build and focused disjunction suite pass with zero replay gaps ([identity and results](docs/evidence/2026-10-05-p06-disjunction-search-bound.md)). No paired timing was taken, so this change is not claimed as a measured speedup. Stack detail is partial at the capture limit, and broader profile-guided speedups remain open. |
| P-07 | Close the largest real-code support bottlenecks using the faster loop | Refresh the census; rank unresolved declarations by root cause and downstream impact; repair summaries, invariants, borrow/region modeling and expression coverage with source-correspondence and negative controls. Record coverage gains and latency together | **Partial.** The six-input census binds proof source `1f273b…`, frontend/Stage1 `7b27fa…`, and binary `ba640c47…`; all inputs were hash-stable. A narrow kernel replay rule now closes the simple conditional fallback disjunction: a fresh strict O2 targeted run proves the repaired obligation with zero gaps while the wrong-guard negative control stays unproved. `Slide.inner` still has two replay gaps at refused roots 48 and 51; the focused investigation records two reverted narrow attempts and preserves the wrong-guard negative control (`docs/evidence/2026-10-05-p07-slide-inner-conditional-gaps.md`). Field equality times out at 120s; kernel comparison and lexer retain unsupported declarations with complete replay for admitted certificates. Broader census refresh and paired latency evidence remain open. |

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
| Compiler reuse | Pinned frontend export, stage1-first build, stage0 provenance checks, recorded build manifests | Preserve coherent product/frontend/runtime identity across concurrent builds and qualify current exact products |
| Kernel | AST-free core, arena validation, typed proposition admission, replay modules | Small core does not imply the entire trusted replay and source-admission path is small or proved |
| Program checking | Contracts, call summaries, scheduling, frames, loops, termination checks | Coverage and source correspondence vary by construct and certificate family |
| Resources | Places, aliases, borrows, regions, sview tracking, resource traces | Exact provenance across some returned calls remains deliberately unsupported |
| Automation | Arithmetic, congruence, bounded reasoning, tactics, bounded repair | Typed arithmetic and independent replay need further consolidation |
| Agent surface | JSON reports, goal/theorem queries, suggestions, scripts, repair, dependency index | Stable protocol evolution, compact state transport, durable proof artifacts, and repair isolation need work |
| Dogfooding | Kernel harnesses, standalone audits, required verified helper declarations | Partial replay coverage is not complete kernel or assistant self-verification |

### 2.2 Known work that must not be hidden by the roadmap

Historical planning snapshot: the repository was dirty at proof HEAD `162bd5d`, with frontend pin `1c948fd4`. This paragraph and the following prior-run findings retain their original context; the 2026-10-05 plan-update inspection found a clean tree at `cd42c89c`. Neither snapshot establishes a current full-suite baseline.

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

**Superseded ordering:** §23 controls the next execution sequence and carries forward unresolved §0A P-00–P-07 gates. BACKLOG.md retains themed completion records; reuse completed work rather than rebuild it. The original ordering follows for reference.

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

## 23. Current high-ROI execution roadmap (2026-10-05)

This section supersedes scheduling in §0, §0A and §20, while preserving their acceptance requirements. It defines **90 ordered work packages**. Order reflects risk removed, breadth of useful verification enabled, and total engineering cost; it is not an invitation to implement every subsystem simultaneously. Finish a small measurable vertical slice and commit it before starting the next. A reproducible false acceptance or memory-corruption defect preempts the queue.

### 23.1 What the next program builds on

The inspected checkout is clean at `cd42c89c`; the local branch is seven commits ahead of its upstream tracking branch. That is an inventory observation, not authorization to push, merge other branches, or publish a release. This documentation update did not rebuild products or run the full proof/compiler matrices.

Recent checked-in gains include source-derived deterministic call-witness replay, an explicitly capped 32-name difference-closure search with boundary/over-bound regressions, and an agent protocol schema gate. Existing work also includes portable packages, report/build identity controls, immutable declaration-artifact envelopes, qualified-constant regressions, scalar-witness indexes, and paired performance harnesses. Extend these foundations. Do not schedule their existence as new deliverables.

During this documentation pass, other work advanced the branch through `239ba817` and modified call-witness replay. Those implementation changes are outside this documentation task and are not validated here. The themed backlog additionally records completed W-01 linear-oracle reconstruction, W-02 symbolic-range rules (with further instance work open), W-03 indexed framing and C-01 bounded difference closure. R-025/R-049/R-057/R-070 extend those capabilities; they must not reopen completed work under new IDs. Before executing any R task, reconcile its scope with current BACKLOG.md evidence and retire already-satisfied subrequirements.

Important remaining gaps are concrete:

- Portable output still emits `source.authenticated: false` in [package_output.elisa](src/app/package_output.elisa). Independent abstract replay and authenticated program correctness are separate capabilities.
- P-04 has artifact envelopes/storage controls, but no completed typed frontend artifact pipeline, semantic dependency discovery, reverse invalidation, or verifier reuse. P-05 has restart/replay tests, not a completed incremental verification session.
- The P-00 historical crash remains unexplained. The exact-current R-001 census completed both historical crash workloads without a crash, while mocap `track` now has 89 replay gaps, including two current `Slide.inner` roots. This does not establish a fix or cause; see [`docs/evidence/2026-10-05-r001-current-census.md`](docs/evidence/2026-10-05-r001-current-census.md).
- Large fact contexts, qualified rewriting, field equality, composed call summaries, and repeated certificate replay need bounded current measurements. Old timeouts and memory captures motivate investigations; they are not measurements of this checkout.
- Protocol validation exists, but its present test helper implements only a small schema-keyword subset. A passing shape check is not validation of every semantic cross-field invariant.
- Coverage is heterogeneous. A successful kernel-core fixture is valuable; it is not a proof of complete kernel soundness, compiler correctness, or every source adapter.
- Trust, source completeness, verdict correctness, proof coverage, latency, and memory must be measured separately. Increasing “proven” counts alone is not the optimization objective.

### 23.2 Work-package contract and priority rules

For every R task below, record: starting commit/toolchain identities; exact supported input class; defect or bottleneck evidence; producer/checker/source responsibilities; implementation files; dependencies; focused positive and adversarial tests; uncached/replay outcomes; timing/memory evidence where relevant; unresolved limitations; and a small completion commit. Proposed features remain planned until this record exists.

The **Change** paragraph describes implementation, and **Gate** describes acceptance. Referenced paths are entry points, not permission to put every new responsibility into those files. Split by responsibility before the 600-line source limit, use private theorem constructors and narrow public APIs, and preserve real Elisa syntax.

Default validation tiers:

1. Documentation-only: reference/inventory checks and diff review; no unnecessary compiler rebuild.
2. Local search optimization: focused proofs/refusals, malformed evidence, exact cached/uncached outcome comparison, portable replay, paired uninstrumented benchmark.
3. Kernel/admission/translation change: rule mutation tests, relevant source/repair/reuse routes, standalone replay, full relevant matrix, dogfood, and required platform evidence.
4. New language semantics: documented model, faithful-source controls, wrong-semantics counterexamples, end-to-end correspondence evidence and explicit unsupported boundaries.
5. Release: exact clean committed products, full required suites on macOS/Linux, current census, dependency/trust inventory, benchmark and incident review.

Dependencies override numeric order when necessary. Independent benchmark/documentation work can proceed while a correctness fix is under investigation, but no optimization is accepted on top of an unclassified outcome difference. Reprioritize using newly measured evidence, preserving task IDs and recording the reason.

### 23.3 Priority band A — proof authority and immediate reliability

These have the highest ROI because every other feature depends on trustworthy outcomes.

#### R-001 — Refresh the exact-current failure and coverage inventory

**Change:** Reuse `scripts/p07_support_census.py`, `scripts/p01_baseline.py`, and current refusal tests to classify every known P-00/P-07 failure against one immutable product. Include historical qualified rewrites, field equality, conditional-return gaps, composed summaries, difference-closure limits, and representative real projects. Record complete obligations, not only successful certificates.

**Gate:** Every input has a complete report or explicit crash/timeout/memory-limit record; manifests match inputs and binaries. Produce a tracked compact census with no assertion that historical findings are current without reproduction. Depends on coherent existing build provenance.

**Status:** Six-input gate met. The strict O2 product and all input hashes are recorded in [`docs/evidence/2026-10-05-r001-current-census.md`](docs/evidence/2026-10-05-r001-current-census.md), alongside complete report digests or the explicit field-equality timeout, changed-versus-prior outcomes, and focused qualified-rewrite, conditional-return, composed-summary, and difference-closure controls. P-00 cause analysis and the current P-07 replay/support limits remain open.

#### R-002 — Close or contain the historical qualified-rewrite corruption

**Change:** Carry P-00 forward using the retained crashing binary and minimized qualified-constant cases. Compare generated append/index code, array/store lifetime behavior, and source history with current controls. If a causative compiler defect is established, fix the compiler and add differential cases; otherwise document exactly why the cause remains unresolved.

**Gate:** Source-level explanation and minimized responsible regression, or explicit unresolved incident with affected product identities. Crash disappearance alone cannot mark this done. Require O0/O2 and stage0/stage1 controls plus Linux qualification for a confirmed fix.

**Progress (2026-10-05):** The exact 51-byte reproducer (SHA-256 `3cf171b7…fd94ea2`) passes on
the current strict O2 Stage1 proof product `6502ec0e…ccde64` (proof revision `e9d27ef6`) with a
complete report and independent replay, while retained product `74f49810…789658a` still crashes
before producing JSON. The retained product was built from dirty proof/compiler trees and is not
the unavailable originally measured binary `d734fd75…`; current success does not identify a fix.
The crash trace localizes an invalid generated indexed store in
`proof_qualified_body_rewrite`, but the cause remains unresolved and Linux is untested. Exact
inputs, manifests, controls, and limits are recorded in
[`docs/evidence/2026-10-05-p00-exact-current-recheck.md`](docs/evidence/2026-10-05-p00-exact-current-recheck.md)
and [`docs/evidence/2026-10-05-p00-qualified-crash-cause-audit.md`](docs/evidence/2026-10-05-p00-qualified-crash-cause-audit.md).
R-002 remains open pending reconstructable historical source/product evidence or an isolated
source-level cause and qualified regression.

#### R-003 — Eliminate known producer/replay disagreements

**Change:** Reproduce remaining `Slide.inner` conditional roots and any new census gaps; trace exact formation, branch premises, arithmetic type witnesses and conclusion evidence. Extend the smallest justified inference or stop the producer from advertising unsupported evidence. Reuse conditional replay modules rather than adding a blanket acceptance fallback.

**Gate:** Original valid roots independently replay; wrong guards, missing conjuncts, overflow-sensitive variants and forged branch certificates refuse. A conservative refusal can contain the defect but must remain listed as a capability gap until useful proof is restored.

#### R-004 — Make whole-program admission completeness structural

**Change:** Audit `certificate_admission.elisa`, report aggregation and declaration scheduling for paths where missing bodies, skipped branches, unsupported nodes, semantic errors or truncated checks disappear from the verdict. Represent expected obligation inventory and completed checks explicitly; tie each exported theorem to a checked root.

**Gate:** Deleting an obligation, changing counts, omitting a declaration, introducing an unreachable unsupported operation or failing an imported dependency cannot yield unconditional program `proved`. Coverage and certificate counts remain explanatory data, not theorem authority.

#### R-005 — Audit source-derived boundary facts and call witnesses

**Change:** Extend the recent source-derived witness work in `check/function_contracts_and_frames.elisa` and `replay/boundary_trace_shapes.elisa`. Inventory initial facts about parameter types, ranges, calls, aliases, effects and resources; replay exact owner, argument position, state version and declaration identity instead of trusting producer bookkeeping.

**Gate:** Swapped arguments, similarly named modules, changed contracts, stale pre-call facts, forged origins and substituted alias targets refuse. Document each remaining adapter-trusted fact. Zero replay gaps must not conceal an unjustified source premise.

**Progress (2026-10-05):** Replay now rejects a deterministic-call trace whose scalar call contains a
reference actual hidden under parentheses; `examples/deterministic_call_trace_replay_runtime.elisa`
mutates the in-memory trace and confirms refusal, then restores and replays the original. Exact
call-site binding to the source owner/line and argument state version remains open, as do the wider
parameter/range/alias/resource boundary inventory and the rest of this gate.

#### R-006 — Exhaustively harden all certificate/package decoders

**Change:** Inventory raw integer IDs, node arities, child spans, enums, textual markers and version dispatch in `src/portable/`, `src/proof/kernel_replay/` and admission. Check sizes before allocation, arithmetic before index use, duplicate IDs and DAG cycles. Make decode failure distinct from a valid empty proof.

**Gate:** Truncation, overflow lengths, cyclic terms, unknown tags, invalid UTF-8 policy, malformed Boolean payloads and incompatible versions produce bounded structured rejection. Fuzz parser and checker together; retain minimized failures.

**Progress (2026-10-05):** A source audit of the portable replay path found existing caps and checks
for package file size, exact object schemas (including duplicate keys), numeric encodings, copied
node strings, node/child/theorem/hypothesis counts, identity bytes, node shapes, child spans,
cycles, forward references, theorem roots and rule dispatch. Existing focused tests include those
malformed shapes and selected count limits. The inventory note
`docs/evidence/2026-10-05-r006-decoder-boundary-inventory.md` records the source inventory. A
follow-up raw-byte probe reproduced acceptance of malformed UTF-8 in a theorem label; the reader
now validates bounded input bytes before JSON parsing and decoded package strings before use. Six
invalid UTF-8 sequences and six malformed header-Boolean types return structured refusals. The
integrated root snapshot also passed the strict pinned O2 build, `scripts/test_portable_replay.py`,
`scripts/tests/test_portable_package_string_budget.py`, and `scripts/test_p05_package_restart.py`;
the exact replay product identity is recorded in the cross-check note. The broad decoder/ID
inventory, parser/checker fuzzing, escaped
surrogate and malformed kernel-Boolean cases, systematic boundary matrix, parser-resource tests
and worst-case memory evidence remain open, so R-006 is not complete.

#### R-007 — Freeze typed contexts and control assumption discharge

**Change:** Establish immutable/versioned checked environments, distinct binder IDs, capture-avoiding substitution and exact context membership. Audit branches and tactics for leaked assumptions, reused scratch handles and mutation after checking. Share term storage only under explicit lifetime and context rules.

**Gate:** Escaping eigenvariables, alpha-renaming collisions, sibling contamination, shadowed names, stale context IDs and post-validation mutation cannot manufacture a theorem. Positive nested quantifier and branch proofs preserve their valid behavior.

**Progress (2026-10-05):** A narrow pinned O2 audit of quantifier substitution and two branch controls found that substitution refuses when capture-avoiding rewriting would cross a differently named nested binder, dictionary binders use marker-based simultaneous substitution, and disjunctive branches receive separate fact arrays. The focused symbolic-quantifier, variant-exclusion and conditional-ensure tests passed. This does not test post-validation arena mutation, scratch-handle reuse, escaping eigenvariables, distinct binder IDs or exact/stale context identity; R-007 remains open. Details and build identity are in `docs/evidence/2026-10-05-r007-quantifier-boundary-audit.md`.

#### R-008 — Establish a complete trusted-rule/dependency register

**Change:** Link each inference family, specialized arithmetic/resource checker and source-adapter premise to implementation, specification, tests and trusted assumptions. Inventory all theorem-construction paths and keep checked theorem constructors private. Distinguish logical axioms, source correspondence, compiler/runtime trust and environment assumptions.

**Gate:** Every admitted root exposes its transitive trust dependencies; no solver or tactic success enters as an unlabeled axiom. Review specialized checkers as TCB even when outside `kernel_core.elisa`.

**Progress (2026-10-05):** The starting register in
`docs/evidence/2026-10-05-r008-trust-register.md` maps the visible logical, resource, effect,
structural, tactic and portable-package admission paths and records their current trust labels and
focused test sources. It is source inspection only: construction call sites are not exhaustive and
no complete transitive root-to-source/compiler/runtime dependency graph or rule soundness map is
established. R-008 remains open.

#### R-009 — Automate soundness-incident and artifact invalidation policy

**Change:** Version rule semantics and source-admission identities; introduce a documented affected-version registry and cache/package refusal or mandatory-replay policy. Preserve reproducer, exact product, trust boundary and downstream theorem impact for every confirmed incident. Reuse existing identity controls.

**Gate:** An artifact generated by an affected rule cannot silently retain an unconditional verified label after a fix. Test old/new package handling and dependency cascades; semantic migrations remain separate from cosmetic format changes.

**Progress (2026-10-05):** Source review found existing report-cache keys bound to included inputs,
the exact executable, target, relevant environment and cache recipes; declaration artifacts bind
to the current build context, source slice, payload and dependencies; portable theorem packages
are independently replayed and label source trust as adapter-supplied. The audit in
`docs/evidence/2026-10-05-r009-invalidation-policy-audit.md` records focused test sources and
three passing host-side cache/artifact identity checks; those checks use synthetic identities and
do not validate a compiled proof product or package migration. No complete confirmed-incident/
version registry or old/new semantic migration policy was found, so R-009 remains partial.

### 23.4 Priority band B — bounded work and usable performance evidence

Start after immediate false acceptance/corruption containment. The goal is predictable cost before adding broader search.

#### R-010 — Instrument end-to-end phase and work counters

**Change:** Add lightweight measurements around import, parse, semantic checks, scheduling, VC generation, search, certificate construction, replay and serialization. Coordinate a genuine monotonic clock API with compiler/runtime support; do not infer internal duration by subtracting unrelated wall times. Expose counts even where phase timers are unavailable.

**Gate:** Disabled instrumentation has measured negligible cost; nested phases do not double-count exclusive time. Counter totals agree with workload inventory. Clock failures cannot alter proof outcomes.

**Progress (2026-10-05):** A source-level report inventory maps existing counters and their limited origins across import, lex/parse, semantic checks, scheduling, VC generation, search, certificate construction, replay, and serialization. The CLI exposes artifact/workload counts, selected return-analysis and goal-cache counters, kernel arena counts, output bytes, and replay outcomes; it has no internal monotonic clock or complete phase-work totals. P-01 external process wall/CPU/RSS and Python JSON-decode time remain harness measurements. No internal durations were inferred and no ambiguous counter was added. Instrumentation overhead and phase-work consistency gates remain unverified; see [`docs/evidence/2026-10-05-r010-measurement-coverage.md`](docs/evidence/2026-10-05-r010-measurement-coverage.md). R-010 remains open.

#### R-011 — Establish versioned performance and coverage sentinels

**Change:** Extend existing P-01 and paired benchmark harnesses with tiny interactive goals, successful/refused symbolic quantifiers, kernel core, field equality, composed calls, resource-heavy modules and adversarial fact growth. Keep inputs and semantic expected outcomes independently versioned.

**Gate:** At least seven alternating paired rounds after warm-up for claims; report median/p95, CPU, peak RSS, proof bytes, obligations and replay. Timeouts remain censored outcomes, not successful timings. Include cold/no-op/edit and portable-replay costs.

**Progress (2026-10-05):** P-01 now has an independently versioned workload contract in [`scripts/p01_sentinels.json`](scripts/p01_sentinels.json): six existing fixtures are pinned by path, size and SHA-256 with expected proof/refusal outcomes. The runner rejects fixture-set, path or content drift before measurement and consumes the manifest's semantic outcomes. Focused harness validation passed (`python3 scripts/test_p01_baseline.py`); no `build/elisa-proof` exists in this checkout, so this is not a fresh product or timing baseline. R-011 remains open: additional workload classes (field equality, composed calls, resource-heavy modules and fact-growth scaling), paired benchmark expansion, and seven-round evidence are outstanding. See [`docs/evidence/2026-10-05-r011-p01-sentinel.md`](docs/evidence/2026-10-05-r011-p01-sentinel.md).

#### R-012 — Account for actual search work with named budgets

**Change:** Replace ad hoc depth-only containment with explicit counters for visited nodes, fact scans, comparisons, rewrites, branch candidates, substitutions and allocated scratch bytes. Centralize named limits and checked arithmetic. Keep search budgets distinct from certificate replay/decoding limits.

**Gate:** Budget exhaustion returns a precise stage/dimension/observed/limit with no partial theorem. Boundary and one-over tests include the current 32-name difference closure. Accepted proofs replay within independent checker bounds.

#### R-013 — Remove fact-count-dependent denial-of-service shapes

**Change:** Benchmark repeated tautologies, irrelevant disjunctions, wide equality graphs and nested pure summaries across increasing sizes. Identify superlinear scans before changing algorithms. Retain `bounded_model_work_budget.elisa` as intentional stress data and add logically rich variants that exercise the same dimensions.

**Gate:** Publish scaling curves and expected asymptotic work counters; beyond configured bounds the system terminates predictably. Do not eliminate stress coverage by simplifying away all duplicated facts before their relevant cost boundary is exercised.

#### R-014 — Make allocation lifecycle observable

**Change:** Integrate optimized allocation-site/lifetime captures from the Elisa profiler and compiler tools; distinguish reserved arena capacity, committed memory, live nodes, dead retained nodes and process RSS. Attribute by stable source identity and store generation. Correlate captures with search phases.

**Gate:** Known allocation/reclamation probes produce expected counts and high-water marks; dropped events and truncated captures are explicit. Instrumented proof output agrees with uninstrumented output. Never count instrumentation overhead as target cost.

#### R-015 — Isolate builds, products and evidence snapshots

**Change:** Ensure concurrent work uses immutable source exports, separate product paths and atomic manifests. Keep frontend revision, compiler product, runtime object, ABI, optimization mode and recipes coherent. Preserve exact measured executables when investigating regressions.

**Gate:** Concurrent builds cannot overwrite the binary named by another run; source mutation during preparation fails or restarts explicitly. Stage1 freshness is checked, stage0 fallback is labeled and validated, and no stale-product bypass is the normal workflow.

#### R-016 — Bound reporting and diagnostic materialization

**Change:** Separate compact verdict/trust/repair summaries from opt-in full facts and AST dumps. Stream diagnostics or serialize interned references with explicit ownership; preserve complete authoritative obligation inventory and certificate export. Record serialization bytes and retained report memory.

**Gate:** Compact and full routes agree on conclusions, assumptions, unresolved goals and replay. Large refusal reports stay bounded without silently truncating proof-critical data. Optional presentation truncation has an explicit marker and retrieval path.

#### R-017 — Set ratcheted, workload-specific performance gates

**Change:** Once R-011 provides a baseline, set reviewed ceilings for interactive p95, batch throughput, replay latency and peak memory. First aim for at least 30% lower peak live allocation on the largest measured workload and 20% lower dominant-phase CPU where a profile identifies removable repeated work; these are targets, not claimed gains.

**Gate:** No accepted speedup changes admitted conclusions or trust. Treat small changes within variance as inconclusive. Pause an optimization after two bounded failed experiments and reassess evidence rather than indefinitely expanding budgets.

#### R-018 — Reduce compile/test iteration overhead safely

**Change:** Finish P-03: closure-specific keys, unchanged snapshot preservation, checksum-validated output reuse, targeted suite dependency maps and one build of each required product per run. Keep full matrices available and required for release. Cache negative decisions only with complete context.

**Gate:** Comment-only and unrelated-file edits avoid unnecessary work while relevant dependency/runtime/flag changes force it. Corrupt outputs trigger rebuild. Publish actual no-op cost, not only compiler cache-hit time.

### 23.5 Priority band C — remove repeated work in the current engine

R-010–R-014 identify which items have the greatest payoff; reorder within this band using measurements.

#### R-019 — Build reusable, checked fact-frame indexes

**Change:** Extend existing scalar-witness indexes with exact complement, equality, integer width/domain, disjunction and declaration-identity indexes. Build once per immutable frame; add parent/delta views for branches. Keep ordered candidate traversal where current bounded search behavior depends on order.

**Gate:** Indexed and scan implementations agree on a differential corpus including malformed markers and collisions. Demonstrate reduced scans and allocation on fact-heavy workloads. Index membership alone never establishes an unvalidated fact.

#### R-020 — Introduce bounded canonical term sharing

**Change:** Intern immutable typed terms using structural equality after hash lookup. Include sort, width, binder/declaration identity, effects and context-dependent metadata in keys. Begin with high-frequency leaf/operator forms; avoid whole-AST replacement before a measured pilot.

**Gate:** Forced hash collisions cannot merge distinct terms; store-generation mismatches reject. Measure construction cost, retained nodes and equality calls. Sharing cannot make source handles escape regions.

#### R-021 — Use persistent branch contexts with cheap deltas

**Change:** Replace full hypothesis copies with immutable parent frames and small additions/removals; explicitly model invalidated mutable-place facts. Flatten only where measured necessary. Track proof dependencies rather than retaining every historical frame.

**Gate:** Nested cases, failed siblings, loops and writes preserve exact logical state. Branch memory scales with changed facts rather than all ancestor facts; no lost provenance or cross-branch assumption leakage.

#### R-022 — Cache normalization and substitution by semantic identity

**Change:** Memoize normalization, qualified-constant resolution, typed substitution and pure-definition unfolding using complete context/version keys. Preserve cycle detection and budget accounting. Bound retention by session/declaration lifetime and expose hits/misses.

**Gate:** Changed overloads, regions, parameter types, float mode or definitions invalidate entries. Cached/uncached results match; rejected or partially normalized terms cannot acquire a valid normal form.

#### R-023 — Replace repeated equality scans with proof-producing congruence

**Change:** Build congruence classes for the supported pure typed term subset, emitting explicit equality paths and constructor applications. Keep overloaded/effectful operations outside unless their semantics are witnessed. Index projections and disequalities for common record/ADT goals.

**Gate:** Independent replay checks every equality edge; arbitrary calls with identical spelling do not become congruent. Benchmark field equality and repeated equality-frame goals, including wrong-field and changed-state negatives.

#### R-024 — Make disjunction search relevant and predictably bounded

**Change:** Profile current relevant-disjunction selection; index exact atoms and known refutations before semantic equality. Separate candidate selection from proof evidence, reuse scalar witnesses and track actual work. Preserve late relevant premises and useful disjunctive syllogisms.

**Gate:** Existing disjunction bound/domain/float controls pass; all alternatives needed by a proof are checked. Coarse fact truncation that loses valid proofs is not a completed optimization. Publish paired CPU/RSS evidence.

#### R-025 — Represent arithmetic evidence as sparse proof objects

**Change:** In linear and difference-constraint modules, use sparse coefficients, indexed variables and explicit derivation edges. Avoid materializing dense closure where a bounded shortest-path or focused contradiction witness suffices. Keep width/wrap preconditions attached.

**Gate:** Exact arithmetic checker validates every combination/path; minimum-integer and overflow cases remain conservative. Preserve the 32-name contract until a separately reviewed semantics/budget change justifies widening it.

#### R-026 — Reclaim scratch and obligation-local state promptly

**Change:** Partition immutable shared terms from ephemeral rewrite/search arrays, branch witnesses and diagnostic buffers. Introduce clear region ownership per declaration/obligation and release scratch after certificate compaction. Measure retained capacity and live high-water marks.

**Gate:** Returned certificates contain no dangling borrowed handles or views; sview lifetime rules remain valid. Repeated checking of the same file does not monotonically grow retained live state. Use compiler/debugger lifetime diagnostics when failures expose language gaps.

#### R-027 — Make replay linear in checked evidence where practical

**Change:** Replace rediscovery of producer search with explicit witnesses for candidate choices, arithmetic paths, substitutions and branch splits. Share checked proof-DAG nodes with immutable typed contexts; replay each node once per exact context. Keep source formation and boundary checks.

**Gate:** Removing or changing witness steps rejects even when search could independently find another proof. Portable replay needs no AI/solver/search engine. Publish replay work versus DAG nodes and quantify residual nonlinear checks.

### 23.6 Priority band D — incremental artifacts and local interaction

This is a major ROI multiplier for development, proof repair and AI workflows; it requires exact identities, not trusted cached verdicts.

#### R-028 — Export immutable typed frontend artifacts

**Change:** Coordinate compiler artifacts containing resolved declarations, instantiated types/operators, source maps and relevant semantic options. Reuse `scripts/declaration_artifact_identity.py` envelopes; distinguish syntax artifacts from checked semantic artifacts. Define versioned canonical encoding.

**Gate:** Cold reconstruction and exported artifacts agree on admitted declarations and diagnostics. Malformed/stale artifacts fail closed. No raw AST/store pointer survives process boundaries.

#### R-029 — Record complete semantic dependency edges

**Change:** Discover dependencies on bodies when unfolded, summaries, types, constants, field defaults, operators, imports, negative resolution results, effects, regions and termination. Preserve ordered fact/definition inputs where required. Make dependency capture a first-class verifier result.

**Gate:** Mutation tests for every dependency class invalidate consumers; adding a previously absent declaration also invalidates failed resolution. Missing dependencies cannot masquerade as independent proofs.

#### R-030 — Implement reverse invalidation and SCC scheduling

**Change:** Maintain reverse edges and schedule recursive components atomically; separate syntactic/body edits from changed verified summaries. Reuse unaffected declarations only through recorded dependencies and checked identities. Explain each invalidation reason.

**Gate:** Cold and incremental theorem sets, trust ledgers and completeness match after edit sequences. Mutual recursion, deleted definitions, contract strengthening/weakening and module renames have targeted controls.

#### R-031 — Persist replayable certificate artifacts

**Change:** Store proof DAGs, exact contexts, source/IR correspondence references and complete dependency identities alongside immutable artifact envelopes. Separate heuristic search caches from admitted evidence. Validate disk entries before use and independently replay after reload. Add an authenticated program-package mode only when checked correspondence binds exact source bytes, typed IR, semantics and declaration roots; retain abstract/adaptor-trusted mode explicitly until then.

**Gate:** Forged `verified` fields, truncated nodes, corrupt payloads, changed contracts and mismatched targets reject. Replacing source while preserving abstract proof terms cannot authenticate the new program; a source digest by itself is not correspondence evidence. Restart recovers only currently valid checked artifacts; eviction affects speed, not correctness.

#### R-032 — Implement a generation-safe local verification session

**Change:** Retain frontend and checked declaration state in a local process with immutable snapshot generations. Route inspect/prove/repair/export through one admission path. Cancellation stops work and prevents old requests from publishing into a newer source generation.

**Gate:** Concurrent edits, cancellation, restart and out-of-order replies cannot expose stale proofs as current. CLI remains functional independently; no network or AI dependency enters the common path.

#### R-033 — Distinguish semantic identity from presentation identity

**Change:** Separate normalized declaration identity, source-byte authentication and span maps. Permit location remapping after whitespace/comments where semantics are unchanged; regenerate source-correspondence bindings as required instead of pretending bytes are identical.

**Gate:** Comment edits reuse semantic proof work without stale locations or false source authentication. Changes to contracts, literal spelling with changed meaning or compiler options invalidate appropriate artifacts.

#### R-034 — Harden cross-process cache publication and eviction

**Change:** Extend the existing eight-thread publication test to multiple processes, interrupted writers, competing generations and bounded storage. Use atomic immutable publication, verified reads, deterministic eviction policy and explicit miss reasons.

**Gate:** No partial entry is visible; losing a publication race cannot replace newer evidence. Cache misses/corruption reduce performance only. Test disk-full, permission failure and interrupted rename behavior.

#### R-035 — Add dependency-aware selective replay

**Change:** Retain checked dependency DAGs inside a session and invalidate precisely affected nodes. Across process/revision boundaries start with full independent replay; reduce repeated replay only under documented immutable-context invariants.

**Gate:** Changing one dependency invalidates all and only its true consumers. Replay-cache state cannot skip formation, source binding, assumption accounting or rule-version checks.

#### R-036 — Add resource-aware parallel declaration checking

**Change:** Schedule independent declarations/SCCs with memory-aware worker limits, separate arenas and deterministic result ordering. Parallelize frontend/build orchestration separately from kernel internals. Keep opt-in concurrency until measurements support a safe default.

**Gate:** Serial/parallel outputs and trust agree across repeated runs; cancellation and failures are isolated. Publish throughput and peak aggregate RSS; more workers must not recreate out-of-memory failures.

### 23.7 Priority band E — faithful source semantics and modular verification

Prioritize constructs appearing in the current census over speculative language coverage.

#### R-037 — Make typed verification IR the source-model boundary

**Change:** Define a compact immutable IR for already supported expressions, state updates, branches, calls and exceptional exits. Preserve resolved operators, target widths, source spans and effect/resource transitions. Pilot one existing checker path before expanding.

**Gate:** IR/source execution correspondence is documented and tested; unsupported AST constructs remain explicit. Kernel replay checks IR evidence independently of mutable compiler AST rewrites.

#### R-038 — Consolidate weakest-precondition generation

**Change:** Express assignment, sequence, branches and returns through reusable WP rules over versioned state. Reuse current contracts/return checking while eliminating duplicated substitutions. Make partial correctness and total correctness distinct judgments.

**Gate:** Missing branch paths, incorrect assignment substitution, early return and unreachable unsafe operations cannot disappear. Small exhaustive interpreters cross-check generated obligations for bounded programs.

#### R-039 — Verify modular summaries and exact call substitution

**Change:** Cache verified summaries for pure/effectful callees, binding generics, argument identities, frames and exceptional postconditions. Record when bodies are unfolded versus contracts consumed. Improve composed-call cases without replacing missing summaries with opaque truths.

**Gate:** Wrong-argument, unverified-callee, alias-changing and stale-contract controls refuse. Composition benchmarks prove useful valid contracts with complete replay and measured bounded memory.

#### R-040 — Expand loops through inductive invariants

**Change:** Check initiation, preservation and exit reasoning for explicit invariants; model break/continue and modified places. Add untrusted invariant suggestions using ranges and branch facts, requiring ordinary proof obligations for each candidate.

**Gate:** Off-by-one, omitted updates, nonpreserved resources and invalid exit conditions reject. Valid traversal/search loops verify without bounded unrolling being reported as unbounded proof.

#### R-041 — Establish termination and recursion summaries

**Change:** Add checked structural descent and lexicographic/measure decrease for representative recursive functions and SCCs. Distinguish potentially diverging program functions from total logical definitions. Carry termination requirements into unfolding and theorem use.

**Gate:** Nondecreasing recursion, negative unbounded measures, cyclic summary justification and mutually recursive loopholes refuse. Useful list/tree algorithms obtain independent decrease evidence.

#### R-042 — Complete machine-integer operation semantics

**Change:** Specify and implement signed/unsigned arithmetic, casts, comparisons, division/remainder, shifts and bitwise operations for each supported width and target-sized type. Separate mathematical integers from machine values; attach wrap/overflow facts explicitly.

**Gate:** Boundary matrix includes min/max, high-bit unsigned, divide-by-zero, signed-min division, invalid shifts and narrowing. Source, tactic, repair and portable replay agree; no heuristic reinterpretation via `i64`.

#### R-043 — Make float/string/character boundaries explicit

**Change:** Preserve existing conservative float rules while defining which IEEE operations, NaNs, signed zeros, infinities and rounding modes are supported. Separately model string bytes/characters, indexing and cstr termination according to Elisa semantics.

**Gate:** No total-order inference on unwitnessed floats; no string-length/encoding conflation or unterminated cstr assumption. Start with high-use decidable operations rather than a broad incomplete numeric model.

#### R-044 — Verify collections through abstract models and frames

**Change:** Give arrays, darrays, dictionaries and slices precise models for length, lookup, update, allocation/reallocation and errors. Relate representation operations to model transitions. Reuse current push/pop/indexed-write checks and preserve ownership-bearing value distinctions.

**Gate:** Bounds, aliasing, moved backing storage, reallocation-invalidated views, missing-key and mutation cases refuse correctly. Valid parser/buffer loops gain reusable collection lemmas.

#### R-045 — Define foreign/unsafe/low-level proof boundaries

**Change:** Isolate FFI, pointers, native callbacks and low-level memory primitives with explicit contracts, ABI identities and unsafe assumptions. Validate source admission does not silently convert unsupported operations into pure terms. Verify selected runtime primitives incrementally.

**Gate:** A program using unchecked foreign assumptions is labeled conditional, not unconditional. Target/ABI mismatches and missing contracts reject; compiler differential execution is evidence, not a proof of semantic correspondence.

### 23.8 Priority band F — ownership, regions and effects

Build on existing tracking rather than importing an unrelated permission model wholesale.

#### R-046 — Canonicalize places and alias/state identities

**Change:** Define stable root/projection/index paths with checked alias relations and state epochs; normalize forwarded by-reference parameters and tracked caller places. Carry exact place witnesses across summaries and frames.

**Gate:** Forwarded references verify when justified; overlapping unknown indexes, stale versions and similarly named places cannot share ownership facts. Recheck the historical indexed-frame failure before marking it current.

#### R-047 — Preserve view backing storage and region lifetimes

**Change:** Complete sview/slice/reference provenance through wrapper calls, returns, fields and containers. A view must reference valid backing storage for its entire live region; empty views need a valid documented representation, not an optional-invalid-pointer shortcut.

**Gate:** Wrong backing argument, freed/reallocated owner, shorter returned region and hidden field escape refuse. Valid long-lived views and returned borrowing wrappers verify. Compiler region rules and proof models must agree.

#### R-048 — Check quantitative ownership/resource conservation

**Change:** Define affine/linear consumption and transfer rules over existing resource traces. Track split/join conservation, moves, borrowing and destruction; introduce fractional read permissions only for actual shared-read proof requirements.

**Gate:** Duplication, double release, use-after-move, invented fractions and forgotten resources cannot prove. Resource accounting remains explicit across branches and summary calls.

#### R-049 — Make framing proof-producing and footprint-aware

**Change:** Represent callee read/write/allocate/free footprints and prove disjoint preserved state. Support exact indexed places and conditional alias constraints. Make unknown footprints an unresolved permission obligation rather than assuming preservation.

**Gate:** Valid nonoverlapping updates frame automatically; overlapping writes, opaque forwarded targets and allocation invalidation require evidence or refuse. Independent replay checks the footprint relation.

#### R-050 — Verify region allocation and value/reference boundaries

**Change:** Audit `new[r]` as allocation into `@r`, store ownership and automatic reference reading under actual language rules. Connect allocation witnesses to region lifetimes and ownership-bearing collection semantics; fix compiler representation gaps with minimized cases.

**Gate:** Valid reference allocation compiles/proves, while pointer-as-owned-value and region escapes reject at the responsible boundary. Do not introduce a nonexistent dereference operator.

#### R-051 — Model effects and handler transitions compositionally

**Change:** Preserve resolved effect identities, capability requirements and handler state in IR and summaries. Separate specification-only effects from executable effects; model handler resume/discontinue behavior only for a documented supported subset.

**Gate:** Missing effects, fabricated purity, incorrect handler state and capability leakage refuse. Valid effect restrictions compose across module boundaries.

#### R-052 — Verify errors, cleanup and exceptional postconditions

**Change:** Model error returns/throws, early cleanup and resource release on every exit. Add exceptional summaries with exact state/resource obligations; connect them to WP generation and caller reasoning.

**Gate:** A correct normal return cannot hide a leaking or invalid exceptional path. Valid cleanup wrappers and fallible collection/parser operations verify on all documented exits.

#### R-053 — Support checked ghost state and stable invariants

**Change:** Introduce proof-only values and ghost transitions with erasure/noninterference rules. Tie struct/module invariants to construction, mutation and ownership transfer; keep ghost authority distinct from executable mutable state.

**Gate:** Ghost state cannot affect runtime behavior or fabricate physical resources. Broken invariant transitions refuse; independently checked ghost lemmas support useful protocol/data-structure specifications.

#### R-054 — Grow a reusable resource/effect specification library

**Change:** Package contracts and proved lemmas for views, indexed updates, buffers, builders, cleanup and capability wrappers. Provide examples that expose assumptions and exact footprints; keep model definitions versioned.

**Gate:** Library use reduces repeated obligations/annotation cost on two real programs with no trust increase. Mutation controls break proofs at the relevant library dependency, not unrelated declarations.

### 23.9 Priority band G — expressive reusable mathematics

This delivers broad verification power without requiring dependent types in Elisa.

#### R-055 — Admit checked ADT declarations and eliminators

**Change:** Specify constructors, injectivity, distinctness and exhaustive case analysis for the supported inductive subset. Check positivity/well-founded declaration requirements; bind constructor identities to resolved types.

**Gate:** Empty/recursive malformed declarations cannot imply arbitrary propositions. Valid option/result/list/tree cases replay; forged constructors and wrong type parameters reject.

#### R-056 — Implement induction with explicit motives and hypotheses

**Change:** Add structural induction proof terms for admitted ADTs and natural-number measures. Validate motive formation, each constructor case and permitted induction hypotheses. Keep recursive program correctness tied to termination/summaries.

**Gate:** Invalid induction hypotheses, skipped cases and circular self-use refuse. Prove useful list length, tree traversal and parser-consumption properties independently.

#### R-057 — Expand quantifiers with disciplined scoping

**Change:** Implement exact introduction/elimination and typed instantiation witnesses; add indexed untrusted trigger/search selection with budgets. Reuse existing symbolic-quantifier checks and cache only under complete binder/context identities.

**Gate:** Eigenvariable escapes, ill-typed instances, capture and inconsistent witness markers reject. Quantified replay avoids rediscovering search and remains bounded on hostile inputs.

#### R-058 — Introduce terminating, proof-producing simplification

**Change:** Maintain versioned rewrite sets with proved equalities, orientation policies and termination/fuel controls. Separate definitional reduction from theorem rewriting; preserve source operator/effect constraints.

**Gate:** Every rewrite replays, cycles terminate as unknown, and conditional rules require premises. Show reduced proof/search cost on a fixed corpus without stronger trust.

#### R-059 — Provide useful polymorphism and modular theorem namespaces

**Change:** Bind type parameters and module-qualified theorem names explicitly; instantiate reusable lemmas without display-name lookup. Define public/private theorem boundaries and export only checked declarations.

**Gate:** Wrong generic arguments, hidden/private declarations and namespace collisions reject. Human proofs reuse one library theorem across multiple concrete supported types.

#### R-060 — Add extensional reasoning only through explicit rules

**Change:** Identify actual needs for function, array/map or record extensionality; formalize each rule or mark its axiom dependency. Prefer finite/indexed equality witnesses where sufficient. Never infer equality from pretty-print coincidence.

**Gate:** Missing domain cases and side-effectful function comparisons refuse. Any classical/extensional axiom appears transitively in the theorem ledger.

#### R-061 — Build arithmetic/order and data-structure lemma libraries

**Change:** Prove reusable order, interval, divisibility, length, lookup/update and sequence lemmas under exact numeric models. Attach simplifier eligibility and dependency identities; separate machine and mathematical statements.

**Gate:** Libraries close recurring census obligations with smaller certificates and fewer scans. Wrong-width and off-by-one variants fail using the same interface.

#### R-062 — Add lightweight refinements and specification ergonomics

**Change:** Support checked range/nonzero/index/state predicates on existing types, with generated introduction/use obligations. Keep runtime representation unchanged and distinguish inferred suggestions from validated refinements.

**Gate:** A refinement cannot be attached to an unchecked value or survive an invalidating write. Measure annotations removed and added proof cost on practical code.

#### R-063 — Support specification abstractions and verified module interfaces

**Change:** Hide representations behind abstract models, verified contracts and exported lemmas; define how clients depend on interface versus body. Integrate with incremental summary identity and explicit trust.

**Gate:** Representation changes preserve client proofs only when interface obligations remain checked. Abstract types cannot export contradictory axioms disguised as implementation contracts.

### 23.10 Priority band H — automation and human/agent workflows

Keep every proposed result untrusted until ordinary admission; optimize the common deterministic path first.

#### R-064 — Expose a strict versioned goal/query protocol

**Change:** Extend current v1/v2 schema work to goals, facts, definitions, dependencies, attempts and repair commands. Validate full required schema semantics and cross-field relationships; preserve compatibility intentionally.

**Gate:** Missing required fields, invalid nested arrays, inconsistent replay/count fields and unsupported versions are rejected by protocol tests. Deterministic IDs and ordering survive repeated runs; unknown fields have a specified compatibility policy.

#### R-065 — Provide compact session-based state transport

**Change:** Send canonical goal/context IDs and deltas instead of full AST/fact dumps for every agent query. Expose paginated exact retrieval and stable snapshot generation. Reuse R-032 rather than adding another verifier service.

**Gate:** Reconstructed contexts equal full reports; stale generations reject commands. Measure bytes and latency per inspect/repair cycle without hiding unresolved goals or trust.

#### R-066 — Make proof text round-trip into checked proof terms

**Change:** Extend current Elisa-like proof rendering into a parser/elaborator for supported human steps: given/show, apply, cases, rewrite, instantiate and explicit subgoals. Keep elaboration outside the kernel and render checked evidence faithfully.

**Gate:** Exported proofs replay after editing/reimport without AI. Ambiguous names, missing steps and incomplete proofs stay open; printed `qed` follows admission only.

#### R-067 — Add deterministic lemma discovery and ranking

**Change:** Index proved theorem conclusions by typed symbols, shapes and required premises. Rank cheaply by exact applicability, dependency availability and expected proof cost before broad search. Expose why a lemma applies or fails.

**Gate:** Discovery never imports unchecked summaries. Measure recall/latency on held-out real goals; similarly spelled but incompatible declarations stay distinct.

#### R-068 — Report precise failed premises and search attempts

**Change:** Record actual tier/candidate/budget trace instead of relying solely on post-hoc refusal classification. Return smallest identified unmet premises, dependencies, resource/effect requirements and attempted engines; label unknown explanations honestly.

**Gate:** Explanations reference real checked attempts, do not equate failed search with falsity, and remain bounded. Users can reproduce a refusal from structured data.

#### R-069 — Isolate and validate automated repair candidates

**Change:** Run proposed source/proof edits in immutable child snapshots with focused invalidation. Rank repairs by checked obligations closed, assumptions introduced, downstream regressions and cost. Publish exact diff and verified impact.

**Gate:** Failed candidates cannot mutate admitted state; successful repairs are independently replayable without the generating AI. No silent contract weakening or new assumption counts as a correctness repair.

#### R-070 — Extend the existing oracle with high-value reconstruction

**Change:** Reuse the completed W-01 linear oracle and independently replayed Farkas evidence. Choose the next census-dominant unsupported fragment, such as checked quantifier instances or bit-vectors; specify translation, request explicit evidence and extend a bounded checker. Keep solver discovery/query generation outside the kernel; retain unsupported/timeout distinctions.

**Gate:** Forged unsat answers, bad translation, incomplete certificates and mismatched queries reject. Compare useful coverage gained against checker/TCB complexity before adding another solver.

#### R-071 — Add deterministic engine selection and bounded portfolios

**Change:** Select normalization, congruence, intervals, linear/difference reasoning, bit-vectors or quantified search based on supported term shapes and measured cost. Apply budgets per engine and total request; avoid invoking expensive solvers for trivial goals.

**Gate:** Portfolio ordering affects latency only, not theorem meaning. Every engine returns checked evidence or explicit non-proof; publish engine hit/cost distributions.

#### R-072 — Produce checked counterexamples and bounded diagnostics

**Change:** Replay candidate models against source/IR semantics, including path conditions, widths, ownership and effects. Separate a concrete violating trace from an unvalidated solver assignment, and bounded success from unbounded correctness.

**Gate:** Spurious models are rejected or labeled unvalidated; valid false contracts produce reproducible inputs/traces. Counterexamples cannot authenticate a theorem merely because no model was found.

### 23.11 Priority band I — larger system properties, staged by demand

Start only once sequential semantics/resources and portable evidence support real examples. Within this band, prioritize observed user workloads.

#### R-073 — Add bit-precise bounded execution

**Change:** Model finite loops/recursion and memory operations for an explicit supported subset, with checked SAT/bit-vector evidence or independently validated execution traces. Record bounds, target semantics and coverage.

**Gate:** Finding no bug within a bound is labeled bounded checking, not unbounded proof. Overflow/alias/path completeness controls verify the model; useful counterexamples feed ordinary regression tests.

#### R-074 — Verify parser and protocol examples end to end

**Change:** Select actual Elisa parser/buffer/protocol code using existing imported compiler infrastructure. Specify consumption, success/error behavior, bounds, resource preservation and round-trip properties; build reusable lemmas before automation expansion.

**Gate:** Prove properties across all supported paths and retain malformed-input counterexamples. Track annotation count, unresolved obligations, proof bytes and end-to-end checking time.

#### R-075 — Establish a concurrency semantics and race-safety slice

**Change:** Specify supported threads/tasks, shared state, synchronization and memory-order assumptions. Start with ownership transfer and exclusive/shared-read access rules before richer concurrent separation logic.

**Gate:** Race-producing access, invalid transfer and missing synchronization refuse; valid message-passing and protected-state examples verify. No sequential frame rule is silently reused for concurrent interference.

#### R-076 — Add checked concurrent invariants and atomic operations

**Change:** Define invariant ownership, opening/closing rules and atomicity obligations for one useful synchronization primitive. Introduce ghost protocols/resource algebra only to support this slice and keep all model assumptions explicit.

**Gate:** Invariants cannot remain open across prohibited interference points; fabricated ghost resources and invalid atomic windows reject. Proofs compose over two threads with complete replay.

#### R-077 — Verify protocol state machines and ownership transitions

**Change:** Specify typestate/session transitions as ADTs plus capabilities; verify message validity, sequencing and resource transfer. Reuse effect/ghost/ADT libraries instead of creating a separate unconnected proof language.

**Gate:** Illegal transitions, duplicate messages and capability reuse refuse. Valid implementations refine the declared protocol with source-correspondence evidence.

#### R-078 — Add lock-order and deadlock-safety checking

**Change:** Model lock acquisition/release, blocking effects and order invariants; provide a proof-producing acyclic-order checker for a supported subset. Distinguish absence of modeled lock cycles from whole-program deadlock freedom.

**Gate:** Cyclic acquisition, forgotten release and aliasing locks reject. Unsupported blocking/FFI dependencies remain explicit; a bounded scheduler run is not a general guarantee.

#### R-079 — Introduce temporal obligations and fairness explicitly

**Change:** Define traces, state predicates and safety/liveness judgments for finite-state examples. Record environment progress/fairness assumptions; use checked invariant/ranking arguments or certified finite-state evidence.

**Gate:** Safety cannot imply liveness without progress evidence; unfair schedules and missing environment guarantees invalidate unconditional claims. Keep temporal models related to source transitions.

#### R-080 — Add refinement between abstract and executable models

**Change:** Define simulation relations for protocols/data structures and check initial, step and observation obligations. Support stuttering only with explicit progress conditions where liveness is claimed.

**Gate:** An abstract model theorem transfers only through checked refinement obligations; unmodeled exceptional/low-level behavior prevents transfer. Validate one meaningful implementation rather than a generic empty framework.

#### R-081 — Package practical verified standard components

**Change:** Deliver versioned libraries for buffers, maps/sequences, parsers, state machines and supported synchronization primitives. Bundle contracts, proofs, trust summaries, examples and incremental identities.

**Gate:** At least two independent clients reuse each component without copying its proof internals; changed interfaces invalidate clients correctly. Maintain corpus latency/RSS gates as library size grows.

### 23.12 Priority band J — dogfooding, independent assurance and release quality

Dogfooding runs throughout the roadmap; these ordered packages deepen its guarantees.

#### R-082 — Publish an exact self-verification scope matrix

**Change:** Map kernel/admission/search/report/compiler/runtime modules to properties proved, tested, assumed or unsupported. Record required declaration sets and distinguish memory safety, functional correctness and logical soundness.

**Gate:** Every “self-verified” claim names properties, code revision and trust dependencies. A 37/37 fixture or zero replay gaps cannot stand in for whole-assistant verification.

#### R-083 — Verify kernel data-structure invariants

**Change:** Prove bounds, arena ownership, DAG acyclicity, immutable contexts, binder scope and checked index arithmetic for kernel primitives. Use existing standalone harnesses and expand source support only through justified rules.

**Gate:** Required declarations prove with no circular use of their own unverified summaries. Adversarial runtime probes and compiler stage differential controls corroborate implementation behavior.

#### R-084 — Formalize the calculus and rule soundness

**Change:** Define denotational/judgment semantics for the admitted typed core and prove preservation of truth for each rule family. Start with propositional/equality rules, then arithmetic/ADT/resource extensions. Record axioms explicitly.

**Gate:** Meta-theorems are replayable in a declared trusted foundation; proving test examples is not a rule-soundness proof. Clearly distinguish mathematical calculus soundness from implementation correspondence.

#### R-085 — Relate kernel implementation to its specification

**Change:** Verify parsing/formation/replay functions refine the mathematical rules over well-formed inputs. Decompose totality, rejection behavior and success correctness. Establish trusted bootstrap boundaries so self-checking is not presented as eliminating all trust.

**Gate:** Every accepted implementation result maps to a derivation; invalid input cannot exploit unspecified behavior. Independent bootstrap/checker evidence remains available.

#### R-086 — Dogfood selected compiler passes

**Change:** Prioritize lexer bounds, parser preservation, name resolution, region escape checks and typed lowering invariants based on actual incidents. Prove tractable pass properties and validate transformation witnesses where full verification is premature.

**Gate:** Proof-discovered compiler defects receive minimized stage0/stage1 cases and fixes. Pass-specific guarantees are labeled precisely; verified lexical safety does not imply correct machine code.

#### R-087 — Build a genuinely independent cross-check path

**Change:** Specify canonical abstract proof packages and implement a small checker with independently reviewed control flow/representation where feasible. Cross-check current Elisa replay on a rule-complete corpus; avoid treating copied producer logic as independence.

**Gate:** Divergent checker outcomes block release and are minimized. This tool is corroborating assurance, not an undocumented non-Elisa proof oracle; the main system and admission remain in Elisa.

#### R-088 — Expand mutation, generative and differential testing

**Change:** Generate well-typed small source programs, valid proof DAGs and single-step invalid mutations. Cross-check bounded execution, producer/replay, cached/uncached, serial/parallel and stage0/stage1 behavior. Seed from real soundness incidents.

**Gate:** Tests detect intentionally broken formation, premise, arithmetic, region and source-binding guards. Record mutation survival reasons; random passing runs are supporting evidence rather than a proof.

#### R-089 — Establish compatibility and release qualification

**Change:** Version CLI/protocol/package/source-model semantics with migrations and explicit retirement policies. Run current full suites, census and benchmarks on immutable macOS/Linux products; retain compact durable evidence and exact product digests.

**Gate:** No known supported-subset false acceptance; no admitted replay gaps; reviewed coverage losses and performance regressions; honest open-feature list. Cross-target replay rejects incompatible ABI-dependent statements.

#### R-090 — Run continuous evidence-driven backlog renewal

**Change:** After each band, rank remaining failures by root cause, affected declarations, trust risk, proof effort saved and measured cost. Retire completed tasks with links to commits/evidence; add newly discovered high-impact gaps without erasing historical incidents.

**Gate:** The plan stays executable: one active critical path, clear next task, bounded experiments and frequent validated commits. “World class” is demonstrated by reliable real-program proofs, efficient independent replay and precise refusal, not feature-count marketing.

### 23.13 Concrete first execution cycles

Do not spend the first cycle designing all 90 packages. Use this ordered sequence:

1. **Cycle 1 — current truth:** R-001 and R-015; freeze exact products, rerun the small known-failure corpus and publish current coverage/cost evidence. Reconcile historical evidence, including whether the two conditional gaps still exist.
2. **Cycle 2 — admission reliability:** R-002–R-005, prioritizing any reproduced unsafe behavior; land one minimized fix at a time. If historical cause remains unresolved, retain it as an incident and work on independently measurable current defects.
3. **Cycle 3 — cost visibility:** R-010–R-014; add cheap counters and an allocation profile for the largest current complete workload plus the dominant timeout. Keep collector overhead and partial captures visible.
4. **Cycle 4 — one dominant optimization:** choose R-019, R-023, R-024, R-025, R-026 or R-027 from the profile. Require exact conclusion/trust equivalence and repeatable uninstrumented improvement before claiming a gain.
5. **Cycle 5 — incremental vertical slice:** R-028–R-032 on a two-module program with calls, constants and one refusal. Demonstrate body edit, contract edit, comment edit, missing dependency, restart and cancellation against cold checking.
6. **Cycle 6 — coverage with controlled cost:** close the largest real-code root cause through R-037–R-054; show newly verified declarations, unchanged adversarial outcomes and bounded cost.
7. Repeat the evidence/profile/feature loop; introduce expressive math and agent workflows as their dependencies permit. Keep kernel/specification dogfood and incident regression growth continuous.

### 23.14 Performance objectives and stop conditions

These are proposed engineering targets to ratify on the R-011 reference machines, not measured current capabilities:

| Workflow | Initial target | Required accompanying evidence |
| --- | --- | --- |
| No-op build | No compiler/link/signer invocations and under 250 ms median orchestration where the machine supports it | Exact unchanged output/manifest identity; validated closure and environment |
| Warm small-goal inspect | Under 100 ms p95 in a local session | Current generation, exact goal/context, full trust semantics |
| Small declaration edit | Under 500 ms p95 for the reference two-module program | Cold/incremental equivalence and correct reverse invalidation |
| Portable replay | Evidence-proportional node visits, no search/AI/solver, bounded hostile-input rejection | Complete rule/source-boundary checks, proof bytes and peak RSS |
| Largest current successful workload | At least 30% lower peak live allocation from the frozen baseline | Unchanged admitted theorem set, assumptions and completeness |
| Dominant search/replay bottleneck | At least 20% lower measured phase CPU after a focused architectural improvement | Seven paired rounds and no significant unrelated sentinel regression |
| Batch parallelism | Improved throughput under a fixed aggregate memory ceiling | Serial/parallel equivalence, process isolation and deterministic output |
| Repeated session requests | Stable retained live memory after warm-up and eviction | Store-generation/lifetime tests and no stale proof publication |

If a target is infeasible on a qualified platform, revise it with measurements and a recorded reason; never weaken soundness gates to reach it. Report inclusive and exclusive phase costs, live allocation and RSS separately. A cache hit is not “zero-cost proof”; include identity validation and required replay.

Do not pursue global canonicalization, e-graphs, broad solver portfolios, distributed verification, GPU search, aggressive parallel replay or a new dependent type theory until a real workload demonstrates better value than the preceding packages. These are possible later investigations, not required architecture. Avoid raising global limits to disguise an algorithmic cost problem.

### 23.15 Outcome scorecard

Each completed cycle updates a compact scorecard:

- **Soundness:** confirmed incidents, affected artifact versions, admission-route coverage, mutation failures caught, assumptions per theorem.
- **Usefulness:** verified declarations/contracts on pinned real code; unresolved obligations by root cause; annotations and manual proof steps saved.
- **Independence:** replay completeness, source-authentication status, checker dependencies, solver-free and AI-free replay support.
- **Performance:** cold/warm/edit p50/p95, CPU, peak RSS/live nodes, bytes, allocations, scans, replay work and cache miss reasons.
- **Reliability:** crashes, timeouts, interrupted/canceled publications, cross-platform disagreements and malformed-input rejection.
- **Maintainability:** responsibility-based module boundaries, under-600-line source compliance, public/private theorem authority and completed evidence-linked commits.

A useful feature closes a real gap with checked evidence. An optimization saves measured work while preserving that evidence. A foundational improvement reduces the amount of code or environmental state that must be trusted. All three are necessary for an efficient, expressive, high-assurance proof assistant.
