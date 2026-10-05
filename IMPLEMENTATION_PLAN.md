# Elisa-Proof implementation plan

Status: refreshed 2026-10-05 against committed proof HEAD `a60d8f59`. This records the committed baseline only; the current proof worktree also contains uncommitted replay-source investigation, this plan update, and a temporary diagnostic script, so it is not a qualified source snapshot. The adjacent compiler checkout is at `ecd26eb7` with unrelated in-progress parser and thread-shareability edits; its Stage1 product fails the source-tree provenance check and Stage0 cannot currently bootstrap those dirty parser-machine changes. The pinned `~/.elisac/stage1` snapshot at `7b27fa31` passes its own provenance check and is the only presently verified compiler product identified in this rebaseline; it is not the latest compiler checkout. No current proof/replay pair has been established from the exact committed proof tree in this rebaseline. The same-leaf qualified function-summary replay flaw was fixed and regression-tested in `d4c0fee0`; see the R-005 ledger below. Select an explicit verified compiler product and matching runtime for each build. Section 23.17 remains the broad ranked backlog; §23.16 and R-001–R-090 retain detailed designs, definitions and acceptance gates. A Stage1 build made while source inputs change is not qualification evidence. This update does not claim that the whole latest proof HEAD has a matched build or that the full suite passed. Historical measurements apply only to their recorded source/product identities.

## 0A. Active execution priority — correctness and iteration speed (2026-10-05)

Scheduling update: §23 now carries the next ordered backlog. The P-00–P-07 evidence and incomplete acceptance gates below remain binding; this historical queue is not a declaration that those tasks are finished.

**Mandate:** eliminate avoidable compute until Elisa's development cycle is competitive with, and where measured better than, contemporary compilers and verification tools. Correctness remains an acceptance requirement. Fast, dependable iteration is infrastructure for finding correctness defects sooner. This program supersedes the scheduling in §0 and §20; it does not weaken §3, source admission, the trust ledger, or release gates. The older feature milestones remain active after the infrastructure they require is dependable. All work below is planned unless explicitly identified as observed evidence.

### Audit baseline and limits

An earlier 2026-10-05 audit used proof HEAD `13d686b2`, frontend pin `4c479ad1`, and a strict O2 arm64 macOS binary whose recorded source digest matched the dirty working tree. This is historical profiling context, not a current product baseline. Evidence is retained locally under `build/audit-20261005/`; that ignored directory is not a durable release record. Copy reviewed summaries and minimized regressions into tracked evidence when completing the corresponding task.

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

This section supersedes scheduling in §0, §0A and §20, while preserving their acceptance requirements. It defines **90 durable work packages** plus the detailed child gates in §23.16 and the latest re-ranked execution order in §23.17. The R-IDs are stable tracking identities, not a promise to execute numerically. The current ladder reflects reproduced failures, trust risk, breadth of useful verification, expected cost reduction, and dependency order. Finish a small measurable vertical slice and commit it before starting the next. A reproducible false acceptance, crash in a current supported product, or memory-corruption defect preempts the queue.

### 23.1 What the next program builds on

The committed implementation baseline for this update is `7084c68d30f4`. Commit `57572c60` adds
qualified deterministic-call replay validation and a source-level forged-module regression. The
committed version of its regression returned success once under a fresh Stage1 check, but the source
tree advanced during compilation; an uncommitted expansion now adds forged-summary controls. Count
the implementation as landed but do not close the validation gate until the expanded test passes
from an immutable source snapshot. Do not overwrite or stage that test edit. This plan-only change
does not rebuild shared products or run the full proof/compiler matrices.

The recent high-ROI tranche added source-derived deterministic call-witness replay, including
qualified-call target validation; a separately named, explicitly capped 32-name difference-closure
search; bounded scalar quantifier triggers; typed unsigned quotient-bound replay and a subsequent
search-order fix; exhaustive enum-match fact replay; strict portable UTF-8 and package-size checks;
report verdict/proven-attempt invariants; a compact JSON route; agent protocol schema checks; and a
provenance-guarded paired benchmark. It also reorganized the portable replay test suite by
responsibility and added fact-growth and arithmetic soundness controls. These are foundations, not
blanket evidence that each broad feature is complete: extend their source-boundary, negative,
coverage, and performance gates rather than re-listing the landed feature as new work.

The prior planning baseline was `15560c60`; older roadmap revisions also inspected `239ba817` and
`d10085aae1da`. The current implementation baseline is `7084c68d` as stated above. The themed
backlog additionally records completed W-01 linear-oracle
reconstruction, W-02 symbolic-range rules (with further instance work open), W-03 indexed framing
and C-01 bounded difference closure. R-025/R-049/R-057/R-070 extend those capabilities; they must
not reopen completed work under new IDs. Before executing any R task, reconcile its scope with
current BACKLOG.md evidence and retire already-satisfied subrequirements.

Important remaining gaps, based on committed source and tracked evidence, are concrete:

- Portable output still emits `source.authenticated: false` in [package_output.elisa](src/app/package_output.elisa). Independent abstract replay and authenticated program correctness are separate capabilities.
- P-04 has artifact envelopes/storage controls, but no completed typed frontend artifact pipeline, semantic dependency discovery, reverse invalidation, or verifier reuse. P-05 has restart/replay tests, not a completed incremental verification session.
- The P-00 historical crash remains unexplained. The exact-current R-001 census completed both historical crash workloads without a crash, while mocap `track` now has 89 replay gaps, including two current `Slide.inner` roots. This does not establish a fix or cause; see [`docs/evidence/2026-10-05-r001-current-census.md`](docs/evidence/2026-10-05-r001-current-census.md).
- Large fact contexts, qualified rewriting, field equality, composed call summaries, and repeated certificate replay need bounded current measurements. Old timeouts and memory captures motivate investigations; they are not measurements of this checkout.
- Protocol validation exists, but its present test helper implements only a small schema-keyword subset. A passing shape check is not validation of every semantic cross-field invariant.
- Coverage is heterogeneous. A successful kernel-core fixture is valuable; it is not a proof of complete kernel soundness, compiler correctness, or every source adapter.
- Trust, source completeness, verdict correctness, proof coverage, latency, and memory must be measured separately. Increasing “proven” counts alone is not the optimization objective.
- The unsigned-division red gate was traced to producer search ordering, not a kernel replay mismatch. Commit `15560c60` tries the narrow quotient rule before recursive symbolic/quantified tiers that could exhaust shared work. Follow-up evidence committed as `7084c68d` validates a matched strict Stage1 O2 proof/replay pair: three positive same-width quotient bounds, including a high-bit `u64`, independently replayed, while five negative controls stayed unproved. This closes only that narrow quotient property; the broad arithmetic matrix remains open. The shared `build/` pair was still mismatched at the last recorded preflight, so do not use it for current integrated or performance claims until rebuilt from one immutable snapshot.
- The last tracked R-011 evidence found valid individual proof/replay manifests but different proof-source-tree hashes. The benchmark correctly refused to measure them. Until one immutable Stage1 build produces a matched product pair, do not use those executables for portable-package integration or performance claims.
- The committed source-size baseline has `src/app/cli.elisa` at 614 lines, above the repository's 600-line responsibility boundary. A working-tree extraction into `src/app/cli_tactics.elisa` is in flight but unvalidated and excluded from this baseline. Accept it only after source-size, namespace/API, CLI parity and strict Stage1 gates pass on a stable snapshot; do not create arbitrary numbered fragments. This maintenance gate does not delay soundness fixes.
- Call-summary, loop, and resource features have meaningful partial implementations, but high-value holes remain: conditional result transport through named/forwarded calls, a loop invariant combined with early break and a verified call, and a caller-place witness preserved through a forwarded by-reference argument. These should be small source-bound vertical slices with replay and adversarial controls, not broad rewrites.
- Instrumented profiles identify replay validation, root checks, witness extraction, and arena helpers as candidates, but the captures are incomplete/dropped and do not establish uninstrumented bottlenecks. The expensive field-equality workload also needs minimization and current-product reproduction before selecting congruence versus interning work.

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

**Current execution note (2026-10-05):** Commit `57572c60` adds
`proof_replay_deterministic_qualified_target`, which permits a qualified function witness only
when the source declaration name is globally unique and the declaration is in the requested
module, plus a regression that forges a wrong-module callee. Commit `078aeb9f` adds source-call
coverage checks and a hidden-reference-actual mutation. A Stage1 harness passed once while the
source tree advanced, so neither that smoke run nor the dirty forged-summary expansion closes the
call-witness slice. Re-run the final tests from an immutable snapshot. Conditional root 48 has
since been closed narrowly as described below; root 51 and complete call-site/argument/state
binding and R-005's wider witness audit remain open.

**Detached follow-up evidence (2026-10-05, not yet integrated into this baseline):** Candidate
commit `b3292d56` reconstructs the declared module and mapped actuals for qualified summary calls;
its isolated harness rejects a forged literal result, a `Gate::bounded(-1)` result paired with an
`x >= 0` proof, and a wrong-module witness while retaining a valid case. The harness used a
provenance-current installed Stage1 snapshot at revision `7b27fa31`, not the newer compiler-repo
Stage1 product now available. Re-run the candidate against the newest provenance-checked Stage1,
review/merge only after exact source and replay validation, and keep its tests separate from other
worktree edits. The same audit identifies remaining `Slide.inner` roots 48 (derive a conjunct from
a compound guard) and 51 (overflow-safe reasoning from `at + 1 < count` to `at < count - 1`);
neither is closed by the call-witness patch. A separate conditional-guard candidate is being
integrated and remains unaccepted until its conflict is resolved and its full proof/replay controls
pass on one immutable snapshot.

**Conditional replay follow-up (2026-10-05):** Commit `90a38a3e` adds a bounded kernel rule that
recognizes an exact primitive comparison as a positive conjunct of a stable `and` guard. The
matched strict O2 proof/replay evidence at source commit `1a78587c` proves `Slide.inner` root 48;
the missing-conjunct, wrong-guard, and overflow-sensitive controls remain refused. Root 51 remains
an explicit gap because it requires a checked signed-arithmetic/range derivation for
`at + 1 < count => at < count - 1`. The evidence is intentionally not generalized to arbitrary
logical implication and used an older Stage1 product than the compiler-repository tip noted in the
current build workflow. Rebuild the exact current snapshot with the latest provenance-checked
Stage1 before carrying this result into current-corpus or performance claims; see
`docs/evidence/2026-10-05-r003-slide-inner-source-trace.md`.

#### R-004 — Make whole-program admission completeness structural

**Change:** Audit `certificate_admission.elisa`, report aggregation and declaration scheduling for paths where missing bodies, skipped branches, unsupported nodes, semantic errors or truncated checks disappear from the verdict. Represent expected obligation inventory and completed checks explicitly; tie each exported theorem to a checked root.

**Gate:** Deleting an obligation, changing counts, omitting a declaration, introducing an unreachable unsupported operation or failing an imported dependency cannot yield unconditional program `proved`. Coverage and certificate counts remain explanatory data, not theorem authority.

**Progress (2026-10-05):** Report admission now checks that the recorded declaration count equals
the emitted declaration-detail inventory and that findings agree with the failure counter
(`src/proof/model/report_invariants.elisa`). The source-admission matrix passed on the strict O2
product from root revision `e9d27ef6` (SHA-256
`394b47e0c3b4cccf566c5143144658cd93aa954a095ae72135e0afd1d05c7628`): six malformed classes
were refused across all twelve CLI routes, while the suite's admissible incomplete-goal controls
remained available. This covers parse, import, semantic and proposition-formation refusals, not
structural mutation of the report inventory. R-004 remains open until omission/deletion/count
mutations and unreachable unsupported operations are shown to fail closed.

An additional invariant now requires the number of recorded successful goal attempts to match
the report's `proven` counter; deleting a successful attempt or retaining a success count without
an attempt makes source admission fail. The standalone report-invariant mutation harness and the
six-class/twelve-route source-admission matrix passed on strict O2 product SHA-256
`9363e938ab063baf212ff8ebd9e3d75e8a0f46470897d738c8f0f5222a3814eb` (source revision
`43796a5eac31ce5707645e2815b294dd16ab4b5d`). Exact identities and commands are recorded in
[`docs/evidence/2026-10-05-r004-proven-attempt-inventory.md`](docs/evidence/2026-10-05-r004-proven-attempt-inventory.md).
This still does not bind a complete expected obligation inventory to the original AST or prove
that every unsupported path has a recorded attempt, so R-004 remains open.

The latest continuation (`e83c4369`, documented at `d10085aa`) binds the `proven` count to the
recorded successful-attempt inventory, in addition to declaration and finding counts. The source
gate and mutation harness reject a deleted successful attempt and a success counter without a
matching attempt. This closes a report-consistency subcase only; expected obligations must still
be derived from the original admitted source/declaration schedule and reconciled against every
terminal status, including unsupported and skipped paths.

Follow-up: source admission now also requires recorded goal attempts to be no more numerous than
counted obligations. A runtime mutation deletes an open obligation ledger row and its aggregate
count while retaining the attempted goal; the formerly self-consistent report is refused. This
binds each remaining attempt to some counted event, but does not detect omission of a source check
that leaves no attempt, nor coordinated rewrites of source and report. Focused evidence is in
[`docs/evidence/2026-10-05-r004-open-attempt-bound.md`](docs/evidence/2026-10-05-r004-open-attempt-bound.md).

#### R-005 — Audit source-derived boundary facts and call witnesses

**Change:** Extend the recent source-derived witness work in `check/function_contracts_and_frames.elisa` and `replay/boundary_trace_shapes.elisa`. Inventory initial facts about parameter types, ranges, calls, aliases, effects and resources; replay exact owner, argument position, state version and declaration identity instead of trusting producer bookkeeping.

**Gate:** Swapped arguments, similarly named modules, changed contracts, stale pre-call facts, forged origins and substituted alias targets refuse. Document each remaining adapter-trusted fact. Zero replay gaps must not conceal an unjustified source premise.

**Progress (2026-10-05):** `src/proof/replay/source_call_coverage.elisa` now independently
reconstructs straight-line local bindings and assignments before a witnessed call, then checks its
source site and ordered/named actuals. The replay path rejects a parenthesized reference actual and
a forged scalar actual; the direct mutation harness restored and replayed the original trace.
Qualified calls are checked against a unique declaration in the named module, and a wrong-module
forgery was rejected. These focused results are recorded in
[`docs/evidence/2026-10-05-luna-slices-integrated-validation.md`](docs/evidence/2026-10-05-luna-slices-integrated-validation.md).
The standalone replay manifest in that combined run still names an older source tree, so no
coherent producer/replay-pair claim is made. Control-flow call sites remain fail-closed, and
post-call state liveness/version validation plus the wider parameter/range/alias/resource inventory
remain open.

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
invalid UTF-8 sequences and six malformed header-Boolean types return structured refusals. A
strict pinned O2 end-to-end probe also rejects malformed Boolean kernel payload types as
`malformed/node-schema` and out-of-range decimal payloads as `malformed/arena-inadmissible`; all
16 positive packages and the complete portable replay refusal corpus passed. Product identities
and exact refusal boundaries are recorded in `docs/evidence/2026-10-05-r006-decoder-boundary-inventory.md`.
Escaped UTF-16 policy is now explicit and covered: valid surrogate pairs are accepted, while
isolated, reversed, or malformed high/low surrogates return `malformed/json`.
The integrated root snapshot also passed the strict pinned O2 build, `scripts/test_portable_replay.py`,
`scripts/tests/test_portable_package_string_budget.py`, and `scripts/test_p05_package_restart.py`;
the exact replay product identity is recorded in the cross-check note. The broad decoder/ID
inventory, parser/checker fuzzing, systematic boundary matrix, parser-resource tests and
worst-case memory evidence remain open, so R-006 is not complete. Commit `c87fc1b9` adds one
focused malformed-package-Boolean control; it does not establish exhaustive Boolean-field or
all-decoder coverage.

**JSON nesting boundary follow-up (2026-10-05):** Commit `4da00dd9` pins the portable parser's
existing maximum JSON container depth of 256. Nested source arrays at depth 255 and 256 proceed to
the package source-schema refusal; depth 257 returns structured `malformed/json`. The test and
strict O2 replay identities are recorded in `docs/evidence/2026-10-05-r006-decoder-boundary-inventory.md`
(`93a3e2f0`). This verifies the exact cap boundary, not parser allocation/peak-memory behavior or
the full set of decoder fields.

**Progress (2026-10-05, structure-aware matrix):** Commit `8f1cbf66` adds 28 fresh-process
malformed-package cases across nested schema types, theorem-root integer encodings, child indices,
out-of-arena references, cycles, forward references, and an 8 MiB path string. Each invocation has
explicit CPU/wall/RSS/output bounds and checks structured result/trust consistency; all 16 positive
packages and existing package attacks still pass. No decoder change was warranted by this matrix.
This is deterministic structure-aware mutation, not coverage-guided/raw-byte fuzzing; maximal valid
dimensions and stress close to resource caps remain open. Its single sampled parser-workload RSS/time
is not a benchmark speedup claim; details are in
`docs/evidence/2026-10-05-r006-structure-aware-fuzz.md`.

**Integrated-current-main confirmation:** Commits `27f2a3ea` and `d0b946d6` record fresh isolated
proof/replay builds after the conditional-replay change. The latest tested source snapshot passed all
16 positive packages and all 28 malformed/adversarial cases with matching manifests and no partial
replay statuses. This is strong coverage for those package shapes, not a claim of broad parser fuzz
completeness or a current performance baseline; retain the older Stage1 identity in the evidence
note and rebuild with the newer verified compiler before using these runs as current toolchain
evidence.

**Unknown node-tag follow-up (2026-10-05):** Commits `1f580f73` and `3f973b55` add an explicit
fresh-process case that changes a theorem-reachable kernel node to an unknown kind and includes it
in the mutation summary. The focused portable replay suite passed all 16 positive packages and 29
structured mutations on a matched strict O2 proof/replay pair, with no partial theorem replay.
Exact identities and the bounded sample resource record are in
`docs/evidence/2026-10-05-r006-unknown-node-tag.md` (`270a1e67`). This adds one unknown-tag
boundary to the deterministic matrix; fuzzing and complete decoder/resource coverage remain open.

**Theorem-count cap follow-up (2026-10-05):** Commits `bc45e01e` and `60cfddd1` add a fresh-
process exact/one-over test for the portable theorem-count limit: 65,536 theorem entries replay,
while 65,537 returns bounded `over-budget/theorem-budget` refusal with an empty theorem result and
zero replay summary. The portable suite and focused regression passed on a matched strict O2
proof/replay pair. Exact identities and remaining scope are in
`docs/evidence/2026-10-05-r006-theorem-count-boundary.md` (`a6fb5a42`). This covers one parser cap;
the rest of the valid maxima and parser memory/CPU envelope remain open.

**`source.admissible` wrong-type runtime follow-up (2026-10-05):** The existing portable replay
suite passed using explicitly selected proof/replay binaries from generation
`79948cae3ccc4190aeebd778041c4b0b`, whose matched manifests identify source commit `414e5693`.
Changing `source.admissible` to JSON integer `0` returned structured `malformed/source-schema`
with no theorem rows and a zero replay summary. The suite also replayed 16 positive packages and
passed its bounded structure-aware and raw-byte mutation matrices. This is runtime evidence for
that historical pair only, not validation of current HEAD `3ebb3605`; the exact command, binary
hashes, result and per-process limits are recorded in
[`docs/evidence/2026-10-05-r006-source-admissible-runtime.md`](docs/evidence/2026-10-05-r006-source-admissible-runtime.md).

#### R-007 — Freeze typed contexts and control assumption discharge

**Change:** Establish immutable/versioned checked environments, distinct binder IDs, capture-avoiding substitution and exact context membership. Audit branches and tactics for leaked assumptions, reused scratch handles and mutation after checking. Share term storage only under explicit lifetime and context rules.

**Gate:** Escaping eigenvariables, alpha-renaming collisions, sibling contamination, shadowed names, stale context IDs and post-validation mutation cannot manufacture a theorem. Positive nested quantifier and branch proofs preserve their valid behavior.

**Progress (2026-10-05):** A narrow pinned O2 audit of quantifier substitution and two branch controls found that substitution refuses when capture-avoiding rewriting would cross a differently named nested binder, dictionary binders use marker-based simultaneous substitution, and disjunctive branches receive separate fact arrays. The focused symbolic-quantifier, variant-exclusion and conditional-ensure tests passed. Commit `c864a3c3` adds a tactic-runtime regression for one sibling-context contamination shape. These checks do not test post-validation arena mutation, scratch-handle reuse, escaping eigenvariables, distinct binder IDs or exact/stale context identity; R-007 remains open. Details and build identity are in `docs/evidence/2026-10-05-r007-quantifier-boundary-audit.md`.

**Progress (2026-10-05):** The executable tactic harness now mutates one disjunction-case child after construction and confirms that the sibling and parent fact arrays retain their original sizes. The focused harness compiled and ran successfully against the pinned Stage1/runtime; exact identities are in `docs/evidence/2026-10-05-r007-sibling-context-mutation.md`. This covers fact-array isolation for this tactic construction path only; stale context IDs, post-validation arena mutation, escaping eigenvariables, distinct binder IDs and broader assumption-discharge behavior remain open.

**Progress (2026-10-05, follow-up):** Commits `7a215424` and `69fc8338` add targeted runtime tests: a valid branch certificate is accepted, then either a child’s captured initial facts are mutated or the left child is given its sibling’s context; composed replay must refuse the mutation while preserving sibling isolation. A nested portable-branch control also passed an isolated proof CLI build. Evidence is recorded in `docs/evidence/2026-10-05-r007-sibling-context-mutation.md` (refreshed by `75caccaa`). These checks do not establish a general immutable-context implementation, arbitrary AST backing-store protection, stale generation safety, concurrency, or all tactic/scratch paths.

**Quantifier escape follow-up (2026-10-05):** Commits `8037346a` and `038cf854` add a finite universal positive control and an outer-scope adversarial goal. Independent replay accepts `forall x in [1]: x == 1` but refuses to prove free `x == 1` from that quantified fact. The focused kernel arena harness passed against its recorded pinned Stage1/runtime pair; evidence is in `docs/evidence/2026-10-05-r007-quantifier-binder-escape.md`. This is one name-based finite-universal escape shape. Binder IDs, general alpha-renaming/shadowing, existential introduction, post-validation mutation, and other context routes remain open.

**Nested binder shadowing follow-up (2026-10-05):** Commit `005884de` extends the focused kernel runtime harness with a positive nested finite universal whose outer and inner binders are both `x`. Replay preserves the inner body's binding for the second outer instance; the harness also checks that substituting the outer `x` rewrites a shadowed quantifier's range while leaving its body unchanged. An adversarial substitution of free `y` for `x` beneath `forall y` is explicitly refused as unsupported capture. The pinned Stage1 product/runtime probe passed; exact identities and the direct-invocation limitation are recorded in `docs/evidence/2026-10-05-r007-nested-binder-shadowing.md` (`c45385d2`). Binder IDs, general alpha-renaming and broader context mutation remain open.

#### R-008 — Establish a complete trusted-rule/dependency register

**Change:** Link each inference family, specialized arithmetic/resource checker and source-adapter premise to implementation, specification, tests and trusted assumptions. Inventory all theorem-construction paths and keep checked theorem constructors private. Distinguish logical axioms, source correspondence, compiler/runtime trust and environment assumptions.

**Gate:** Every admitted root exposes its transitive trust dependencies; no solver or tactic success enters as an unlabeled axiom. Review specialized checkers as TCB even when outside `kernel_core.elisa`.

**Progress (2026-10-05):** The starting register in
`docs/evidence/2026-10-05-r008-trust-register.md` maps the visible logical, resource, effect,
structural, tactic and portable-package admission paths and records their current trust labels and
focused test sources. It is source inspection only: construction call sites are not exhaustive and
no complete transitive root-to-source/compiler/runtime dependency graph or rule soundness map is
established. R-008 remains open.

**Certificate producer inventory follow-up (2026-10-05):** Commits `fff61c73` and `32aedfe3` make
`scripts/test_kernel_inventory.py` discover every function that appends a `ProofGoalCertificate`
including multiline construction sites, and compare that exact set against `KERNEL_INVENTORY.md`. The first run also exposed two current
boundary fact kinds missing from the inventory; `deterministic-call` and `match-exhaustiveness`
are now documented with their source producers and replay checks. The focused inventory check
passes with 10 source-matched tables and 169 entries. This catches undocumented producer/kind
additions but does not prove producer soundness, constructor privacy across all APIs, or transitive
trust closure; R-008 remains open.

**Private producer follow-up (2026-10-05):** Commit `55442e1b` moves the ordinary goal-certificate
appender `proof_add_goal_attempt` into the module's private section. The inventory regression now
also fails when a discovered `ProofGoalCertificate` appender is declared public. Existing
cross-file callers compiled in a strict Stage1 O2 proof build, the quantifier tactic runtime
retained kernel trace/certificate replay, and the inventory still reports 10 tables and 169
source-matched entries. Build identities and focused scope are in
`docs/evidence/2026-10-05-r008-private-certificate-producer.md` (`767b569a`). The other four
appenders were already private. This protects producer visibility only; it does not complete the
trust graph, prove source premise soundness, or make report structures immutable.

#### R-009 — Automate soundness-incident and artifact invalidation policy

**Change:** Version rule semantics and source-admission identities; introduce a documented affected-version registry and cache/package refusal or mandatory-replay policy. Preserve reproducer, exact product, trust boundary and downstream theorem impact for every confirmed incident. Reuse existing identity controls.

**Gate:** An artifact generated by an affected rule cannot silently retain an unconditional verified label after a fix. Test old/new package handling and dependency cascades; semantic migrations remain separate from cosmetic format changes.

**Progress (2026-10-05):** Source review found existing report-cache keys bound to included inputs,
the exact executable, target, relevant environment and cache recipes; declaration artifacts bind
to the current build context, source slice, payload and dependencies; portable theorem packages
are independently replayed and label source trust as adapter-supplied. The audit in
`docs/evidence/2026-10-05-r009-invalidation-policy-audit.md` records focused test sources and
three passing host-side cache/artifact identity checks; those checks use synthetic identities and
do not validate a compiled proof product or package migration. Commits `9d9afc28` and `9a022026`
add a strict incident registry and reject a malformed product-kind field. The registry is not yet
shown to invalidate real cache entries or proof packages by transitive semantic rule identity.
No complete old/new semantic migration policy is established, so R-009 remains partial.

### 23.4 Priority band B — bounded work and usable performance evidence

Start after immediate false acceptance/corruption containment. The goal is predictable cost before adding broader search.

#### R-010 — Instrument end-to-end phase and work counters

**Change:** Add lightweight measurements around import, parse, semantic checks, scheduling, VC generation, search, certificate construction, replay and serialization. Coordinate a genuine monotonic clock API with compiler/runtime support; do not infer internal duration by subtracting unrelated wall times. Expose counts even where phase timers are unavailable.

**Gate:** Disabled instrumentation has measured negligible cost; nested phases do not double-count exclusive time. Counter totals agree with workload inventory. Clock failures cannot alter proof outcomes.

**Progress (2026-10-05):** A source-level report inventory maps existing counters and their limited origins across import, lex/parse, semantic checks, scheduling, VC generation, search, certificate construction, replay, and serialization. The CLI exposes artifact/workload counts, selected return-analysis and goal-cache counters, kernel arena counts, output bytes, and replay outcomes; it has no internal monotonic clock or complete phase-work totals. P-01 external process wall/CPU/RSS and Python JSON-decode time remain harness measurements. No internal durations were inferred and no ambiguous counter was added. Instrumentation overhead and phase-work consistency gates remain unverified; see [`docs/evidence/2026-10-05-r010-measurement-coverage.md`](docs/evidence/2026-10-05-r010-measurement-coverage.md). R-010 remains open.

#### R-011 — Establish versioned performance and coverage sentinels

**Change:** Extend existing P-01 and paired benchmark harnesses with tiny interactive goals, successful/refused symbolic quantifiers, kernel core, field equality, composed calls, resource-heavy modules and adversarial fact growth. Keep inputs and semantic expected outcomes independently versioned.

**Gate:** At least seven alternating paired rounds after warm-up for claims; report median/p95, CPU, peak RSS, proof bytes, obligations and replay. Timeouts remain censored outcomes, not successful timings. Include cold/no-op/edit and portable-replay costs.

**Progress (2026-10-05):** P-01 has an independently versioned workload contract in
[`scripts/p01_sentinels.json`](scripts/p01_sentinels.json), with fixtures pinned by path, size,
SHA-256 and expected outcomes. The paired benchmark now validates manifest sidecars, executable
hashes, proof/replay source and toolchain identity, and baseline/candidate toolchain identity;
it rechecks manifests after snapshotting inputs. Its default is seven alternating paired rounds
after warm-up and it reports median/p95 wall time, CPU and peak RSS. Fifteen focused harness tests
and its self-test pass. A `Popen.kill()`/`wait4()` double-reap race in the P-01 measurement runner
was fixed, with its test passing five consecutive runs.

**Pinned corpus follow-up (2026-10-05):** Commit `1b20400d` adds three semantic-shape sentinels
with source path, byte size, SHA-256 and expected exit/status: unsigned-boundary refusal,
quantifier success and region-lending success. The manifest test passes. All three also produced
their expected outcomes with zero replay gaps on the explicitly identified published pair in
[`docs/evidence/2026-10-05-r011-sentinel-corpus-follow-up.md`](docs/evidence/2026-10-05-r011-sentinel-corpus-follow-up.md).
That run used a source-dirty product built from `3ebb3605`, so it does not validate the current
integrated source. This is a small corpus expansion, not completion of the semantic-shape matrix,
paired timing baseline, or P1.1 gate.

The actual paired preflight rejected the current `build/elisa-proof` and
`build/elisa-proof-replay`: their proof-source tree hashes are respectively
`8ad03c75…d35715` and `0de5d950…b62f35b`, although both identify the same clean Stage1 compiler
and pinned frontend. The guard emitted no timing result. Exact product hashes and the refusal
output are in [`docs/evidence/2026-10-05-r011-measurement-guard.md`](docs/evidence/2026-10-05-r011-measurement-guard.md).
R-011 remains open: no comparable seven-round baseline has been recorded, and the field-equality,
composed-call, resource-heavy, fact-growth, cold/no-op/edit, portable-replay and other required
sentinel classes still need coverage. Commit `e972dc02` reports semantic workload metrics including
proof/certificate bytes and replayed counts, but these are not yet validated across the complete
sentinel corpus or tied to internal phase/work counters.

#### R-012 — Account for actual search work with named budgets

**Change:** Replace ad hoc depth-only containment with explicit counters for visited nodes, fact scans, comparisons, rewrites, branch candidates, substitutions and allocated scratch bytes. Centralize named limits and checked arithmetic. Keep search budgets distinct from certificate replay/decoding limits.

**Gate:** Budget exhaustion returns a precise stage/dimension/observed/limit with no partial theorem. Boundary and one-over tests include the current 32-name difference closure. Accepted proofs replay within independent checker bounds.

**Progress (2026-10-05):** On starting commit `3ea2364d`, producer difference search was using the kernel replay node-limit constant directly. Commit `a867c7c4` gives the search its own named `PROOF_LINEAR_DIFFERENCE_NODE_LIMIT`, currently 33 matrix nodes (the zero node plus 32 names); replay keeps its independent kernel limit. The existing `scripts/test_long_difference_chain.py` already exercises the exact 32-name acceptance and 33-name refusal, and confirms all accepted certificates replay with zero gaps; it passed after a strict build with the current Stage1 compiler (`e4a16fd2`). This closes only the producer/replay cap naming separation. Actual work counters, checked arithmetic for accumulated work, and a precise stage/dimension/observed/limit exhaustion finding are still open, so R-012 remains open.

#### R-013 — Remove fact-count-dependent denial-of-service shapes

**Change:** Benchmark repeated tautologies, irrelevant disjunctions, wide equality graphs and nested pure summaries across increasing sizes. Identify superlinear scans before changing algorithms. Retain `bounded_model_work_budget.elisa` as intentional stress data and add logically rich variants that exercise the same dimensions.

**Gate:** Publish scaling curves and expected asymptotic work counters; beyond configured bounds the system terminates predictably. Do not eliminate stress coverage by simplifying away all duplicated facts before their relevant cost boundary is exercised.

**Progress (2026-10-05):** Added a paired fact-growth fixture with repeated facts and theorem-relevant integer bounds, plus a focused regression probe. On validation product SHA-256 `394b47e0c3b4cccf566c5143144658cd93aa954a095ae72135e0afd1d05c7628`, 12 duplicates prove/replay and 13 refuse at the goal budget with no partial certificate/model or replay gap. No scaling measurements are claimed. See [`docs/evidence/2026-10-05-r013-fact-growth.md`](docs/evidence/2026-10-05-r013-fact-growth.md). R-013 remains open.

#### R-014 — Make allocation lifecycle observable

**Change:** Integrate optimized allocation-site/lifetime captures from the Elisa profiler and compiler tools; distinguish reserved arena capacity, committed memory, live nodes, dead retained nodes and process RSS. Attribute by stable source identity and store generation. Correlate captures with search phases.

**Gate:** Known allocation/reclamation probes produce expected counts and high-water marks; dropped events and truncated captures are explicit. Instrumented proof output agrees with uninstrumented output. Never count instrumentation overhead as target cost.

**Progress (2026-10-05):** Commits `3dc4dad5` and `a5cba7a7` add a bounded reader for existing
allocation-capture artifacts and a regression ensuring capture-quality fields remain independent.
It preserves per-repetition event counts, completeness, dropped-event counts, lifetime availability,
logical live-byte peaks, and backing-capacity peaks as distinct fields. A synthetic probe covers
complete, dropped, truncated, and malformed captures. The reader was exercised against an existing
compiler memory artifact (six workload groups, 18 complete captures), which verifies producer-schema
compatibility only; those runs do not measure the proof assistant. Proof-workload captures,
source/store/phase attribution, RSS separation, overhead measurement, and known proof
allocation/reclamation probes remain open. See [R-014 allocation summary evidence](docs/evidence/2026-10-05-r014-allocation-summary.md).

**Calibration follow-up (2026-10-05):** Commit `fab7dba0` tests the adjacent Elisa profiler’s
actual lifetime analyzer using a known event sequence: 8- and 16-byte allocations, one explicit
reclaim, reset retirement, 24-byte peak logical liveness, zero live bytes at capture end, and 64
bytes of retained backing capacity. The test rejects incomplete captures, each tested dropped-event
indicator, and event-bound truncation. This is synthetic analyzer-input calibration—not a complete
runtime capture, proof-engine allocation profile, sview lifetime test, or performance result. The
next meaningful step is a known-count Elisa runtime probe followed by captures of real proof success
and expensive refusal paths; do not use the synthetic fixture to choose an optimization.

**Post-reset `sview` control (2026-10-05):** Commits `0816f671` and `b4c383fb` add the existing
`rejected_sview_after_region_destroy.elisa` source control to the real profiler runtime harness. The
proof checker refuses the destroyed-region borrow before target execution, with a
`region-destroy-live-borrow` finding and zero replay gaps. The valid runtime probe separately reads
its view while the backing region is live. This is a static verifier refusal control; it does not
dereference freed storage or cover arbitrary arena-reset and raw-pointer routes. See
[`docs/evidence/2026-10-05-r014-post-reset-sview-control.md`](docs/evidence/2026-10-05-r014-post-reset-sview-control.md).

#### R-015 — Isolate builds, products and evidence snapshots

**Change:** Ensure concurrent work uses immutable source exports, separate product paths and atomic manifests. Keep frontend revision, compiler product, runtime object, ABI, optimization mode and recipes coherent. Preserve exact measured executables when investigating regressions.

**Gate:** Concurrent builds cannot overwrite the binary named by another run; source mutation during preparation fails or restarts explicitly. Stage1 freshness is checked, stage0 fallback is labeled and validated, and no stale-product bypass is the normal workflow.

**Progress (2026-10-05):** Commits `7b9cb6ec` and `01a4dede` harden checksum-sidecar reuse and
parallel compile-log testing. The current paired benchmark correctly rejects the shared proof and
replay products because their proof-source digests differ. A coherent isolated pair and atomic
per-snapshot output workflow are still required; build robustness tests do not make mismatched
products comparable.

Commit `937ae0bb` fixes one source of that mismatch: when a product's dependency closure is
unchanged, `ELISA_PROOF_PRODUCTS=all` now refreshes its whole-snapshot proof provenance and
checksum while reusing the binary. A controlled fixture edits a source outside both closures and
confirms both manifests converge on the current source-tree digest without compiler or linker
work; a following no-op preserves all product and manifest bytes/timestamps. A strict Stage1 O2
pair has matching proof source digest `72d57a84…`. Follow-up commits `619c3dc8`, `3df1134c`, and
`37c9d862` add a barrier-controlled same-output concurrency test and stage all requested binaries
and manifests before publishing any of them. The second concurrent build is rejected by the
output-tree lock without changing outputs. An injected replay-link failure leaves both prior
products and manifests unchanged. Final file renames are still sequential, so interruption during
publication can leave a partial pair. A later injected rename failure demonstrated this concretely:
the proof product, manifest and checksum had advanced while replay remained old. Both individual
sidecars were valid, but the pair-level source-tree identity differed; a guarded reader rejected
the pair, and a subsequent ordinary build repaired it. The failure test now reports both identities.
An atomic symlink/pointer alone is insufficient if a consumer resolves proof and replay paths on
opposite sides of a switch; a safe design needs a shared generation ID plus readers that pin the
same immutable generation (or verify a stable pointer and retry). Immutable concurrent snapshots
and source-mutation detection during preparation also remain open. Exact identities and outcomes
are in [R-015 manifest-pair coherence evidence](docs/evidence/2026-10-05-r015-manifest-pair-coherence.md).

**Independent-root control (2026-10-05):** `scripts/test_build_independent_roots.py` runs two builds
concurrently from separate proof roots and compiler-source fixtures, pausing both at staged-manifest
creation with mocked compiler/linker tools. It confirms distinct root-local locks, object/binary/
manifest staging paths, source identities and pair generations; both published pairs resolve. This
tests orchestration only and exposes no race in the exercised boundary. Real compiler concurrency,
source mutation during snapshot preparation, failure recovery across roots and cross-filesystem
coordination remain unverified. See [independent-root mocked evidence](docs/evidence/2026-10-05-r015-independent-roots-mocked.md).

**Source-mutation snapshot control (2026-10-05):** Commit `04ea67a2` adds
`scripts/test_build_source_snapshot_race.py`. The fixture pauses after copying the proof `src/`
subtree and before snapshot preparation finishes, then edits a live source and adds a live file.
Mock compiler outputs embed the digest and sentinel bytes from the copied snapshot; the generated
binaries and manifests match that captured digest while marking the live source tree dirty. This
tests only the mocked post-copy preparation boundary. It does not exercise mutation during active
`rsync`, real compiler behavior, or compiler semantics. See [source-mutation snapshot control
evidence](docs/evidence/2026-10-05-r015-source-mutation-snapshot-control.md).

#### R-016 — Bound reporting and diagnostic materialization

**Change:** Separate compact verdict/trust/repair summaries from opt-in full facts and AST dumps. Stream diagnostics or serialize interned references with explicit ownership; preserve complete authoritative obligation inventory and certificate export. Record serialization bytes and retained report memory.

**Gate:** Compact and full routes agree on conclusions, assumptions, unresolved goals and replay. Large refusal reports stay bounded without silently truncating proof-critical data. Optional presentation truncation has an explicit marker and retrieval path.

**Progress (2026-10-05):** Added an explicit `--summary-json` presentation route. It keeps status, verification state, source byte count and FNV-1a source fingerprint, declaration and obligation totals, replay-confirmed proven/unproven totals, finding-status counts, semantic diagnostic counts, trusted boundary facts, replayed certificate count and the empty trusted-assumption ledger. It sets `details.omitted: true` and names `--json` as the authoritative full-evidence route. Positive and refusal comparisons are recorded in [R-016 compact report evidence](docs/evidence/2026-10-05-r016-compact-report.md). This bounds serialized presentation size for the exercised reports; retained report memory, streaming, and a large-refusal stress bound remain unmeasured and are not claimed complete.

The route is now checked in as `019cea37` and has focused positive/refusal coverage in
`scripts/test_report_summary.py`. Extend parity tests to the full source/trust/replay dependency
surface before relying on the compact route for batch tooling.

#### R-017 — Set ratcheted, workload-specific performance gates

**Change:** Once R-011 provides a baseline, set reviewed ceilings for interactive p95, batch throughput, replay latency and peak memory. First aim for at least 30% lower peak live allocation on the largest measured workload and 20% lower dominant-phase CPU where a profile identifies removable repeated work; these are targets, not claimed gains.

**Gate:** No accepted speedup changes admitted conclusions or trust. Treat small changes within variance as inconclusive. Pause an optimization after two bounded failed experiments and reassess evidence rather than indefinitely expanding budgets.

#### R-018 — Reduce compile/test iteration overhead safely

**Change:** Finish P-03: closure-specific keys, unchanged snapshot preservation, checksum-validated output reuse, targeted suite dependency maps and one build of each required product per run. Keep full matrices available and required for release. Cache negative decisions only with complete context.

**Gate:** Comment-only and unrelated-file edits avoid unnecessary work while relevant dependency/runtime/flag changes force it. Corrupt outputs trigger rebuild. Publish actual no-op cost, not only compiler cache-hit time.

**Progress (2026-10-05):** `scripts/test_build_dependency_closure.py` now corrupts one product's manifest checksum sidecar in its deterministic end-to-end build fixture. The next build recompiles and relinks that product, regenerates a checksum matching its new manifest, and leaves the other product unchanged. This establishes the rebuild decision with stub compiler/linker tools; no real-build timing or compiler-semantics claim is made. Closure/no-op cost, suite dependency maps, and measured real no-op cost remain open.

**Progress (2026-10-05, build-pair follow-up):** The fixture also verifies same-output build locking
and preservation of both installed products when replay linking fails after the proof link. These
are deterministic orchestration controls, not a real-compiler semantic test or a timing result.
Full crash-during-publication recovery and test dependency scheduling remain open.

### 23.5 Priority band C — remove repeated work in the current engine

R-010–R-014 identify which items have the greatest payoff; reorder within this band using measurements.

#### R-019 — Build reusable, checked fact-frame indexes

**Change:** Extend existing scalar-witness indexes with exact complement, equality, integer width/domain, disjunction and declaration-identity indexes. Build once per immutable frame; add parent/delta views for branches. Keep ordered candidate traversal where current bounded search behavior depends on order.

**Gate:** Indexed and scan implementations agree on a differential corpus including malformed markers and collisions. Demonstrate reduced scans and allocation on fact-heavy workloads. Index membership alone never establishes an unvalidated fact.

**Progress (2026-10-05):** `4eb4fec1` adds an open-addressed hash lookup for scalar witness names,
retaining the ordered source list and exact string comparison as authority. The Stage1 marker
fixture compares indexed and original scan behavior for valid/malformed markers and a same-bucket
collision. The combined strict O2 proof product and focused checks are identified in
[`docs/evidence/2026-10-05-luna-slices-integrated-validation.md`](docs/evidence/2026-10-05-luna-slices-integrated-validation.md).
This is a narrow correctness-checked index, not an established speedup: duplicate-heavy and
saturated-table behavior and paired scan/allocation/timing measurements on a representative
fact-heavy workload remain open. Broader frame indexes remain behind those measurements.

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

**Progress (2026-10-05):** The required positive assertions initially failed on manifested proof
binary `12c634…`, despite zero replay gaps. Diagnosis found that the producer tried the narrow
unsigned quotient theorem only after recursive symbolic and quantified searches could consume the
shared budget. Commit `15560c60` moves that sound, width-aware rule earlier; the kernel rule was
already checked and required no semantic change. A subsequent matched isolated Stage1 pair is
recorded below. The shared `build/` products remain mismatched in the last recorded preflight, so
they cannot substitute for that evidence or support current integration claims. R-042 remains open
for the rest of the width/sign/operation matrix.

**Follow-up validation (2026-10-05):** A clean strict Stage1 O2 build at source commit
`c87fc1b9c186a40bf22cc52b55e5b6ac5040943b` rebuilt proof and portable replay together. The direct
same-width unsigned `value / divisor <= value` slice passed with a variable `divisor > 0`, a
positive literal divisor, and a high-bit `u64` dividend; all five mismatch, zero-divisor, wrapping,
unrelated-bound, and signed-negative controls remained unproven. The report had zero semantic
errors and zero replay gaps, with every generated certificate independently replayed. Exact product
identities and focused commands are recorded in [R-042 quotient slice evidence](docs/evidence/2026-10-05-r042-unsigned-quotient-slice.md).
This closes the narrow quotient-bound slice; no width matrix, other arithmetic operation, or full
integrated-suite claim is implied.

**Unsigned u8 shift boundary follow-up (2026-10-05):** Commits `e8d17819`, `1ec99e4b`,
`8e4d6e25`, and `5bf08af1` add a strict O2 source/replay slice: `1 << 4 == 16` proves and
replays; negative counts emit the expected diagnostic; a shift by the u8 width and a false
high-bit-right-shift claim remain unproved. Source and kernel guards agree on these cases, so no
semantic change was indicated. The exact product identities are in
`docs/evidence/2026-10-05-r042-u8-shift-boundaries.md`. This does not establish oversized runtime
shift behavior, other widths/signs, or bitwise/cast parity.

**True high-bit u8 shift follow-up (2026-10-05):** Commit `23025f3d` adds same-sort unsigned
`>>` evaluation to the closed-constant producer and an independent kernel replay rule, both
bounded by the operand width. `128u8 >> 1u8 == 64u8` proves and replays; the width-sized
`128u8 >> 8u8 == 0u8` control remains unproved. The focused regression and matched product
identities are recorded in
[`R-042 high-bit shift evidence`](docs/evidence/2026-10-05-r042-u8-highbit-shift.md)
(`8110f017`). This closes one true high-bit u8 right-shift case; the broader R-042 matrix remains
open.

**Signed overflow boundary follow-up (2026-10-05):** Focused source and kernel audit found matching
fail-closed handling for divide-by-zero and `MIN_I64 / -1` / `MIN_I64 % -1`. The interval rule also
refuses `% -1` when it cannot establish that the dividend excludes the overflow input. Added
positive bounded cases with negative divisors, refusal cases for both minimum overflow operators,
and exact zero-divisor diagnostic checks. The strict proof/replay pair from the quotient-slice
validation independently replayed every accepted certificate with zero gaps. No producer/replay
mismatch or sound narrow behavior fix was found; the broader width-specific minimum and overflow
matrix remains open. See [signed division boundary evidence](docs/evidence/2026-10-05-r042-signed-division-boundaries.md).

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

The previous cycle order is superseded by the execution order in §23.17. Detailed designs and
adversarial acceptance gates remain in §23.16 and the R-package sections. In summary:

1. **Cycle 0 — freeze a trustworthy baseline:** review/land or reject the in-progress R-003
   candidate; make one coherent Stage1 proof/replay build; refresh the small failure census and
   preserve exact manifests. Do not benchmark or claim replay integration from a mismatched pair.
2. **Cycle 1 — close live correctness reds:** reproduce and fix the unsigned-division positive
   regression; close current producer/replay gaps and source-bound call witnesses; strengthen
   whole-program obligation admission. Keep P-00's historical crash as a separately tracked
   incident unless a current product reproduces it.
3. **Cycle 2 — harden the trust boundary:** finish context/binder isolation, decoder fuzz and
   resource limits, root-to-source trust dependencies, and semantic artifact invalidation.
4. **Cycle 3 — make costs observable:** define complete counters and budgets, expand the versioned
   corpus, integrate the profiler without dropped/partial captures, and measure allocation,
   refusal, report and build/test costs.
5. **Cycle 4 — optimize exactly one measured hot path:** use counter/profile evidence to choose
   replay reuse, congruence/equality indexing, fact indexing, branch deltas, sparse arithmetic
   evidence, or scratch reclamation. Compare complete outcomes and trust before/after; require
   paired uninstrumented data.
6. **Cycle 5 — deliver practical semantic slices:** conditional call-result transport; one
   collection traversal with invariant/break/helper; forwarded-reference framing and region-view
   lifetime; then effects/errors and checked ADT induction, each with source/replay controls.
7. **Cycle 6 — make edits and proofs reusable:** typed frontend artifacts, reverse invalidation,
   persistent certificates, a generation-safe local session, deterministic agent queries and
   proof-text round-tripping.
8. **Cycle 7 — dogfood and qualify:** prove selected verifier/kernel data-structure properties,
   verify a bounded compiler pass against an independently stated model, run an independent
   checker where feasible, and qualify exact products on supported platforms. Keep temporal and
   concurrency claims explicitly staged behind their semantic foundations.

### 23.14 Performance objectives and stop conditions

These are proposed engineering targets to ratify on the R-011 reference machines, not measured current capabilities:

Performance is a first-class acceptance dimension, but there is not yet a reliable current
end-to-end baseline for every workload. First make measurements complete and comparable; then
ratchet limits from that baseline. For each optimization, name the predicted dominant operation and
complexity, measure it directly, change one cause at a time, and require identical full outcomes,
obligation inventories, trust dependencies, and independent replay. Use instrumented profiles to
locate work and uninstrumented paired runs to claim speed. Report p50/p95, variance, CPU, RSS,
live/retained arena state, work counters, output/proof bytes, and censored timeout/OOM outcomes.
Report per-workload regressions; do not hide them in an aggregate geometric mean.

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

## 23.16 Detailed child implementation gates after the recent high-ROI tranche

These are detailed child gates mapped to existing R-packages; §23.17 controls their current
execution priority. They do not create duplicate feature work. The R sections above remain the
semantic design and adversarial acceptance contract. A task is not complete because its code
exists: attach the exact source/product identity, tests, replay and cost evidence specified here.
If a new false-acceptance or current-product crash appears, pause the performance queue and move
that defect to the front.

This queue is revalidated at proof HEAD `7084c68d` (2026-10-05); the exact baseline and dirty-tree
exclusions are recorded at the top of this plan.

### 23.16.1 Rebaseline: high-ROI slices now landed, parent work remains open

The following are real committed gains after the prior `15560c60` planning baseline. They
reduce known risks or establish useful instrumentation, but each is a narrow child slice: do not
mark the corresponding R-package complete until its original gate and all adversarial controls
are met. These commits have not been rebuilt together as one coherent release product merely by
appearing on `main`.

| Landed slice | What it now provides | Still not established |
| --- | --- | --- |
| `078aeb9f`, `57572c60`, `d4c0fee0` — deterministic call witnesses | Source-call coverage and qualified target validation have focused regressions; the runtime trace test rejects a hidden reference actual and wrong-module target. A reproduced function-summary forgery that changed `Gate::Inner::bounded` to same-leaf `Elsewhere::Inner::bounded` is now rejected by full-path owner matching, while the original witness replays. | Complete call-site identity, ordered actual/value/place bindings, state versions, alias-qualified path resolution, contract/effect/footprint binding and immutable-source-snapshot validation; conditional `Slide.inner` replay gaps. See [`docs/evidence/2026-10-05-call-summary-module-identity.md`](docs/evidence/2026-10-05-call-summary-module-identity.md). Continue R-003/R-005. |
| `7b9cb6ec`, `01a4dede`, `1abf91e3`, `2d7f2aac`, `b7f26cf9`, `04b91100`, `b554c07d`, `e2a5f6f8`, `95e74c94`, `7ccd8eaf` — build evidence and staged publication | Checksum corruption, deterministic same-root locking, prepare-before-publish, injected compile/link failures, and an injected mid-rename interruption are covered; the latter exposes a mixed pair with individually valid manifests that a pair-identity guard refuses. | Make every reader pin one generation, recover interrupted publication without accepting mixed products, test all rename boundaries and separate roots, snapshot source immutably, and build real matched current products. Continue R-015/R-018. |
| `3dc4dad5`, `a5cba7a7`, `fab7dba0` — allocation capture summary/calibration | A bounded summary preserves independent capture-quality fields; a known synthetic allocation/reclaim/reset sequence calibrates the profiler analyzer and its refusal cases. | Real Elisa runtime allocations, proof workload captures, sview lifetime, source/store/phase attribution, RSS separation, instrumentation overhead and peak proof-engine live bytes. No optimization is selected from synthetic data. Continue R-010/R-014. |
| `9d9afc28`, `9a022026` — soundness-incident registry | Strict incident records are parsed and malformed product kinds are rejected. | Incident completeness, affected theorem/cache/package reachability, automatic invalidation, migration behavior, and integration with actual admission. Continue R-008/R-009. |
| `c864a3c3`, `7a215424`, `69fc8338`, `75caccaa` — tactic branch-context isolation | Tests cover sibling fact-array isolation, mutation of a child after certificate checking, and replacing one branch child’s context with its sibling’s context; invalid composed replay must refuse. | These are targeted regression tests, not immutable/versioned context implementation. Arbitrary AST backing-store mutation, stale generation handles, binder IDs, concurrency, reentrancy and all routes remain open. Continue R-007. |
| `c87fc1b9`, `8f1cbf66`, `acb895ad`, `27f2a3ea`, `d0b946d6`, `1f580f73`, `3f973b55`, `270a1e67`, `bc45e01e`, `60cfddd1`, `a6fb5a42` — package decoder refusal | A matched strict O2 pair replayed all 16 positive packages, refused 29 structured mutations including an unknown reachable node kind, accepted exactly 65,536 theorem entries, and refused 65,537 without partial replay. | Raw-byte/coverage-guided fuzzing, all decoder fields and valid maxima, cap-adjacent memory/CPU tests, and a rebuild with the newest compiler remain open. Continue R-006. |
| `bc45e01e`, `60cfddd1`, `a6fb5a42` — theorem-count cap boundary | Exact theorem count 65,536 replays; 65,537 yields bounded structured refusal, no theorem results and zero replay summary. | Only the theorem count cap is covered; other count maxima, node/child memory budgets and CPU limits remain open. See [`docs/evidence/2026-10-05-r006-theorem-count-boundary.md`](docs/evidence/2026-10-05-r006-theorem-count-boundary.md). |
| `e972dc02` — benchmark semantic workload metrics | The benchmark harness reports classification and semantic workload quantities alongside measurements and rejects incomplete reports. | Current coherent products, broad pinned corpus, phase/work counters, allocation/RSS quality, paired performance evidence, and useful ratcheted budgets. Continue R-010–R-017. |
| `4eb4fec1` — scalar witness name index | A hashed lookup narrows one scalar-witness name-resolution path; a runtime marker-dispatch fixture exercises it. | Collision/duplicate/name-normalization adversaries, comparison against the scan path, broad call-site coverage, and a paired profile proving lower end-to-end work without outcome drift. Treat as a candidate optimization, not a speedup claim. Continue R-019/R-023. |
| `7084c68d` — unsigned quotient slice integrated | A matched strict Stage1 O2 proof/replay pair independently replayed same-width unsigned `x / d <= x` with variable/literal divisors and a high-bit `u64` dividend; five negative controls stayed unproved. | Only this narrow quotient property is closed. Other widths/operations, complete arithmetic matrix, exact-current integrated census, and broader R-042 remain open. See [`docs/evidence/2026-10-05-r042-unsigned-quotient-slice.md`](docs/evidence/2026-10-05-r042-unsigned-quotient-slice.md). |
| `f6e18613`, `605710a9`, `6776977c`, `9793a98f`, `b5793019` — signed division/remainder boundaries | Safe negative-divisor cases prove; zero divisors and `MIN_I64 / -1` or `% -1` stay unproved, with exact diagnostic-site and independent replay checks. | This is only the `i64` division/remainder edge slice; widths, casts, shifts, bitwise operations, overflow modes, and cross-route semantic parity remain open. See [`docs/evidence/2026-10-05-r042-signed-division-boundaries.md`](docs/evidence/2026-10-05-r042-signed-division-boundaries.md). |
| `4da00dd9`, `93a3e2f0` — portable JSON depth boundary | Depths 255 and 256 reach structured source-schema refusal; depth 257 reaches structured malformed-JSON refusal at the pinned cap. | Does not cover parser allocation/peak memory, CPU near the cap, or other decoder fields. Continue R-006. |
| `8037346a`, `038cf854` — finite universal escape control | Independent replay accepts the quantified positive control and refuses one attempt to use its bound name as a free outer-scope fact. | Binder identity, general shadowing/alpha-renaming, existential rules, mutation and other context routes remain open. Continue R-007. |
| `005884de`, `c45385d2` — nested binder shadowing | Same-named nested finite universals replay; outer substitution rewrites the inner range but preserves its body; capture-prone free-name substitution refuses. | This is focused name-based shadowing coverage, not stable binder IDs or general alpha-renaming. Post-check mutation and broader context routes remain open. Continue R-007. |
| `e8d17819`, `1ec99e4b`, `8e4d6e25`, `5bf08af1` — unsigned u8 shift boundaries | A safe small shift proves and replays; negative and width-sized shifts and a false high-bit result stay unproved; producer and kernel guards agree. | Other widths, oversized execution behavior, casts, bitwise operations and cross-route parity remain open. Continue R-042. |
| `23025f3d`, `8110f017` — true high-bit u8 right shift | `128u8 >> 1u8 == 64u8` proves and independently replays; the width-sized refusal remains closed. Producer and kernel use matching unsigned same-sort rules. | One `u8` right-shift value is covered; other counts, widths, left shift, casts, bitwise operations and cross-route parity remain open. See [`docs/evidence/2026-10-05-r042-u8-highbit-shift.md`](docs/evidence/2026-10-05-r042-u8-highbit-shift.md). |
| `71ede8b4`, `fcbc4b95`, `ee9ba097`, `c83e2825`, `efe67466`, `89d61b89`, `f1161b05`, `d196c7a6`, `6c8292e2`, `89fc3b9c` — signed unit-shift implication and edge refusals | Only the exact `(x + 1) < y ⇒ x < (y - 1)` positive-conjunction shape is admitted; range safety is established from source facts before the guard is used as an arithmetic premise. A matched current-Stage1 pair replays `Slide.inner` 6/6 including roots 48 and 51, with wrong-guard/missing-conjunct/overflow/wrong-bound controls refused. The unsigned `u64` shape and exact `count > I64_MIN` source-name shape now refuse before goal certification; matched strict O2 evidence reports zero replay gaps. | Narrow rule and refusal only. The positive edge pair's source snapshot (`6753e0df`) predates latest main; rebuild the full integrated pair. The i64-minimum refusal keys on the source constant name and does not implement lower-edge replay; alternate names, equivalent expressions, other widths, mixed sorts, reversed comparisons and all source-to-kernel routes remain open. See [`docs/evidence/2026-10-05-r042-i64-min-positive-refusal.md`](docs/evidence/2026-10-05-r042-i64-min-positive-refusal.md), [`docs/evidence/2026-10-05-r003-root51-edge-audit.md`](docs/evidence/2026-10-05-r003-root51-edge-audit.md), and the original boundary evidence. Continue R-003/R-042. |
| `90a38a3e`, `1fda811c` — conditional conjunct replay | Exact primitive positive conjuncts of a stable `and` guard now replay through the fallback rule; root 48 proves and forged/missing/overflow-sensitive cases refuse. | The original evidence predates the signed-shift extension and used an older Stage1 product. Root 51 is now closed by the narrow `71ede8b4` slice, but broader conditional-call/replay inventory and current-compiler integration remain open. |
| `576a090f` — benchmark harness responsibility split | The overlong Luna benchmark driver is split into coherent process, validation, and orchestration modules under the source-size limit. | This is maintainability/iteration groundwork, not a verifier speedup; broaden real workload coverage and measure end-to-end test-loop savings under R-011/R-018. |

The detailed acceptance sequence below is retained for reference; §23.17 is the authoritative
re-ranked queue after these additional commits. It begins with reproducible source/product identity
and closure of fail-closed admission gaps, then builds trustworthy real-workload cost evidence,
then optimizes measured repeated work and memory before broadening semantics. Newly landed tests and
build orchestration reduce risk but do not substitute for their remaining source-to-kernel,
full-corpus, crash-recovery, or performance gates. Never use mutable-tree measurements as baseline.

### Phase 0 — trustworthy inputs and exact-current behavior

1. **Review the landed qualified-call change and test expansion (R-003/R-005).** The source patch is
   committed as `57572c60`; the test's forged-summary expansion is still uncommitted. Check exact
   owner/argument/state provenance and run all positive and mutated-trace cases from one immutable
   source snapshot before closing this slice; otherwise revise or discard only the follow-up while
   preserving the reproducer.
2. **Check Stage1 and all build inputs (R-015).** Record compiler binary hash/revision, frontend
   revision, runtime/ABI, flags, target, source-tree digest, and build recipe. Reject stale Stage0
   or mismatched Stage1 provenance before compiling or measuring.
3. **Build proof and replay products from one committed snapshot (R-015).** The build now prepares
   both binaries/manifests/checksums before publishing, serializes writers targeting the same build
   tree, and tests that a replay-link failure preserves the old pair. Verify both manifests and
   executable digests, with matching source/compiler/frontend/runtime/target/options. The final
   path replacements are sequential, so crash-at-each-rename recovery and a single-generation
   activation mechanism remain required; do not describe the pair as transactionally atomic yet.
4. **Refresh the exact-current census (R-001).** Run the qualified-constant reproducer, `Slide.inner`
   conditional cases, call-summary/transport gaps, field-equality positive/refusal cases, recent
   arithmetic gates, kernel core, and representative real-code inputs. Record every complete
   report, refusal, timeout, memory stop, crash, and replay gap; do not call an incomplete report a
   pass.
5. **Preserve the integrated division boundary slices (R-042).** Keep the matched strict Stage1
   unsigned quotient proof/replay and the signed `i64` division/remainder boundary suite in the
   exact-current suite, including high-bit `u64`, negative divisors, divide-by-zero, and
   `MIN_I64 / -1` and `% -1` refusal. These are narrow slices, not the full arithmetic matrix.
6. **Keep unsigned-division adversarial controls fail-closed (R-042).** Preserve zero divisor,
   mismatched width, signed negative dividend, unrelated ceiling, and potentially wrapping sum
   refusals under the same source facts. Add wrong divisor type/cast, high-bit, and equality-boundary
   controls; each report and standalone replay must agree.
7. **Expand the rest of machine arithmetic semantics (R-042).** After the quotient slice integrates,
   work through width/sign-specific remainder, casts, shifts, bitwise operations, signed-minimum
   division, and overflow behavior. State which operations wrap, trap, or are unsupported; never
   infer mathematical-integer laws from an `i64` representation.
8. **Resolve the current R-003 replay inventory.** Trace each current conditional `Slide.inner`
   root and each qualified/nested call witness from source node through producer trace to replay.
   Either add the narrow missing derivation with mutations or make the producer refuse before
   emitting a partial certificate. Keep a useful supported positive case; don't disguise a gap as
   a blanket unsupported result.

### Phase 1 — prove admission and source correspondence fail closed

9. **Bind every call witness to its exact source call (R-005).** Replay the caller declaration,
   call-site node, callee identity, formal-to-actual map, argument position, type/width, place,
   source expression, and pre/post state version. Test same-typed swapped arguments, namespace
   collisions, shadowing, parentheses, nested reference actuals, stale contracts, and alias changes.
10. **Derive the expected obligation inventory from admitted input (R-004).** Compare source
    declarations and supported executable paths with scheduled VCs, completed solver attempts,
    replayed roots, refusals, and unsupported markers. Missing body, branch, imported dependency,
    or unreachable unsupported operation must prevent unconditional `proved`.
11. **Mutation-test every verdict count and route (R-004).** Delete a declaration, obligation,
    attempt, successful proof, finding, or replay record; forge totals; duplicate IDs; and test CLI,
    focused goal, tactic, repair, cache, and package routes. Require structural rejection, not just
    inconsistent display text.
12. **Give checked contexts and binders stable semantic identity (R-007).** Test stale context IDs,
    alpha-renaming, same-spelled nested binders, eigenvariable escape, assumption discharge,
    sibling contamination, arena-generation reuse, and mutation after validation. No name-only
    equality may substitute for binder/declaration identity.
13. **Complete portable and kernel decoder boundary tests (R-006).** Add structure-aware generated
    truncation, duplicate/unknown tags, integer overflow, hostile lengths, escaped surrogate,
    malformed Boolean, child-span, forward-reference, cycle, and version mutations. Check bounded
    CPU/RSS as well as structured rejection; retain minimized corpus seeds for every finding.
14. **Fuzz source import and certificate replay together (R-006/R-088).** Mutate valid source,
    reports, and proof packages with exact one-field semantic corruptions. Assert no panic, crash,
    partial proved output, or timeout escape; whenever producer output is accepted, replay it in a
    fresh process with no AI/solver.
15. **Publish the transitive trust graph (R-008).** Starting from each admitted root, report the
    exact checker rule, adapter premises, source model, compiler/frontend guarantee, runtime/ABI
    assumptions, package version, and external dependencies. Audit every theorem constructor;
    keep trusted constructors private and unsupported assumptions explicit.
16. **Version soundness incidents and invalidate old artifacts (R-009).** Add a semantic rule
    version registry and a confirmed-incident format. Test pre-fix proof packages and cached reports
    against post-fix builds; require replay under the new checker or explicit refusal/migration.
    Cosmetic schema changes must not masquerade as semantic invalidation.
17. **Dispose of P-00 with source-level evidence (R-002).** Attempt to recover the measured crashing
    product/source identity, compare generated indexed-store/lifetime code, and determine whether a
    current source/compiler reproducer exists. Close only with a causal fix and O0/O2 Stage0/Stage1
    plus platform regressions, or a durable unresolved-incident record naming unavailable evidence
    and affected product identities. A crash disappearing is not a causal explanation.

### Phase 2 — establish performance truth before optimizing

18. **Define a stable measurement schema (R-010).** Give each phase and counter a precise owner,
    unit, denominator, scope, overflow policy, and inclusive/exclusive definition. Start with integer
    work counters; use a monotonic clock only through a real compiler/runtime API. Counter failure
    must not affect verifier status.
19. **Instrument search work directly (R-012).** Count goals, visited states, fact scans, equality
    comparisons, candidate rejections, substitutions, rewrites, branch splits, generated terms,
    certificate nodes, replay edges, cache hits/misses, and scratch bytes. Make all accumulated
    work arithmetic checked and keep producer, replay, parser, and memory ceilings independent.
20. **Return actionable budget refusals (R-012).** At every exact and one-over boundary, report
    stage, dimension, observed work, configured limit, and whether any safe partial evidence exists.
    Exhaustion must yield `unknown`/`timeout`/`unsupported`, never `false` and never partial
    `proved`. Confirm the existing 32-name difference-closure behavior remains unchanged.
21. **Version one representative benchmark corpus (R-011).** Pin small interactive, large complete,
    expensive refusal, field equality, composed call, loops/resources, arithmetic/fact growth,
    symbolic quantifier, portable replay, report serialization, no-op/edit, and kernel-core cases.
    Store source hashes, expected outcomes, obligation/certificate counts, and product identities.
22. **Create coherent baseline/candidate snapshots (R-011/R-015).** Use at least seven alternating
    measured pairs after warm-up with the same Stage1/frontend/runtime/target/options. Verify full
    JSON, trust, declaration inventory, certificate count, and replay before comparing time; reject
    changed binaries or manifests before and after the run.
23. **Report a full cost vector for every benchmark (R-011).** Include cold and warm wall time,
    p50/p95, CPU, peak RSS, proof/package/report bytes, obligations, replay count, phase/work
    counters, and cache miss reasons. Treat crash, timeout, OOM, incomplete profile, and measurement
    cancellation as censored outcomes—not fast successes.
24. **Make profiler captures complete and useful (R-014).** Use the available Elisa profiler on a
    large successful proof, a costly refusal, and a small interaction. Record dropped/truncated
    events, capture bounds and instrumented overhead; classify expected nonzero verifier exits
    correctly instead of labelling complete refusal captures partial. Never infer uninstrumented
    speed from an instrumented profile.
25. **Publish fact-growth scaling curves (R-013).** Sweep relevant and irrelevant facts, duplicate
    facts, branch count, equality-graph width, and theorem depth independently around exact budget
    edges. Report actual counters and time/RSS; distinguish linear, quadratic, and capped work.
    Preserve the 12-duplicate proof / 13-duplicate refusal and the richer mixed-fact fixture.
26. **Measure large refusal and timeout behavior (R-013/R-016).** Bound parsing, search, replay,
    diagnostic construction, and serialization separately. Prove that timeout/memory limits cannot
    leak incomplete `proved` output, and that every omitted presentation field has an explicit
    marker and authoritative retrieval route.
27. **Prove summary/full report semantic parity (R-016).** Compare verdict, trust assumptions,
    exact obligation/proven/unproven counts, replay status, and source identity for positive,
    negative, unsupported, and timeout inputs. Then profile peak retained report memory and bytes;
    a smaller JSON document alone is not proof of lower memory.
28. **Measure the actual edit/build/test loop (R-018).** Separately time clean build, no-op build,
    comment-only edit, one prover-file edit, one fixture edit, unrelated source edit, and replay-only
    change. Count compiler, link, runtime-hook, manifest, and test invocations; report cold cache
    and validated-hit costs separately.
29. **Finish dependency-selective build/test scheduling (R-018).** Prove transitive closure and
    runtime/flag invalidation with real builds; map tests to source/feature dependencies; rerun only
    sound focused tests on a narrow edit but retain a full exact-commit release suite. Corrupt cache
    and manifest controls must force rebuilds.
30. **Restore the 600-line responsibility limit.** The committed baseline's `src/app/cli.elisa` is
    614 lines. An uncommitted working-tree change extracts tactic/script dispatch to
    `src/app/cli_tactics.elisa`; it remains unaccepted until visibility, CLI behavior, all
    source-size checks, and a fresh Stage1 build/tests pass on one stable snapshot. Keep coherent
    responsibilities and narrow public/private APIs; do not create numbered private files.
31. **Set ratcheted performance budgets (R-017).** From the accepted baseline, set workload-specific
    p95 latency, throughput, RSS/live-allocation and replay budgets. Start with the stated allocation
    and dominant-phase CPU reduction targets only where profiles identify removable work; record
    platform/variance and permit documented evidence-based revisions, never soundness relaxations.

#### Performance measurement micro-slices — finish before broad algorithm rewrites

These are deliberately separate, commit-sized child gates for R-010–R-018. Their order is
mandatory unless a newly found soundness defect takes priority. “Profiler says X is hot” is a lead,
not proof of a bottleneck; “the run got faster” is not a result until semantic parity and product
identity pass.

**Perf-01 — Freeze source and product identity.** Export a read-only source snapshot and record its
tree digest plus every included input. Bind Stage1 binary/revision, frontend, runtime object/ABI,
target, optimization, flags, build recipe and proof/replay executable digests. Verify the manifest
before and after each sample; abort rather than silently restarting on drift. Keep one output path
per snapshot so concurrent jobs cannot replace the binary under measurement.

**Perf-02 — Version a workload corpus by bottleneck class.** Pin at minimum: tiny interactive
theorem; large complete module; costly refusal; large malformed package; fact-heavy success and
refusal; field equality; call-summary composition; arithmetic widths; loop/resource verification;
symbolic quantification; kernel self-check; standalone portable replay; full-report serialization;
and clean/no-op/local/transitive edit builds. Record source digest, expected verdict, declaration
and obligation counts, trust facts, replay count/gaps, certificate digest and configured limits.

**Perf-03 — Gate timings on full semantic parity.** Compare structured output from baseline and
candidate. Normalize only identified volatile presentation fields; compare source identity,
expected obligations, statuses, assumptions, dependency/trust records, findings, certificates and
replay. Timing is invalid if a crash, timeout, omitted declaration, censored run or changed verdict
is treated as an optimization. Keep full output hashes and explain each normalization.

**Perf-04 — Finish metric definitions.** For every measurement state its owner, unit, scope,
denominator, reset point, overflow policy, inclusive/exclusive status and whether it is a diagnostic
or an enforcement budget. Represent unavailable as unavailable, never as zero. Use checked counter
updates and ensure metric failures cannot change a proof result.

**Perf-05 — Separate external cost from proof cost.** Capture process wall/CPU time, peak RSS,
signals/exit code, timeout/OOM, output bytes, startup, compiler/link/runtime-hook invocations and
harness JSON decoding. Split build, verification, independent replay, package import/export and
orchestration. Report both end-user latency and attributable prover cost; do not subtract unrelated
timers to invent phase measurements.

**Perf-06 — Instrument phase boundaries with real clocks.** Count and, after a valid monotonic-clock
API is available, time source loading, lex/parse, import/resolution, semantic/source admission,
obligation scheduling/generation, candidate search, normalization, certificate formation, replay,
report assembly and serialization. Define nested inclusive/exclusive timing and check that all
exclusive phases reconcile to the parent within documented overhead. Keep disabled mode cheap and
verify its overhead against an uninstrumented binary.

**Perf-07 — Put work counters inside loops.** Count source/AST nodes, declarations, obligations,
facts scanned, comparisons, index probes/collisions, candidate attempts/rejections, rewrites,
substitutions, branch copies/deltas, generated term/certificate nodes, replay edges, cache
lookups/hits/misses, diagnostic bytes and scratch/live allocations. Build small fixtures with exact
counter expectations. This separates algorithmic progress from scheduler noise and enables strict
work ceilings even when wall-time tests are noisy.

**Perf-08 — Calibrate the profiler before using allocation numbers.** With the Elisa profiler,
exercise known-count allocate/free/retain probes and a returned-sview lifetime probe. Reconcile
reserved capacity, committed memory, live/dead-retained nodes, peak live bytes and process RSS.
Record dropped events, truncated captures, stack depth, capture limits and stable source/function
identity. An uncalibrated or incomplete capture cannot select an optimization target.

**Perf-09 — Measure instrumentation overhead explicitly.** Run the same immutable workload as
uninstrumented, counter-only and full-profiler variants. Compare proof report and replay identity,
then quantify time and memory overhead. Use only the uninstrumented paired result for speedup
claims; use captures to locate candidates, not to predict production latency.

**Perf-10 — Profile success and failure shapes.** Capture a small success, a large success, a
high-cost refusal, an expensive replay, and a parser/package rejection. Ensure expected nonzero
program status is distinguished from profiler failure. Summarize self/total time, call count,
allocation and bytes by stable function identity; include setup and serialization so a local kernel
win does not hide a larger end-to-end regression.

**Perf-11 — Separate cold, warm, cached and edited runs.** For each relevant fixture measure cold
process/full build, warm process if supported, validated report-cache hit, certificate-only replay,
comment-only edit, body-only edit, transitive include/contract edit and unrelated edit. Include the
cost of identity calculation, cache validation and publication; a cached verdict is never free or
authoritative without those checks.

**Perf-12 — Publish one-variable scaling curves.** Sweep source size, declarations, obligations,
relevant facts, irrelevant facts, duplicate facts, branch depth, equality graph width, proof-DAG
nodes, package size and dependency fanout independently. Keep inputs deterministic and include
exact budget plus one-over points. Publish raw counters, CPU/RSS and the range over which an
observed linear/quadratic/capped model is justified; do not extrapolate beyond a budget transition.

**Perf-13 — Bound hostile and expensive refusal costs.** Put explicit CPU/RSS/time limits around
large source, deeply nested terms, hostile package lengths, long proof DAGs and fact explosions.
Require bounded structured refusal, no partial `proved`, no partially published cache, and a
precise first exhausted stage/dimension. A refusal that consumes the whole service budget is a
performance bug even when sound.

**Perf-14 — Establish reliable paired statistics.** Warm up identically, alternate candidate and
baseline order, collect at least seven pairs, retain all samples, report median/p95 and spread, and
state platform/background-load caveats. Define outlier handling before collecting data. Overlapping
uncertainty or effects below the noise floor are “inconclusive,” not “faster.”

**Perf-15 — Rank the profile by end-user return.** Attribute total cost across build, load/parse,
source verification, search, replay, memory pressure, serialization and orchestration. Rank
candidates by measured total latency/memory saved per engineering effort and by how many workloads
benefit. Re-profile after each material win; do not keep optimizing the former hotspot after it
moves.

**Perf-16 — Ratchet workload-specific budgets.** Once the coherent baseline exists, set separate
ceilings for interactive p95, large-module completion, refusal termination, replay throughput,
peak RSS/live bytes, allocations, report/certificate bytes and local-edit latency. Keep strict
deterministic work-count gates and variance-aware timing bands. Require repeated breach for noisy
timing thresholds; document exceptions with a reason and review trigger. Budget changes cannot
weaken semantic coverage or adversarial limits.

#### Ordered optimization experiments — measured ROI before feature breadth

1. **Remove wasted build/test work (R-018).** First profile include-closure hashing, dependency
   discovery, compiler starts, link/runtime hooks, test fixture setup and JSON decoding. Reduce only
   the measured term. Confirm unrelated edits trigger no rebuild, while source/include/compiler/
   runtime/ABI/flag changes invalidate exactly the dependent products; checksum corruption forces a
   rebuild. Publish no-op and local-edit latency, not just compiler cache-hit time.
2. **Validate the scalar-name hash index (R-019; `4eb4fec1`).** Retain a scan implementation as an
   independent test oracle. Exercise forced hash collisions, duplicates, empty names, marker
   variants, shadowing, candidate-order sensitivity, wrong widths and wrong sorts. Compare exact
   results and counts; measure total scans, allocations and end-to-end latency on a fact-heavy real
   fixture. A hash match only selects a candidate; a checked witness still proves it.
3. **Remove duplicate replay traversal (R-027).** Count node/root/witness visits on balance,
   lexer, kernel core and package replay. Distinguish repeated traversal from equality, witness
   rediscovery and report duplication. Only then pilot memoization keyed by exact immutable source,
   context, checker-rule version and arena generation; cycle, mutation and stale-handle controls
   must still reject.
4. **Minimize field equality before choosing an algorithm (R-023).** Decompose the real timeout
   into parse, normalization, candidate scan, equality, certificate formation and replay. Compare
   a hash/indexed prototype with proof-producing congruence on the minimized case. Keep wrong-field,
   changed-state, alias, overload/effect, width and binder negatives; require end-to-end paired data.
5. **Index immutable fact frames (R-019/R-024).** Pilot exact proposition, complement, width/domain,
   declaration and disjunction indexes. Build once per frame and preserve deterministic candidate
   order when proof/budget outcomes depend on it. Differentially compare to scanning on late relevant
   facts, malformed markers and collision-heavy cases; require fewer real fact visits, not only
   faster synthetic microbenchmarks.
6. **Make arithmetic witnesses sparse (R-025).** For one real linear/difference workload, store
   only the variables and derivation edges used by the proof. Replay the exact integer/fixed-width/
   wrapping side conditions. Measure search state, proof bytes and replay steps; keep minimum-value,
   overflow and one-over-node-cap controls. Do not silently widen the existing 32-name contract.
7. **Use branch deltas only when copying dominates (R-021).** Measure fact-array bytes copied per
   branch. Replace copies in one branch-heavy proof with immutable parents and explicit additions/
   removals; verify siblings, failed branches, early exits, loops and mutable-place invalidation.
   Memory must scale with the delta without losing assumptions or source provenance.
8. **Cache pure normalization/substitution under full semantic keys (R-022).** Start with immutable
   pure terms; include declaration, overload/type/width, binder/context, region, float mode and rule
   version. Test source edits, shadowing, recursive cycles, cancellation and eviction. Compare
   cached and uncached complete reports; rejected/partial normalization may not become a valid term.
9. **Intern terms only if equality/allocation dominates (R-020).** Pilot typed leaves/operators,
   structural equality after hashing, forced collisions and generation checks. Track hit rate, table
   retention and GC/region lifetime. Reject global unbounded tables and any handle that escapes the
   source or arena generation it denotes.
10. **Reduce peak memory and large-report cost (R-016/R-026).** Separate immutable certificates
    from obligation-local scratch, compact evidence then release scratch, and stream optional
    presentation details while preserving complete authoritative statuses/trust. Measure peak live
    memory and retained capacity, not just serialized JSON size. Stress many sequential obligations
    and cancelled/restarted sessions for leaks.
11. **Parallelize only after dependency and memory models are explicit (R-036).** Partition
    independent declarations by a checked dependency DAG with per-worker budgets. Require
    normalized byte-identical outcomes for jobs=1/N, deterministic failure ordering, bounded total
    memory, cancellation-safe publication and no shared mutable proof context. Parallelism follows,
    not precedes, deterministic scheduling evidence.
12. **Add interactive incremental reuse after cache soundness (R-028–R-035).** Export immutable
    typed frontend artifacts, collect complete dependency edges, invalidate reverse closures and
    persist replay certificates by exact identities. Benchmark cold/full, no-op, local edit,
    dependency edit and restart; compare theorem sets, refusal reasons, completeness and trust
    ledgers against uncached full verification.

#### Performance acceptance and stop rules

- Each experiment begins with a reproducer, minimized workload, profile/counter hypothesis and
  retained baseline or differential oracle. Commit one optimization at a time.
- Compare semantic reports and replay first, deterministic work second, and uninstrumented latency/
  memory third. Any unexplained outcome difference stops the optimization for soundness triage.
- Reject apparent wins that shift cost into an unmeasured phase, depend on weakened limits, omit
  obligations, truncate authoritative evidence, or trade unbounded memory for latency.
- Keep source/product manifests and raw paired samples. Commit a compact evidence record with the
  implementation; preserve incomplete validation and censored samples explicitly.
- After two bounded experiments with no reproducible gain, stop and re-profile/re-rank instead of
  adding more complexity or increasing budgets.

### Phase 3 — optimize only the measured dominant cost

32. **Attribute the replay hot path (R-027).** On balance, lexer, kernel core, and portable replay,
    measure node/edge visits and repeated root/witness checks. Determine whether cost comes from
    duplicate traversal, witness rediscovery, equality work, or report duplication before editing.
33. **Pilot exact-context replay memoization (R-027/R-007).** Cache only immutable checked nodes
    under full source, context, rule-version, and arena-generation identity. Mutated premises,
    stale generations, DAG cycles, wrong sources, and omitted witness steps must still fail.
    Measure nodes avoided, memory retained, and replay CPU with complete parity.
34. **Minimize and attribute field equality (R-023).** Reproduce current completion/timeout under a
    bounded resource envelope. Separate AST normalization, structural equality, candidate scans,
    certificate production, and replay; only then choose congruence indexing versus term sharing.
    Keep wrong-field, changed-state, sort/width, binder, and overloaded/effectful-call negatives.
35. **Add immutable-frame indexes only if scans dominate (R-019).** Pilot equality/complement and
    scalar-width indexes on the measured fact-heavy workload. Compare against a retained scan
    implementation under hash collisions, malformed markers, reordering, and late relevant facts.
    Index hits select candidates; only replayable evidence establishes a fact.
36. **Add branch deltas only if context copying dominates (R-021).** Replace full fact-array copies
    with immutable parents plus explicit additions/removals on one branch-heavy case. Test siblings,
    loop writes, early return, and failed branches for nonleakage; show memory proportional to the
    delta without regressing proof completeness.
37. **Pilot typed term interning only if repeated equality dominates (R-020).** Start with immutable
    leaf/operator terms, including sort, width, declaration, binder, effect, and context identity.
    Force hash collisions and generation mismatch; measure hit rate, allocation saved, retention,
    and total latency before expanding the pilot.
38. **Cache normalization/substitution only with complete semantic keys (R-022).** Include overload,
    type, region, source declaration, checker/rule version, and float mode as applicable. Test
    included-definition edits, shadowing, recursive cycles, cancellation, cached/uncached reports,
    and bounded eviction.
39. **Reduce arithmetic certificate size using sparse evidence (R-025).** Pilot one linear/difference
    case with sparse coefficients and explicit derivation edges; replay exact integer/width/wrap
    side conditions. Compare proof bytes and replay work, and retain min-value, overflow and
    one-over-node-bound refusals.
40. **Reclaim scratch by proof lifetime (R-026).** Separate immutable terms/certificates from
    obligation-local search arenas and release scratch after certificate compaction. Stress repeated
    obligations, long-lived sessions, cancellation, returned sviews, and store-generation reuse;
    validate retained memory and absence of dangling handles.
41. **Optimize the build/test pipeline from its profile (R-018).** If include hashing/closure
    dominates, reduce unnecessary key inputs with dependency evidence; if process startup dominates,
    batch only compatible tests; if compilation dominates, coordinate compiler-side incremental
    support. Keep each optimization isolated and prove stale dependency/runtime changes still
    invalidate all affected products.

### Phase 4 — highest-utility source semantics, one vertical slice at a time

42. **Transport conditional call results through named arguments (R-039).** Instantiate the
    verified callee relation with exact formal-to-actual substitution, including branch guards and
    widths. Prove one real `call_result_order_transport_gap` case; swapped arguments, shadowing,
    altered branch result, false contract, and aliasing writes stay unproved.
43. **Verify one loop traversal with all control edges (R-038/R-040/R-041).** Use a collection
    traversal with an explicit invariant, an early break, and a verified helper. Generate separate
    initiation, preservation, exit, frame, and decrease obligations. Reject missing updates,
    off-by-one bounds, invalid break facts, and a nondecreasing same-SCC recursive call.
44. **Finish total-versus-partial recursion discipline (R-041/R-056).** Require a checked structural
    or well-founded decrease before recursive unfolding in logical summaries. Test mutual recursion,
    lexicographic measures, negative measures, false structural descent, and cyclic proof-summary
    dependencies.
45. **Add an abstract collection model used by real code (R-044/E-01/E-02).** Begin with one
    dynamic-array length/index/push transition and one quantified prefix property. Tie every model
    step to source width, mutation epoch, reallocation, and resource frame; reject stale views,
    invalid indices, and incorrect element/count postconditions.
46. **Prove forwarded-reference framing (R-046/R-049).** Track a caller-place witness through a
    wrapper to a verified mutating callee, then preserve facts about disjoint fields. Alias two
    actuals, forward an unknown index, alter the callee footprint, and forge a place/epoch witness;
    require exact replay rejection.
47. **Close region and string-view lifetime boundaries (R-047/R-050).** Specify `new[r]`, reference
    versus plain-value destinations, mutation/reallocation invalidation, returned `sview` backing
    storage, and region escape. Test shorter-lived backing, wrong region, stale view after resize,
    and value/reference confusion with Stage1 source semantics as the model.
48. **Compose effect and exceptional summaries (R-051/R-052).** Verify one handled and one
    unhandled effect through a wrapper, plus one error/cleanup path. Replay transitive effect
    identity and handler transitions; reject omitted callee effects, spoofed extern rows, leaked
    capabilities, skipped cleanup, and false exceptional postconditions.
49. **Grow checked ADTs from one useful parametric enum (R-055/R-056).** Source-bind a complete
    `Option[T]`-like constructor inventory, generate a motive-checked split, then prove a structural
    induction lemma. Omitted/duplicate constructors, bad type arguments, non-positive recursion,
    skipped cases, and escaped induction hypotheses refuse.
50. **Create reusable math/data lemmas only after the model is stable (R-058/R-061).** Add a
    terminating proof-producing simplifier and a small order/length/lookup-update library. Record
    theorem dependencies and widths; test rewrite cycles, conditional-premise omission, integer
    overflow, and off-by-one variants.
51. **Add checked refinements and abstract module interfaces (R-062/R-063).** Demonstrate one range
    or nonzero refinement and one representation-hiding library contract. Mutating writes invalidate
    refinements; body changes preserve client proofs only when exported interface obligations remain
    checked.

### Phase 5 — dependable interaction, reuse, and practical proof coverage

52. **Make refusal explanations evidence-backed (R-068).** Record actual attempted tiers, candidates,
    premises, resources/effects, dependencies, and budget usage. Test that “unknown” is never
    phrased as false and that every explanation corresponds to a reproducible attempt.
53. **Validate counterexamples against source semantics (R-072).** Replay a candidate model through
    widths, branch conditions, calls, ownership, and effects. Keep invalid solver assignments
    labeled unvalidated; minimize valid witnesses without changing their meaning.
54. **Finish a strict goal/session protocol (R-064/R-065).** Validate the full schema and semantic
    cross-field invariants for IDs, counts, replay, generations, assumptions, pagination, and unknown
    fields. Use compact snapshot IDs and deltas only when reconstructed context exactly matches the
    full report.
55. **Round-trip human proof text into checked terms (R-066).** Parse a small `have`/`apply`/`cases`/
    `rewrite`/`calc` subset, elaborate outside the kernel, serialize proof terms, and replay without
    AI. Missing/ambiguous steps remain open; printed `qed` appears only after replay.
56. **Isolate AI repair candidates (R-069).** Run edits in immutable child snapshots, diff contracts
    and assumptions explicitly, invalidate dependent proofs, and accept only exact replayed results.
    Reject silent precondition strengthening, weaker postconditions, dropped obligations, and
    changed trust assumptions as “fixes.”
57. **Prove a real tokenizer/parser property end to end (R-074/J-01).** Choose a bounded but useful
    Elisa implementation; prove token boundaries/consumption, bounds, error paths, and resource
    preservation. Include malformed-input counterexamples and publish annotation count, unresolved
    roots, proof bytes, replay time, and total checking cost.
58. **Package two reusable verified components (R-081).** Start with a buffer/sequence and a parser
    helper, each with source model, contracts, replayable lemmas, trust summary, and versioned
    dependencies. Demonstrate independent clients and correct invalidation after an interface edit.

### Phase 6 — dogfooding and release assurance

59. **Prove kernel arena invariants without circular admission (R-082/R-083).** Establish bounds,
    generation ownership, immutable-context assumptions, DAG acyclicity, binder scope, and checked
    index arithmetic for a small required declaration set. The theorem set and transitive trusted
    dependencies must be printed and manually reviewed.
60. **Formalize rule soundness separately from implementation correctness (R-084/R-085).** State
    semantics for the admitted fragment; prove core rule preservation in an explicit trusted
    foundation, then relate implementation acceptance to derivations. Do not claim self-hosted
    self-verification removes compiler, runtime, bootstrap, or source-adapter trust.
61. **Verify one compiler pass against an independent model (R-086).** Begin with a small constant
    folding or lexer invariant, use a separately stated evaluator/specification, and check pass
    preconditions/postconditions on Stage1. Minimize every proof-discovered compiler bug into
    Stage0/Stage1 differential regressions.
62. **Cross-check with a genuinely independent replay path (R-087).** Implement a small
    representation/control-flow-independent checker for a fully specified rule subset. Differential
    test every generated certificate in that subset; minimize disagreements and treat any mismatch
    as a release blocker.
63. **Expand mutation/differential qualification (R-088).** Generate valid small source/proof pairs
    and one-step corruptions; compare producer/replay, cache/no-cache, serial/parallel, and Stage0/
    Stage1 behavior. Mutation survivors require explicit justification, not just a high aggregate
    score.
64. **Stage bounded execution and concurrency only behind explicit models (R-073/R-075–R-080).**
    Introduce one bit-precise bounded checker and one synchronization protocol only after their
    source semantics and evidence format are fixed. A bounded success stays bounded; safety never
    implies liveness without fairness/progress proof.
65. **Qualify a release from immutable products (R-089).** Run the complete exact-commit matrix on
    supported macOS/Linux targets, verify package replay with no solver/AI, publish the support and
    trust matrix, review all soundness incidents, and meet ratcheted workload latency/RSS gates.
    Unsupported features and known refusals stay visible in release notes.

**Re-ranking rule:** review this ladder after every five to ten committed slices or whenever a new
red soundness test appears. Promote a new task only with a reproducer, source location, trust impact,
estimated cost, dependency, and falsifiable acceptance gate. Mark a parent R-package complete only
when every required child slice and its original gate are satisfied; a faster run or a higher
proved-count is not sufficient by itself.
- **Reliability:** crashes, timeouts, interrupted/canceled publications, cross-platform disagreements and malformed-input rejection.
- **Maintainability:** responsibility-based module boundaries, under-600-line source compliance, public/private theorem authority and completed evidence-linked commits.

A useful feature closes a real gap with checked evidence. An optimization saves measured work while preserving that evidence. A foundational improvement reduces the amount of code or environmental state that must be trusted. All three are necessary for an efficient, expressive, high-assurance proof assistant.

## 23.17 Re-ranked high-ROI program after the latest committed tranche

This section supersedes the execution order in §23.16; the earlier section remains the detailed
design and adversarial-gate catalog. Its original rebaseline was proof HEAD `f338a42d` plus the
evidence named below; it is retained as a historical snapshot, not the current baseline. The
2026-10-05 refresh and active, more granular schedule are in §23.18. A commit hash does not mean a
single coherent proof/replay product was built from it. Do not benchmark or make current support
claims until product provenance is freshly checked.

**Historical compiler preflight (original §23.17 snapshot only; superseded by §23.18):** the
adjacent `Elisa-compiler` checkout was recorded as clean at
revision `bc8def2eadf41dd088adce22b4d3d9e74aadfee9`; its `scripts/stage1_provenance.py check .
bin/elisac-stage1` reported current at that time, and that product's SHA-256 was
`96eca8200bb268ea5cc1635a66d6b0da0cd85611331319c3227362d9421c2947`. The installed
`~/.elisac/elisac-stage1` wrapper instead pointed to snapshot `7b27fa31`; it was not the latest
compiler and its snapshot did not have the checkout's provenance file. At that time, fresh work
was directed to select the explicitly checked `../Elisa-compiler/bin/elisac-stage1` and matching
runtime and record both identities. This is compiler-input evidence only, not evidence that all of Elisa-Proof at
`ed9e0390` was rebuilt with it. The bounded R-003 root-51 slice has a matched current-Stage1 pair at
proof commit `fcbc4b95` (`ee9ba097`); it closes that root only. A newer focused edge-test pair at
proof commit `b7f5dd74` exercised the added near-maximum and overflow-guard fixtures. Neither pair
is a matched build of the complete current proof HEAD; see the evidence notes and P0.3/P0.5.

### Ranking rules

1. **False acceptance, omitted source obligations, and stale/forged proof evidence outrank all
   feature work.** A refusal is costly; a false theorem can invalidate every downstream use.
2. **Prefer shared infrastructure that closes many root causes.** Exact identities, source-bound
   witnesses, context generations, independent replay, and trustworthy build products multiply the
   value of every later feature.
3. **Performance work must show end-user return.** A lower counter, faster synthetic loop, smaller
   JSON document, or profiler hotspot is only a hypothesis until a complete real workload has
   identical obligations, trust data, verdicts, certificates, and replay results.
4. **Add expressiveness by vertical slice.** Make one useful property provable end-to-end, including
   source correspondence, negative controls, proof-term construction, replay, diagnostics, and
   performance, before generalizing the rule.
5. **Keep each child item independently reviewable and commit after every small validated gain.**
   Record incomplete evidence honestly; never mark a parent R-package done because its easiest test
   passed.

### Landed groundwork: keep its narrow scope explicit

| Groundwork now present | Why it has high ROI | Remaining evidence or implementation |
| --- | --- | --- |
| Source-call witness reconstruction and qualified-target checks (`078aeb9f`, `57572c60`, `b3c9bdef`, current R-003/R-005 follow-ups) | Closes a dangerous gap between a generated call summary and the source call it claims to model. Deterministic-call replay now binds the full six-field AST source span; the focused harness rejects a forged call offset while accepting the restored source trace. | Exact caller/callee declaration identity, all argument and place bindings, generic instantiation, value/reference modes, state epochs, alias/effect/frame provenance, and conditional/control-flow witness replay remain open. See [`docs/evidence/2026-10-05-r005-call-node-span.md`](docs/evidence/2026-10-05-r005-call-node-span.md). |
| Decoder schema and mutation defenses (`c87fc1b9`, `db6f8e5b`, `5118536c`, `1f580f73`, `3f973b55`, `270a1e67`, theorem-cap commits through `a6fb5a42`, `a2ad33ea`, `03c8e3ce`, `01a14d9a`, `64d93a52`, `4827a121`, `ce3211b8`; R-006) | The matrix includes an unknown theorem-reachable node tag, exact/one-over 65,536 theorem count, a missing required top-level `trust` field, a scalar substituted for the required `source` object, and a wrong-type `source.admissible` field with an asserted empty replay result. The latest wrong-type mutation is statically checked but awaits execution against a published pair. The bounded raw-byte run checks 512 mutations and all 16 positive packages in resource-capped processes. | Different immutable corpus snapshots observed three and one valid-mutated encodings respectively; both replayed fully. This remains deterministic, not coverage-guided fuzzing. Every decoder field/valid maximum, cap-adjacent CPU/RSS, source-import fuzzing, and real publication crash recovery remain open. See [`docs/evidence/2026-10-05-r006-required-header-key.md`](docs/evidence/2026-10-05-r006-required-header-key.md), [`docs/evidence/2026-10-05-r006-required-object-type-confusion.md`](docs/evidence/2026-10-05-r006-required-object-type-confusion.md), and [`docs/evidence/2026-10-05-r006-admissible-boolean-type.md`](docs/evidence/2026-10-05-r006-admissible-boolean-type.md). |
| Build preparation and generation-pinned pair publication (`1abf91e3`, `2d7f2aac`, `b7f26cf9`, `04b91100`, `bf2c7158`, `f338a42d`, `9137402c`, `75aee13f`, `982d8b10`, `84cb3ac6`, `c86225dc`, `6dfae1f6`, `5a67377a`, `5d4a3eea`, `df7c61be`, `03e47aab`, `57762e62`, `b74a4064`, `67dba359`, `f865063c`, `8024dc21`, `27e7b849`, `e98696b4`; R-015 evidence) | Same-root locking and staged preparation preserve prior outputs on failed builds; an immutable matched generation with atomic `CURRENT` pointer and pair resolver now rejects incomplete/mixed/tampered pairs. Nine migrated consumers (portable replay, P-05 restart, correlated disjunction, linear certificates, package byte boundaries, package string budget, theorem budget and sview provenance, dogfood package export/replay) resolve and use a matched product generation. A mocked build is also SIGKILLed before pointer replacement; restart resolves the complete old pair, removes the stale lock and publishes a complete new pair. | Many tests, CLI paths, benchmarks, build helpers and documentation commands remain to inventory and migrate. The P-05 and theorem-budget consumers have focused wiring/cap evidence; sview provenance has resolver wiring evidence only because this worktree lacked a published pair. The crash test uses mocked tools at one boundary; real Stage1 crash/restart, immutable source snapshots, multi-root writer coordination, and old-generation retention policy remain open. See [`docs/evidence/2026-10-05-r015-portable-replay-consumer.md`](docs/evidence/2026-10-05-r015-portable-replay-consumer.md), [`docs/evidence/2026-10-05-r015-p05-paired-consumer.md`](docs/evidence/2026-10-05-r015-p05-paired-consumer.md), [`docs/evidence/2026-10-05-r015-correlated-disjunction-consumer.md`](docs/evidence/2026-10-05-r015-correlated-disjunction-consumer.md), [`docs/evidence/2026-10-05-r015-linear-certificate-consumer.md`](docs/evidence/2026-10-05-r015-linear-certificate-consumer.md), [`docs/evidence/2026-10-05-r015-byte-boundary-consumer.md`](docs/evidence/2026-10-05-r015-byte-boundary-consumer.md), [`docs/evidence/2026-10-05-r015-string-budget-consumer.md`](docs/evidence/2026-10-05-r015-string-budget-consumer.md), [`docs/evidence/2026-10-05-r015-theorem-budget-consumer.md`](docs/evidence/2026-10-05-r015-theorem-budget-consumer.md), [`docs/evidence/2026-10-05-r015-sview-wrapper-generation-consumer.md`](docs/evidence/2026-10-05-r015-sview-wrapper-generation-consumer.md), and [`docs/evidence/2026-10-05-r015-build-sigkill-restart.md`](docs/evidence/2026-10-05-r015-build-sigkill-restart.md). |
| Tactic sibling/mutation/stale-context adversarial tests (`c864a3c3`, `7a215424`, `69fc8338`, `e218e4ad`) | Demonstrates that selected context substitution and mutation attacks are caught. A source-level Stage1 O0 runtime harness proves and replays an unchanged split certificate, then mutates a solved child’s captured goal and requires replay refusal. | Stable semantic context and binder IDs, immutable validated inputs, general arena-generation checks, arbitrary AST backing-store mutation, and complete route coverage remain open. The broader CLI branch suite was unavailable in the agent worktree because it had no proof binary. See [`docs/evidence/2026-10-05-r007-postcheck-goal-mutation.md`](docs/evidence/2026-10-05-r007-postcheck-goal-mutation.md). |
| Report-admission inventory checks and result ledger (`93e3a83b`, `2638f329`, `a5898eb4`, `d211b0fa`, `5968eeaf`; R-004) | Declaration summaries are checked against ordered parsed-source inventory; counted obligations require attempts; proven attempts are bound to a matching retained certificate ledger. Stage1 mutations rejected tampered declarations, obligations, attempts, roots, findings, duplicated-proven ledger results, reordered/forged obligation ledger identities, ledger rows and totals. The ledger now binds each result to its source-check accounting-event ordinal. | Event order is not semantic source identity: a checker path that omits recording an obligation entirely remains undetected, and source line/kind/name metadata is not carried by the bool-only producer API. Coordinated AST+report rewriting is outside the tested threat model. All admission routes, source-body/path classification and independent source enumeration remain open. See [`docs/evidence/2026-10-05-r004-obligation-ledger-duplicate.md`](docs/evidence/2026-10-05-r004-obligation-ledger-duplicate.md) and [`docs/evidence/2026-10-05-r004-obligation-ledger-identity.md`](docs/evidence/2026-10-05-r004-obligation-ledger-identity.md). |
| Private certificate producers (`55442e1b`, `767b569a`, R-008) | All five discovered `ProofGoalCertificate` appenders are private; a source inventory regression rejects public visibility. Existing cross-file callers compile and quantifier tactic trace/certificate replay still succeeds on Stage1. | Source visibility and one runtime control do not prove privacy enforcement or producer soundness, cover every certificate-like type, close transitive trust, or prevent mutation through other APIs. Continue R-008. |
| Profiler lifecycle summary and runtime allocation probe (`3dc4dad5`, `a5cba7a7`, `fab7dba0`, `5dfcebba`, `0816f671`, `b4c383fb`, `170083ee`) | Synthetic analyzer calibration is complemented by a real Elisa probe for runtime allocation/reclaim/reset and the production lifetime analyzer; it separately reports logical-live, backing capacity and RSS peaks. A verifier-side negative control rejects a borrow after region destruction with zero replay gaps. The analyzer also refuses a synthetic capture marked complete when stack-overflow event loss is reported. | The event-loss control covers analyzer classification only, not real runtime event emission. No matched uninstrumented baseline or overhead result, real prover profile, phase attribution, or proof-arena census. The lifetime negative control refuses before target execution; arbitrary arena-reset and raw-pointer invalidation routes remain open. See [`docs/evidence/2026-10-05-r014-profiler-event-loss-gate.md`](docs/evidence/2026-10-05-r014-profiler-event-loss-gate.md). |
| Fact-growth scaling evidence (`13f5da2f`, R-013) | A 25-case one-axis harness varies relevant/irrelevant/duplicate facts and match-arm width; 24 cases prove and replay, and the 13-duplicate case refuses at the expected budget. Every process has wall/RSS bounds. | These are bounded sweeps, not asymptotic guarantees or paired optimization evidence; several key solver-work counters and per-goal allocation/time metrics remain absent. The products were built with the then-pinned `7b27fa31` compiler, not the current `bc8def2e` Stage1. Rebuild before current-product claims. |
| Narrow signed/unsigned division slices (`7084c68d`, `f6e18613`, `605710a9`, `6776977c`, `9793a98f`, `b5793019`) | Protects high-risk division edge cases and confirms some exact properties independently replay. | Only selected `u64` quotient and `i64` division/remainder cases; do not extrapolate to other widths or machine operations. |
| Bounded signed unit-shift conditional replay (`71ede8b4`, `fcbc4b95`, `ee9ba097`, boundary tests `3f7cee74`, refusal commits `d196c7a6`, `6c8292e2`, `89fc3b9c`) | A current-Stage1 matched pair closes `Slide.inner` roots 48/51 with 6/6 replay and negative controls; the focused boundary pair proves a safe near-maximum case and refuses an overflowing guard. The exploratory `count > I64_MIN` replay gap is now contained by an exact source-name refusal before certificate emission, with zero gaps in the matched strict O2 check. | This is one exact i64 implication shape; the positive edge-test proof source predates current HEAD. The lower-edge positive remains unsupported, and the refusal recognizes only the `I64_MIN` source constant name. No general conditional arithmetic or all-width guarantee. |
| Semantic benchmark reporting and scalar witness hash lookup (`e972dc02`, `4eb4fec1`, related R-019 tests) | Gives the measurement harness useful classification and a candidate for reducing repeated lookup work. | A complete current corpus and evidence that this index reduces real end-to-end work without outcome drift are still missing. |

### Priority 0 — restore a trustworthy, exact-current verification boundary

Do these first, in order. If a new false acceptance, crash, or replay disagreement is found, stop
the queue and put its minimized reproducer first.

1. **P0.1 — Reconcile in-flight edits into a committed snapshot.** Inspect each modified/untracked
   file, identify its owner and intended semantic change, run its focused tests, keep unrelated
   edits separate, and commit the small validated slices. Require the source-size/responsibility
   check. Do not use a dirty-tree measurement as the baseline.
2. **P0.2 — Prove compiler freshness before building.** Resolve the intended latest Stage1 binary,
   verify its provenance against the exact compiler source revision and frontend/runtime inputs,
   record its digest, target, optimization and ABI, and fail closed on stale Stage0/Stage1 products.
   Keep the proof repository’s pinned compiler identity explicit; do not silently move its pin just
   because a newer compiler exists.
   **Freshness recheck (2026-10-05):** The adjacent compiler checkout is at `ecd26eb7` with
   uncommitted source changes. Its Stage1 provenance check refuses the binary because the current
   source-tree SHA-256 (`e1d9337b…92cda7c`) differs from the recorded input
   (`ccbf9946…23e299d`). The focused freshness evidence is in
   [`docs/evidence/2026-10-05-p02-stage1-provenance-blocked.md`](docs/evidence/2026-10-05-p02-stage1-provenance-blocked.md).
   No stale-product bypass was used; the exact-current matched pair gate remains blocked.
3. **P0.3 — Complete the matched proof/replay build gate.** Build both products from one immutable
   proof source snapshot and one checked compiler/frontend/runtime identity. Verify manifests,
   executable hashes, source-tree digest, options and certificate format; place outputs under a
   unique snapshot path. A one-product or mismatched pair is unusable evidence.
4. **P0.4 — Migrate every proof/replay consumer to generation-pinned products (R-015).** The
   immutable generation directory, shared manifest generation ID, atomic `CURRENT` pointer and
   validating resolver landed in `bf2c7158`; injected pointer/generation and legacy-file
   interruptions passed with mock tools. Inventory every test, CLI, benchmark, build helper and
   documentation command that opens proof and replay binaries. Each paired operation must resolve
   once and use both returned paths from that generation; a stable legacy filename or two separate
   resolves can still mix generations. Keep compatibility aliases only for single-product use.
   The portable replay Python suite, P-05 package-restart, correlated-disjunction,
   linear-certificate, package-byte-boundary, package-string-budget, theorem-budget and sview
   provenance consumers now resolve once
   and use both paths from that generation. The suite's paired-override failure control and real-product run are recorded in
   [`docs/evidence/2026-10-05-r015-portable-replay-consumer.md`](docs/evidence/2026-10-05-r015-portable-replay-consumer.md)
   (`f338a42d`); the P-05 focused wiring guard and scope are recorded in
   [`docs/evidence/2026-10-05-r015-p05-paired-consumer.md`](docs/evidence/2026-10-05-r015-p05-paired-consumer.md)
   (`75aee13f`); correlated-disjunction pairing and its real-product run are in
   [`docs/evidence/2026-10-05-r015-correlated-disjunction-consumer.md`](docs/evidence/2026-10-05-r015-correlated-disjunction-consumer.md)
   (`c86225dc`); linear-certificate pairing is in
   [`docs/evidence/2026-10-05-r015-linear-certificate-consumer.md`](docs/evidence/2026-10-05-r015-linear-certificate-consumer.md)
   (`5a67377a`); package-byte boundaries are in
   [`docs/evidence/2026-10-05-r015-byte-boundary-consumer.md`](docs/evidence/2026-10-05-r015-byte-boundary-consumer.md)
   (`df7c61be`); package-string-budget pairing and its over-budget refusal are recorded in
   [`docs/evidence/2026-10-05-r015-string-budget-consumer.md`](docs/evidence/2026-10-05-r015-string-budget-consumer.md)
   (`57762e62`); theorem-budget cap evidence is in
   [`docs/evidence/2026-10-05-r015-theorem-budget-consumer.md`](docs/evidence/2026-10-05-r015-theorem-budget-consumer.md)
   (`67dba359`); and sview provenance resolver wiring is in
   [`docs/evidence/2026-10-05-r015-sview-wrapper-generation-consumer.md`](docs/evidence/2026-10-05-r015-sview-wrapper-generation-consumer.md)
   (`8024dc21`). In addition, the dogfood kernel-package export/replay operation resolves one pair
   and uses both paths from that generation; a focused static guard passes and is documented in
   [`docs/evidence/2026-10-05-r015-dogfood-package-pair.md`](docs/evidence/2026-10-05-r015-dogfood-package-pair.md).
   These are nine consumers, not full migration. Other paired consumers and the build/recovery gaps
   below remain open.
   A mocked-tool process-kill/restart check now kills the build before `CURRENT` replacement, then
   resolves the old complete pair and verifies a later build publishes a new complete pair
   (`27e7b849`, `e98696b4`). Mocked independent-root concurrency and post-copy source-mutation
   controls now pass; they do not exercise real Stage1 writers or mutation during an active copy.
   Next add real Stage1 crash/restart coverage, active-copy source-mutation handling, and safe
   old-generation retention/cleanup. Recovery must expose a complete old or new pair, never a
   mixed one.
5. **P0.5 — Refresh the exact-current admission census.** Run, from that one matched product pair,
   the qualified-constant reproducer, each `Slide.inner` conditional gap, qualified/nested call
   cases, forged-summary controls, field-equality success and timeout/refusal, fact-budget edges,
   arithmetic boundaries, package corruption corpus, kernel core, and selected compiler/mocap
   sources. Store complete reports, certificate/replay totals, refusal categories, run limits, and
   product identities. Any crash, timeout, missing report, or replay gap is first-class census
   output, not a pass.
6. **P0.6 — Resolve the qualified-constant crash incident (P-00/R-002).** Recover the original
   measured binary if possible, retain the minimal qualified-constant trigger and passing controls,
   compare generated code and compiler revisions, and use debugger/profiler evidence to identify
   the invalid operation. Fix the responsible proof/runtime/compiler layer; never mask it with a
   broad unsupported result. Keep a compiler differential if the source lowering is responsible.
7. **P0.7 — Close producer/replay gaps without losing valid paths (R-003).** Preserve the narrow
   root-48 positive-conjunct rule and its negative controls. Root 51 now has a narrowly shaped,
   fixed-width-safe signed unit-shift replay rule (`71ede8b4`, hardened against circular guard
   range evidence by `fcbc4b95`); `ee9ba097` records a matched current-Stage1 pair for that bounded
   root. Added near-maximum and overflowed-guard controls (`3f7cee74`) also pass on a matched current
   Stage1 pair, but its prover source is older than the current HEAD. Trace every remaining
   conditional-return gap from source CFG node through VC, witness, certificate and replay. A
   follow-up found and fixed an unsigned-sort producer/replay mismatch: the conditional signed-shift
   fallback now refuses unsigned `u64` before goal certification. A fresh strict O2 matched pair at
   source snapshot `6753e0df` reported zero replay gaps and an uncertified u64 ensure goal; see
   [`docs/evidence/2026-10-05-r003-root51-edge-audit.md`](docs/evidence/2026-10-05-r003-root51-edge-audit.md).
   A separate `count > I64_MIN` replay gap is now contained by a narrow producer refusal keyed to
   that source constant name; regression and matched strict O2 evidence are recorded in
   [`docs/evidence/2026-10-05-r042-i64-min-positive-refusal.md`](docs/evidence/2026-10-05-r042-i64-min-positive-refusal.md)
   (`89fc3b9c`). This closes the gap for the exact reproducer, not positive lower-edge proof support.
   Add only the smallest branch-preserving rule or refuse before emitting incomplete evidence. The
   integrated latest-HEAD pair remains required before a current whole-product claim.
8. **P0.8 — Bind every call proof to exact source semantics (R-005).** Deterministic-call replay
   now binds the full six-field source span of the exact call node (`b3c9bdef`); the focused Stage1
   mutation rejects a forged offset and accepts the restored trace. Validate caller and callee IDs,
   ordered/named actuals, generic instantiation, value/reference mode, places,
   aliasing, widths/sorts, state version, contract digest, effect row and footprint. Differentially
   mutate each field and require both focused and package replay to refuse the forged trace.
9. **P0.9 — Make obligation completeness structural (R-004).** The first report-inventory gate
   (`93e3a83b`) compares declaration summaries with ordered parsed-source inventory, requires an
   attempt for every counted obligation, and validates proven attempts against a sequential matching
   certificate ledger. Stage1 mutations rejected tampered declaration, obligation, attempt, root,
   finding and aggregate fields; a runtime control rejected a duplicate proven result for an open
   obligation (`a5898eb4`). Ledger rows now carry and validate an accounting-event ordinal;
   Stage1 mutations reject reordered entries and a forged ordinal (`5968eeaf`). This ordinal is not
   source-semantic identity, and omitted ledger events remain undetected. Extend this to
   executable-path inventory and classifications
   (checked/refused/unsupported/checked-unreachable), independently derive body/branch counts, and
   exercise every CLI, cache, tactic, repair and package admission route. Whole-AST plus whole-report
   coordinated rewriting is not covered by the current threat model; document or close it explicitly.
10. **P0.10 — Give checked contexts immutable identity (R-007).** A source-level Stage1 O0 runtime
    control now accepts an unchanged checked split child and rejects replay after its captured goal
    is mutated (`e218e4ad`). Add semantic context and binder IDs plus arena generations;
    constructors remain private, and validation binds to immutable snapshots. Extend the three
    branch mutation regressions with stale handles, same-spelled nested binders, broader post-check
    AST mutation, escaped eigenvariables, failed branches, nested tactics,
    scratch reuse, and concurrent access. Compare accepted certificates to a simple independent
    context-membership oracle.
11. **P0.11 — Finish decoder/parser adversarial coverage (R-006/R-088).** The structured matrix now
    includes unknown theorem-reachable tags, a missing required top-level `trust` field, a scalar
    in place of the required `source` object, exact/one-over theorem count, and a `source.admissible`
    wrong-type assertion (runtime pair execution is pending for the last mutation); the established
    schema mutations return structured refusal with empty theorem results. A matched pair checked
    512 deterministic raw-byte mutations in fresh bounded processes and replayed all 16 positives.
    Three valid-mutated encodings replayed in one immutable snapshot; one did in the later boundary
    slice. This is not coverage-guided fuzzing. Extend with generated valid source and packages,
    mutate one byte/field at a time, and cover every tag, Boolean/integer encoding, span,
    object key, UTF-8/surrogate rule, version, count, length, reference, root and checksum. Impose
    process CPU/RSS bounds; retain seeds and assert structured refusal, no panic, no partial `proved`,
    and no partial cache publication.
12. **P0.12 — Publish the executable trust graph (R-008/R-009).** Enumerate every theorem/proof
    constructor and every public admission route. For each accepted root expose kernel rule,
    adapter assumptions, compiler/type-system guarantees, runtime/ABI assumptions, solver and
    package versions, and dependencies. Connect incident records to actual cache/package invalidation;
    demonstrate that a pre-fix artifact is replayed under the new semantic version or refused.

### Priority 1 — make performance visible, reproducible, and bounded

These are measurement gates, not optimization claims. Complete them before broad algorithm rewrites.

13. **P1.1 — Pin a workload corpus by semantic shape (R-011).** Include tiny interactive proof,
    large complete proof, high-cost unknown, parser/package refusal, kernel core, field equality,
    compositional call, region/ownership, arithmetic widths, quantifier, loop, fact growth,
    certificate-only replay, summary/full serialization, no-op build, local edit and transitive edit.
    Pin bytes/hash, expected obligations/status/trust, proof/replay counts, budgets and compiler ID.
14. **P1.2 — Complete per-run phase/work accounting (R-010/R-012).** Define counter owner, unit,
    scope, reset, overflow and inclusive/exclusive semantics. Count nodes, declarations, obligations,
    fact scans, comparisons, index probes/collisions, candidate attempts, substitutions, rewrites,
    branch copies, term/certificate nodes, replay edges, cache operations, diagnostic bytes and live
    scratch. Counter overflow and clock failure must not change the proof verdict.
15. **P1.3 — Make resource exhaustion precise and independent.** Give import, normalization, search,
    certificate generation, replay, decoder, report building, cache, and wall/RSS limits independent
    names and counters. At exact and one-over boundaries report stage/dimension/observed/limit;
    return `unknown`, `timeout`, or `unsupported`, never `false`, no model, and no partial theorem.
16. **P1.4 — Complete profiler calibration and measure overhead (R-014).** The real runtime probe
    (`5dfcebba`) now covers known allocation/reclaim/reset events and the production analyzer, and
    reports logical-live, retained-capacity and RSS separately. The destroyed-region `sview`
    refusal control (`0816f671`) has zero replay gaps but does not dereference stale storage. A
    synthetic analyzer control (`170083ee`) rejects a purported complete capture when stack-overflow
    event loss is present; real event-emission loss/truncation behavior remains unverified. A new
    synthetic analyzer control models nested proof stores with distinct arena IDs and source sites;
    the analyzer keeps the inner reset's 30 ns lifetime separate from the outer allocation's 80 ns
    lifetime and resolves both supplied source locations. This checks accounting for hand-authored
    events only. Runtime emission of nested-store identities/source stacks remains unverified. See
    [nested-store analyzer control evidence](docs/evidence/2026-10-05-r014-nested-store-analyzer-control.md).
    Add profiler-noninterference controls. Then
    capture one matched uninstrumented/counter-only/full-profiler run with identical products,
    workloads, reports and replay; quantify wall/CPU/RSS overhead before using profiles to select a
    hot path. The existing probe makes no claim that a returned view remains valid after reset.
17. **P1.5 — Capture representative prover behavior.** Profile one small success, large complete
    success, expensive refusal, large replay, and malformed-package rejection. Keep incomplete or
    dropped captures out of hot-path selection. Attribute self/total time, call counts, allocations,
    retained arena capacity and RSS separately; include CLI/report overhead.
18. **P1.6 — Quantify instrumentation overhead.** On identical source/product/workload, compare
    uninstrumented, counter-only and fully profiled executions with identical reports and replay.
    Publish added wall/CPU/RSS and event loss. Use captures to locate work but only uninstrumented
    paired runs to claim a speedup.
19. **P1.7 — Produce one-variable scaling curves (R-013).** Independently scale facts, relevant vs
    irrelevant premises, duplicate facts, branches, equality width, goals, AST size, certificate DAG,
    package bytes and dependency fanout. Include exact cap and one-over fixtures; publish observed
    work, CPU, RSS and confidence range rather than extrapolating asymptotics from a single point.
    The landed relevant/irrelevant/duplicate-fact and match-width sweep (`13f5da2f`) is a useful
    first slice only: add explicit fact-visit/comparison, branch-copy/join and allocation counters
    before using it to choose an index or cache redesign; rerun on the current compiler and matched
    products. The `count > I64_MIN` replay gap is contained by a narrow refusal before certificate
    emission (R-042), but a durable positive near-`i64::MIN` premise case and a general lower-edge
    replay rule remain open arithmetic coverage targets. Do not call its 25
    samples a general complexity bound.
20. **P1.8 — Establish coherent paired baselines (R-011/R-015).** Use at least seven alternating
    baseline/candidate rounds after warmup, with source and executable manifests checked before and
    after each batch. Compare exact semantic JSON, trust roots, declaration/obligation inventory,
    refusal reason, certificate and independent replay before accepting timing. Preserve all samples,
    median, p95, spread and censored runs.
21. **P1.9 — Bound refusal and report cost (R-013/R-016).** Stress huge but bounded sources,
    hostile package lengths, deeply nested terms, massive diagnostics and many failed obligations.
    Measure peak retained report memory, serialization bytes, scratch high-water marks and timeouts;
    a smaller summary JSON is not a memory win unless retained allocations fall too. Keep omitted
    details explicitly marked and retrievable from authoritative full evidence.
22. **P1.10 — Measure the actual build/test loop (R-018).** Record clean build, no-op build,
    comment-only change, one verifier-module edit, fixture-only edit, unrelated source edit,
    transitive include edit, replay-only edit, and full test-suite time. Count compiler/link/runtime
    hook/manifest/test invocations. Add sound test-to-source dependency mapping; keep an exact-commit
    full release suite even after focused selection exists.
23. **P1.11 — Set ratcheted cost budgets (R-017).** After coherent baselines exist, set separate
    thresholds for interactive p95, large proof completion, refusal termination, replay throughput,
    peak RSS/live bytes, allocations, artifact sizes, no-op build and local edit. Enforce exact work
    ceilings deterministically; require repeated timing breaches and variance-aware review. No budget
    increase may weaken semantic or hostile-input coverage.

### Priority 2 — remove repeated work, ordered by measured end-to-end return

The order below is the default experiment queue, not permission to guess at hotspots. Re-profile
after each accepted optimization; skip or defer an experiment if counters show its cost is
insignificant on real workloads.

24. **P2.1 — Eliminate unnecessary build and harness work first.** Profile include closure walks,
    hashing, Python startup, compiler startup, linker/runtime hooks, test fixture setup and report
    decoding. Make no-op and unrelated-file edits avoid only proven-independent work; edits to
    compiler/frontend/runtime/ABI/flags or a transitive source must invalidate precisely the
    affected product. Use the R-015 manifest and corruption tests as stale-reuse controls.
25. **P2.2 — Verify the scalar-witness index against an independent scan oracle (R-019).** Force
    hash collisions; cover duplicate/empty names, marker normalization, shadowing, sort and width
    mismatch, malformed entries, and order-sensitive candidates. Compare exact witness selection
    and refusal, then measure fact visits, allocations and end-to-end latency on real fact-heavy
    cases. Keep hash equality only as candidate selection, never as proof.
26. **P2.3 — Reduce disjunction candidate work without dropping valid proofs (R-024).** Count scan
    work for early/late relevant facts, alternatives that are refuted, mixed domains and budget
    exhaustion. Compare indexed candidate selection to the retained implementation and preserve
    disjunctive syllogism and late-premise success. Producer and replay must agree at the cap.
27. **P2.4 — Remove repeated replay traversals (R-027).** Measure proof-DAG node/root/witness visits
    in successful and refused proofs. First eliminate demonstrable duplicate walks; only then try
    memoization under immutable source, exact context, rule version and arena generation. Mutation,
    cycles, omitted witnesses and stale handles remain rejection tests; compare proof bytes, visits,
    memory and replay CPU.
28. **P2.5 — Diagnose and fix the field-equality bottleneck (R-023).** Minimize the expensive real
    source, separate import, term normalization, candidate scan, equality, proof construction and
    replay, then choose indexed structural equality or proof-producing congruence. Preserve wrong
    field, alias, changed state, overload/effect, width and binder negatives; require proof of the
    same positive obligation and paired end-to-end improvement.
29. **P2.6 — Add immutable frame indexes only where scans dominate (R-019).** Pilot exact fact,
    complement, declaration, sort/width and disjunction indexes. Preserve deterministic order and
    the scan oracle, account index build/retention cost, and show reduced visits/allocation on the
    real corpus. Mutated or malformed marker entries must not become facts.
30. **P2.7 — Shrink arithmetic evidence rather than materializing dense closure (R-025).** Pilot
    sparse coefficient maps or shortest-path derivation edges for one measured linear/difference
    case. Replay exact integer/fixed-width/wrap side conditions and compare search memory, proof size
    and checker work; keep `i64` min/max, overflow, and exact/one-over-node caps.
31. **P2.8 — Replace copied branch facts with persistent deltas only if copy cost is material
    (R-021).** Track modified-place invalidation as explicit deltas. Compare memory by branch depth
    and width; test sibling isolation, failed branches, early returns, loop writes, nested cases and
    post-check mutation against the current copied-context oracle.
32. **P2.9 — Bound report construction and serialize details lazily (R-016).** Separate essential
    verdict/trust/obligation data from optional explanations and AST details; stream optional data
    when safe. Compare full versus summary semantic parity and peak live memory, not just output
    bytes. Never omit data required to establish completeness or replay.
33. **P2.10 — Reclaim obligation-local scratch at the correct lifetime (R-014/R-026).** Separate
    immutable terms and certificates from temporary search arrays, branch copies and diagnostics.
    Repeatedly verify large files, cancel/restart sessions and return `sview`s; require stable live
    memory, retained-capacity accounting and no dangling view/region handle.
34. **P2.11 — Pilot typed-term sharing and normalization caches last among local optimizations
    (R-020/R-022).** Begin with immutable typed leaves and operators. Keys must include sort, width,
    declaration, binder/context, effect, region, float mode, source revision and rule version as
    applicable. Force collisions, edits, shadowing, cycles, cancellation and eviction; cached and
    uncached proof reports/replay must match exactly.
35. **P2.12 — Parallelize declarations only after dependency/resource isolation (R-036).** Partition
    a verified dependency DAG; use per-worker budgets and aggregate memory ceilings. Compare jobs=1
    and jobs=N for identical deterministic output, diagnostics and proof roots. Cancelled workers
    cannot publish stale evidence; failure ordering remains stable.
36. **P2.13 — Add incremental artifacts only after identities and reverse dependencies are complete
    (R-028–R-035).** Persist typed artifacts and certificates by content/rule identities, invalidate
    exact reverse closures, replay on reload and test crash-safe cache publication/eviction. Measure
    cold, no-op, local, transitive, interface, restart and cache-corruption cases against uncached
    full verification. A cache miss may cost time; it must never change truth.

### Priority 3 — highest-value verification capabilities, each as a vertical slice

Implement these only after the source/admission/replay boundaries above can represent them
faithfully. The first practical target is modular functional correctness for sequential Elisa,
then ownership/effects; concurrency and liveness follow much later.

37. **P3.1 — Complete machine arithmetic in small width families (R-042).** Specify bit-vector
    semantics for every supported integer width and operation: signed/unsigned add/sub/mul/div/rem,
    casts, comparisons, shifts, bitwise ops and overflow/trap/wrap. Generate exhaustive small-width
    truth tables plus 8/16/32/64-bit boundaries; compare source, tactic, producer, portable package
    and kernel replay. Never lift a machine operation to unbounded integer algebra without checked
    range premises.
38. **P3.2 — Verify one modular call-summary composition gap (R-039).** Start with a pure helper
    returning a value through a conditional postcondition. Substitute exact named/positional actuals,
    branch guard and state versions. Prove a real previously-unproved caller while swapped args,
    false contracts, changed bodies, aliases and hidden effects remain unknown/refused.
39. **P3.3 — Consolidate weakest-precondition generation (R-038).** Express assignment, sequence,
    branch and return with one typed state-substitution layer; distinguish partial from total
    correctness. Cross-check small generated programs against an independent bounded interpreter,
    including early return, dead code and side effects.
40. **P3.4 — Prove one real loop with explicit invariant (R-040).** Generate initiation,
    preservation, exit, frame and variant obligations for one collection traversal with break or
    continue and a verified helper. Test omitted updates, off-by-one bounds, invalid exits, aliasing
    writes and non-preserved resources. Bounded unrolling may not be called an unbounded proof.
41. **P3.5 — Require termination evidence for logical unfolding (R-041).** Add structural and one
    well-founded measure slice, then test mutual recursion, lexicographic order, negative measures,
    false descent and cyclic SCC summaries. Partial program recursion and total logical definitions
    must remain visibly distinct.
42. **P3.6 — Verify one dynamic-array/sequence model (R-044).** Tie length, indexing, push, update,
    capacity growth and element ownership to a source-derived mutation epoch. Prove one quantified
    prefix property; reject invalid bounds, stale views, wrong length, reallocation aliasing and
    forged model transitions.
43. **P3.7 — Complete canonical places and forwarded-reference framing (R-046/R-049).** Preserve
    place identity through wrappers, calls, indexing and fields. Prove a mutating callee preserves a
    disjoint field; test two aliased actuals, unknown indices, pointer-like references, stale epochs,
    altered footprints and untracked forwarded parameters.
44. **P3.8 — Close `new[r]`, regions, values/references and `sview` lifetimes (R-047/R-050).** Model
    allocation region, destination representation, backing storage and mutation/reallocation
    invalidation. Verify that a present view always names live backing for its full lifetime; reject
    escape to a shorter-lived region, value/reference confusion, wrong region and stale view.
45. **P3.9 — Compose effects, handlers, errors and cleanup (R-051/R-052).** Verify one handled and
    one unhandled effect across a wrapper and one failure/cleanup path. Replay exact effect rows,
    handler transition and exceptional postcondition; reject omitted effects, spoofed externs,
    leaked capabilities and skipped cleanup.
46. **P3.10 — Add checked ADT cases, induction and disciplined quantifiers (R-055–R-057).** Begin
    with a parametric option/list-like declaration and explicit motive. Source-bind constructor
    exhaustiveness and recursive positivity; keep induction hypotheses scoped and prevent
    eigenvariable escape. Omitted constructors, wrong type arguments and malformed motive refuse.
47. **P3.11 — Add terminating simplification and reusable lemma libraries (R-058/R-061).** Use a
    deterministic measure/priority scheme, record every rewrite premise and emit replayable steps.
    Test cycles, conditional-premise omission, overflow-sensitive identities and rewrite-order
    stability; deliver a small tested arithmetic and collection library.
48. **P3.12 — Introduce ghost state, refinements and abstract interfaces only with invalidation
    rules (R-053/R-062/R-063).** Prove a nonzero/range refinement and one representation-hiding
    module contract. Mutating source state invalidates refinements; implementation edits preserve
    clients only when the exported verified summary remains identical.

### Priority 4 — make the system efficient and usable for people and agents

49. **P4.1 — Stabilize the versioned goal/query API (R-064/R-065).** Return structured snapshots
    containing exact proposition, typed hypotheses, binders, resources/effects, dependencies, trust,
    attempt history, budget usage and replay state. Use compact IDs/deltas only with exact generation
    validation, pagination and a full-report fallback.
50. **P4.2 — Make failure explanations derive from actual search (R-068).** Distinguish proved,
    disproved with validated counterexample, unknown, timeout, unsupported, incomplete and trusted
    assumption. List attempted engines, premises, resource requirements and first budget exhausted;
    mutation-test explanations against the underlying attempt log.
51. **P4.3 — Add checked counterexamples and bounded execution (R-072/R-073).** Validate solver or
    bounded-model assignments by replaying source widths, branches, calls, ownership and effects.
    A bounded success includes its bound and is never promoted to an unbounded theorem; invalid
    candidate models stay explicitly unvalidated.
52. **P4.4 — Round-trip a small human proof language (R-066).** Parse and elaborate `have`, `apply`,
    `cases`, `rewrite` and `calc` outside the kernel; serialize proof terms and replay from a fresh
    process. Print completion only after replay; ambiguous names or missing premises remain goals.
53. **P4.5 — Add deterministic lemma search and solver portfolios with reconstruction (R-067/R-070/
    R-071).** Schedule cheapest adequate tactic first, impose a shared explicit budget, record tool
    versions/options, and reconstruct every successful answer as a kernel proof. Solver `sat`, `unsat`,
    or process exit alone never changes theorem status.
54. **P4.6 — Isolate AI repair suggestions (R-069).** Apply each edit in an immutable child snapshot,
    display contract/assumption changes and broken dependents, rebuild exact obligations, then admit
    only replayed results. Reject silent precondition strengthening, weaker guarantees, omitted roots
    and trust changes.
55. **P4.7 — Verify a useful parser/protocol path and package components (R-074/R-081).** Prove one
    bounded parser/tokenizer property with resource bounds and malformed-input counterexamples, then
    package a sequence/buffer and helper with reusable contracts, client replay and sound interface
    invalidation.

### Priority 5 — dogfood without circular reasoning; advanced properties last

56. **P5.1 — Freeze a self-verification scope matrix (R-082).** Name exact kernel, elaborator,
    importer, tactics, certificate codecs, source adapters, runtime/compiler assumptions and
    explicitly excluded code. Publish trusted lines/modules and proof roots; do not call the whole
    assistant verified because selected helper lemmas pass.
57. **P5.2 — Prove kernel data-structure invariants (R-083).** Check arena bounds, generation
    ownership, context immutability, DAG acyclicity, binder scope and checked arithmetic using a
    proof route independent enough to expose implementation mistakes. Manually review all
    transitive trust dependencies.
58. **P5.3 — Specify the calculus and prove rule soundness (R-084).** State source/model judgments
    and rule premises in an explicit trusted foundation, then prove each admitted rule preserves
    semantics. Distinguish a theorem about an abstract rule from a theorem that Elisa code correctly
    implements that rule.
59. **P5.4 — Relate implementation to specification (R-085).** Connect concrete kernel data and
    decision procedures to the formal model through refinement lemmas and executable checks. Avoid
    self-hosting circularity; retain compiler, runtime, bootstrap and source-adapter assumptions.
60. **P5.5 — Verify one compiler pass against an independent semantics (R-086).** Start with a small
    lexer invariant or constant-folding pass. Build Stage0/Stage1 differential controls and turn
    every proof-discovered compiler defect into a reduced regression before expanding scope.
61. **P5.6 — Build an independent checker and mutation campaign (R-087/R-088).** Implement a
    representation/control-flow-independent checker for one complete proof subset; differentially
    check every producer certificate and generated one-field mutation. Any cross-check mismatch is a
    release blocker.
62. **P5.7 — Add concurrency, protocol liveness and temporal reasoning only after a sound model
    exists (R-075–R-080).** Specify happens-before, atomicity, invariants, ownership transfer,
    fairness and progress before adding Iris/TLA+-like automation. Test races, deadlocks, starvation
    and invalid fairness assumptions. Safety never implies liveness.
63. **P5.8 — Qualify and continuously renew the release (R-089/R-090).** Run exact-commit
    macOS/Linux matrices, no-AI/no-solver package replay, adversarial corpus, trust/incident review,
    coverage and performance budgets. Keep unsupported semantics and known limitations explicit;
    after every five to ten commits, rerank using new evidence and preserve prior incident history.

### First execution batch from this ranking

The original immediate batch above was written against its historical baseline. Use §23.18 for the
current order: first close the in-flight source-bound summary/replay gap; next publish one exact,
matched product baseline; then measure complete workloads before selecting optimizations. P0.6
continues only when the original crash product or reproducer can be investigated without
contaminating shared build outputs. Do not skip directly to term interning, broad solver portfolios,
temporal logic, or self-hosted proofs: close source/admission gaps and identify dominant costs first.

For every numbered slice, attach: source commit/tree digest; exact Stage1/frontend/runtime/target
identity; focused and adversarial test commands/results; full proof and independent replay outcomes;
work/latency/memory measurements when relevant; unresolved limits; and links to the changed R-package
and evidence note. Commit the implementation, tests and concise evidence as a small reviewable unit.

## 23.18 Active high-ROI execution plan after the latest sentinel tranche

**Rebaseline (2026-10-05).** The committed proof baseline is `a60d8f59`, which expands the P-01
semantic-shape sentinels with unsigned-boundary, quantifier and region-lending workloads. The
sentinel manifest check passes; the published-pair run documented in
[`docs/evidence/2026-10-05-r011-sentinel-corpus-follow-up.md`](docs/evidence/2026-10-05-r011-sentinel-corpus-follow-up.md)
used source-dirty products and is not current integrated-build qualification. The current proof
worktree contains in-flight edits to replay summary/source-call validation and a temporary
diagnostic script; the alias-result regression still reports a replay gap. Treat those edits as
investigation, not a completed fix. The current adjacent compiler checkout is dirty at `ecd26eb7`
and its Stage1 product fails provenance validation. The pinned compiler snapshot at `7b27fa31`
passes its own provenance check but is not the latest checkout. Thus the immediate build gate is a
coherent pinned pair, while latest-compiler qualification remains a separately visible blocker.

This section converts the broad R-001–R-090 backlog into the next executable slices. Its ordering is
deliberate: prevent invalid evidence and close already-observed false negatives; obtain an honest,
repeatable performance baseline; remove proven duplicated work; then expand the highest-frequency
verification cases. A capability or optimization is not complete until the source import, producer,
certificate, independent replay, report and package paths agree. Apply §3's small-commit rule after
each passing slice. When new evidence changes the ordering, update the queue instead of silently
skipping a gate.

### Gate A — close current correctness and provenance risks before feature work

1. **A1 — Finish the call-summary alias replay repair (R-005/R-039).** Minimize
   `open_pure_call_domain` and `repeated_pure_call_domain`; establish why a summary whose call result
   is first stored in a local and then returned is not authenticated by the replay source walker.
   Bind the summary to the exact caller declaration, exact call AST node/span, exact callee identity,
   ordered actual arguments, named-argument mapping, parameter names/types, result destination and
   state/version facts. Only accept a local result when the source proves that the exact call
   initializes that exact local on the corresponding path. Add direct-return, initialized-local,
   renamed-local and supported named-argument positives; add wrong-callee, swapped actuals,
   wrong-local, shadowing, reassignment, two same-line calls, duplicate callee names, branch-only
   initialization and forged-span negatives. Require producer proof plus independent replay with
   zero gaps; otherwise keep the summary unsupported. This is the first code task because the
   currently observed gap withholds otherwise useful proofs and the same boundary could become a
   soundness defect if loosened carelessly.
2. **A2 — Make source-site matching unambiguous under repetition and control flow.** Exercise two
   identical calls on one source line, nested calls, calls in arguments, branches and loop bodies.
   If a source span alone does not identify the occurrence, add a stable AST path or occurrence ID
   whose derivation is checked from imported source; never choose the first same-name/same-line
   candidate. Mutation-test every span/path component and verify deterministic failure on ambiguous
   or truncated correspondence.
3. **A3 — Validate all summary inputs, not only the callee name.** Independently derive the
   parameter-to-actual substitution from source resolution and compare it with certificate
   bindings, including named/positional mixtures, defaults, generics, aliases, references and
   machine widths. Change one recorded binding at a time and require both direct replay and package
   replay to reject it. A producer-side agreement test alone is insufficient because producer and
   replay may share the same bug.
4. **A4 — Preserve independent falsification controls for the repair.** Run the existing disjunction
   domain and search-bound suites plus the generic package, portable replay, call-summary and
   source-mutation suites on the exact same binaries. The intended positives must replay; false
   postconditions, wrong guards and forged call evidence must remain unproved/refused. Record the
   exact first failing assertion, not just the test process exit status.
5. **A5 — Remove scratch diagnostics and freeze a clean proof snapshot.** Keep useful minimized
   regressions and source-level harnesses; delete temporary debug scripts and generated products
   from the commit. Check `git diff --check`, source-file limits, public/private boundaries and
   the exact changed-file list. Commit only the validated replay fix and its tests/evidence, leaving
   unrelated in-flight files untouched.
6. **A6 — Qualify the exact compiler/product pair used for that commit.** First use a compiler
   snapshot whose source/product/runtime provenance passes. Record Stage0 and Stage1 identities,
   frontend revision, runtime object, target, optimization and full proof-source digest. Separately
   block release claims on the latest dirty compiler checkout until its source is committed or
   snapshotted and Stage0→Stage1 bootstraps it successfully. Do not relabel the pinned older compiler
   as “latest,” nor silently take a PATH fallback.
7. **A7 — Build both proof and replay products atomically from the frozen source.** Resolve one
   generation once, use the proof/replay binaries from that generation everywhere, and verify the
   manifest and product hashes before and after every test batch. A lone executable, mixed pair,
   changed source digest or runtime mismatch invalidates the entire run.
8. **A8 — Run the narrow regression matrix before broad suites.** Execute call-summary alias,
   named-argument, generic/module identity, disjunction-domain/search-bound, malformed-certificate,
   package-replay and adversarial false-claim tests. Require complete reports, exact expected status,
   no crash, no timeout, no unexplained missing obligation, and zero replay gaps for every admitted
   result. Record expected negative statuses rather than treating every nonzero exit as success.
9. **A9 — Refresh the full admission/replay census on the matched pair.** Include kernel core,
   real proof modules, qualified constants, `Slide.inner`, field equality, unsigned boundaries,
   quantifiers, region lending, `sview`, call composition and selected compiler/Elisa-core sources.
   Save source and executable identities, theorem/obligation inventory, admitted/replayed counts,
   refusal categories, timeout and peak-memory information. Unsupported is a result to report, not
   a pass silently excluded from the denominator.
10. **A10 — Close the qualified-constant crash incident with causality, not a workaround (P-00).**
    Preserve the 51-byte and larger triggers and the passing controls. Recover the exact historical
    product if possible; compare its generated code/runtime and the current strict O0/O2 behavior;
    use a minimized source/compiler differential to identify whether rewrite logic, array bounds,
    region lifetime, lowering or runtime caused the invalid write. Fix the responsible layer and add
    a regression. A blanket refusal or a passing unrelated new binary does not retire this incident.
11. **A11 — Close structural obligation accounting across every entry point (R-004).** Independently
    enumerate declarations and executable verification paths from imported source, then reconcile
    each path to a checked, refused, unsupported or explicitly unreachable result. Cover CLI,
    cache hit, tactic, repair, portable package and replay-only routes. Mutate/dismiss one source
    path, obligation, attempt, certificate and ledger event at a time. Require that omitted work
    cannot improve the whole-file status; document the coordinated-AST/report attack boundary or
    close it with separately authenticated source bytes.
12. **A12 — Publish trust per theorem and per whole-program claim (R-008/R-009).** Enumerate every
    constructor and admission route; for each report expose exact logical rules, source adapter,
    frontend/type-system, compiler/runtime/ABI, solver, assumptions and dependencies. Exercise
    partial files, imported assumptions, cache/package replay, trusted external declarations and
    incomplete reports. A field saying `replay: complete` must be derived from checked roots, not
    copied from producer metadata.
13. **A13 — Complete parser/package boundary stress and real crash recovery (R-006/R-015/R-088).**
    Fuzz generated valid Elisa and proof packages, then mutate one byte/field across tags, integers,
    booleans, lengths, spans, UTF-8, references and checksums. Run under process CPU/RSS caps and
    require structured refusal, no panic, no partial theorem and no partial cache publication.
    Replace mock-only build interruption evidence with real Stage1 failure/kill/restart tests and
    verify readers see a complete old or new pair, never a mixed generation.
14. **A14 — Keep the compiler qualification boundary explicit.** Track the dirty compiler's
    Stage0 parser-machine rejection as an external dependency, not a prover workaround. Once the
    compiler owner has a stable source revision, make minimal stage0/stage1 differential cases,
    rebuild from that revision and rerun importer/source-correspondence tests. Proof results from
    the pinned compiler remain labelled with that exact version until latest-compiler evidence is
    complete.

### Gate B — establish a performance truth set before optimizing

15. **B1 — Turn the sentinels into a representative, immutable workload corpus (R-011).** Add
    interactive tiny proof, large fully replayed proof, hard refusal, timeout, high-fact success,
    high-fact refusal, repeated calls, call-summary composition, deep equality, branch-heavy code,
    package-only replay, malformed package, source import, resource/region, arithmetic width,
    quantifier, loop, cache hit/miss, no-op build and one-file edit cases. Pin file bytes/hash,
    expected status, exact obligation IDs/counts, trusted roots, proof/replay counts and budget class.
    Keep positive and negative variants adjacent so an optimization cannot “improve” speed by
    dropping difficult goals.
16. **B2 — Define phase boundaries and cost units once (R-010/R-012).** Instrument source read,
    include expansion, tokenize/parse, name/type resolution, import/lowering, obligation creation,
    each tactic/decision procedure, certificate construction, independent replay, report building,
    serialization, cache IO and process startup. Define inclusive/exclusive timing, counter owner,
    reset point, unit, integer overflow handling and whether values are per declaration or process.
    Missing timer support is a concrete compiler/runtime interface task; do not infer phase time
    from end-to-end latency or insert wall-clock timing into trusted proof semantics.
17. **B3 — Count algorithmic work, not only seconds.** Add deterministic counters for AST/term nodes
    visited, fact candidates visited, equality comparisons, index probes/collisions, substitution
    steps, rewrites, branch copies/joins, obligations, certificate nodes/edges, replay root/witness
    visits, allocations, retained arena capacity, diagnostic bytes and serialized bytes. Saturating
    counter overflow must be reported and must never change the proof verdict. Validate every counter
    against a small hand-counted fixture and a deliberately overflowing counter test.
18. **B4 — Calibrate the profiler against non-interference and loss.** Compare identical runs with
    instrumentation off, counters only and full event capture. Test nested stores/regions, reset,
    event-buffer overflow, stack loss, truncated files and duplicate events. An incomplete capture
    must be marked incomplete and excluded from hotspot decisions. Publish overhead in wall/CPU/RSS
    and prove instrumentation cannot alter obligations, certificate bytes or replay verdict.
19. **B5 — Profile the entire user operation.** Capture cold and warm successful proof, large replay,
    costly unknown/refusal, malformed package, build/cache hit, and local-edit rebuild. Attribute
    self and inclusive time, allocation/live bytes, retained capacity and RSS. Include frontend,
    solver process, report serialization and harness costs; “kernel replay is fast” is not a useful
    optimization result if import or report construction dominates.
20. **B6 — Produce orthogonal scaling curves.** Vary one factor at a time: source size, declaration
    count, facts, relevant/irrelevant/duplicate facts, branch count/depth, repeated calls, call graph
    fanout, equality width, certificate DAG size, package size and dependency fanout. Measure exact
    cap, one-under, one-over and hostile shapes. Report observed visits/allocations and p50/p95/RSS;
    never claim asymptotic complexity from a small timing sample.
21. **B7 — Establish paired, outcome-identical performance comparisons.** Use at least seven
    alternating baseline/candidate rounds after warmup with identical source, binary pair, frontend,
    runtime, target, optimization, environment and workload. Compare semantic report fields,
    obligation inventory, trust roots, certificate IDs/bytes where stable, refusal reason and
    independent replay before comparing timings. Publish median, p95, spread, all samples and
    censored runs. A material speedup claim requires a repeatable end-to-end gain or a demonstrated
    asymptotic/work-count reduction without unacceptable RSS or regression elsewhere.
22. **B8 — Derive resource budgets from data and make each dimension independent.** Separate import,
    normalization, search, proof construction, replay, decoder, cache, report and total wall/RSS
    limits. Exact/one-over tests must return `unknown`, `timeout` or `unsupported` with stage,
    dimension, observed value and limit—never `false`, a counterexample, or a partial theorem.
    Set p95, memory and refusal-time targets only after the baseline; then ratchet them without
    weakening required proof or adversarial corpus coverage.
23. **B9 — Measure the developer feedback loop.** Record clean build, true no-op build,
    comment-only edit, proof-module edit, test-only edit, unrelated edit, transitive include edit,
    replay-only edit and full suite. Count compiler launches, include hashes, compiles, links,
    runtime-object builds, signatures, manifest writes and tests. Preserve an exact full-suite CI
    path even when a dependency-aware focused suite is added.
24. **B10 — Maintain a scorecard that blocks regressions.** For each corpus class publish proof
    coverage, unsupported/refusal/unknown/timeout, replay gaps, p50/p95, work counters, peak RSS,
    cache behavior and trust dependencies. Compare only matching identities. A performance win
    which reduces coverage or hides a gap fails; a sound coverage gain with a measured cost is
    reported as a tradeoff rather than mislabeled as faster.

### Gate C — remove measured repeated work, cheapest and broadest wins first

25. **C1 — Make no-op and narrow-edit builds truly incremental (R-015/R-018).** Profile include
    discovery, hashing, dependency resolution and hook startup. Reuse a build product only if every
    effective input, compiler/runtime/target option, output digest and manifest verifies. Avoid
    walking unrelated project directories; a comment-only edit may reuse semantic artifacts only
    after source identity and diagnostic remapping are sound. Test symlink retargets, nested include
    edits, missing-then-created includes, corrupt sidecars and concurrent builders.
26. **C2 — Avoid duplicate parsing and resolution inside a single request.** Map which CLI/report
    paths parse or resolve the same source more than once. Share immutable frontend output for the
    duration of one request, with exact source-store generation and compiler identity; do not retain
    AST pointers past their owner. Prove byte-identical obligations and diagnostics across the
    shared and unshared paths, then measure import time and peak memory.
27. **C3 — Build a source-call/declaration index once per immutable module.** Replace repeated
    whole-AST scans for a call span, qualified declaration, owner function or local initializer
    only where B3/B5 show the scan is material. Key candidates by stable module/declaration/span
    identity; verify selected rows against a simple linear scan oracle. Test same-name overloads,
    identical same-line calls, nested modules and changed source generations. This directly reduces
    replay latency while strengthening source correspondence.
28. **C4 — Add fact and scalar-witness indexes behind a reference scan (R-019).** Pilot exact
    proposition, complement, sort/width and normalized scalar keys. Preserve candidate order where
    search is order-sensitive; force hash collisions, duplicate/empty names, shadowing, malformed
    facts and type mismatch. The index may find candidates, but only structural equality and kernel
    rules prove them. Require lower candidate visits and total cost on real high-fact cases.
29. **C5 — Keep disjunction search relevant and sharply bounded (R-024).** Retain late-relevant
    premise, disjunctive-syllogism and refuted-alternative positives. Count candidates examined,
    not merely eligible facts; define cap behavior consistently between producer and replay. At
    every exact/one-over edge require deterministic `unknown`/`budget` with no partial certificate.
    Benchmark irrelevant-fact-heavy and relevant-fact-heavy inputs to ensure the filter itself pays
    for its build/scan cost.
30. **C6 — Avoid repeated source and state substitutions.** Profile call-summary instantiation,
    WP generation and replay. Intern only immutable, fully typed substitutions within a single
    validated context; keys include binder, declaration, type width, state version, effect/region,
    and source identity as appropriate. Compare to uncached output under forced key collisions,
    shadowing, generic instantiation, reassignment and context mutation; keep cross-request caching
    off until dependency identities are complete.
31. **C7 — Collapse redundant certificate traversals.** Count root, witness and DAG visits in
    admission, replay and package checking. First fuse passes only when they consume the same
    immutable validated evidence; otherwise memoize by certificate node plus exact context/version
    and arena generation. Detect cycles, omitted edges, stale handles and mutated backing storage.
    Require identical checked roots and fewer total visits, not merely faster wall time from noise.
32. **C8 — Fix the field-equality workload before generalizing equality (R-023).** Minimize the
    timed example; split parse, candidate generation, normalization, structural equality, proof
    construction and replay. Implement the smallest proof-producing congruence/index slice that
    changes the real bottleneck. Wrong field, alias, state change, overload, effect, width and binder
    controls must remain rejected. Record success/unknown/timeout and cost for the exact same goal.
33. **C9 — Use sparse arithmetic evidence if dense closure is proven dominant (R-025).** For one
    measured linear/difference fragment, store only coefficients or predecessor edges required by
    the derivation. Replay integer arithmetic exactly and keep machine-width/range/wrap side
    conditions explicit. Compare search CPU, peak live memory, certificate size and replay visits;
    retain signed/unsigned min/max, division and overflow negatives.
34. **C10 — Reduce branch-context copying only when allocation counters justify it (R-021).** Prototype
    immutable parent contexts plus per-branch deltas for facts and invalidated places. Keep a simple
    copied-context oracle for differential tests. Exercise nested branches, early returns, loops,
    sibling failure, cancellation, resource writes and post-check mutation. Require lower allocations
    and peak RSS at realistic branch depth with byte-identical proof outcomes.
35. **C11 — Bound report memory and defer optional presentation work (R-016).** Separate the
    minimum trusted verdict/obligation/trust ledger from explanations, suggestions, AST excerpts and
    verbose measurements. Add summary/full modes or lazy detail retrieval only if both are tied to
    the same immutable report generation. Compare retained heap/RSS and latency; never drop data
    used by completeness, cache keys, replay, or audit.
36. **C12 — Reclaim scratch at obligation and request boundaries (R-014/R-026).** Inventory temporary
    search arrays, proof candidates, branch snapshots and diagnostics by region/lifetime. Repeatedly
    check a large file, return/reset views, cancel and restart, and force allocation failure. Live
    bytes should return to a stable envelope; retained capacity and RSS are reported separately.
    No `sview` may outlive its backing storage, and cleanup cannot publish partial proof state.
37. **C13 — Add typed-term sharing only after identity and allocation profiles (R-020/R-022).** Start
    with immutable leaves/operators and one checking session. Include semantic sort, machine width,
    qualified declaration, binder/context, effect/region, floating mode and rule version in keys as
    applicable. Differentially replay cached/uncached proofs and force collision, mutation, eviction,
    cancellation and source replacement. Do not intern mutable AST or arena-owned references.
38. **C14 — Make repeated CLI requests cheap without weakening revalidation.** After declaration
    identities and complete dependency edges exist, cache parsed/typed artifacts and replayable
    certificates across requests. Validate all keys on every load, replay certificates in a fresh
    process, invalidate reverse dependents after signature/body/contract/effect changes and recover
    safely after interrupted publication. Measure cold, warm, no-op, one-local-edit, one-transitive-
    edit and restart against uncached full checking.
39. **C15 — Parallelize only independent declarations and cap aggregate resources (R-036).** Use the
    verified dependency DAG, per-worker deterministic budgets and one total memory ceiling. Compare
    jobs=1 and jobs=N for exact reports, root order, diagnostics and certificate IDs. Inject worker
    failure/cancel during publication; no stale task may commit artifacts. Keep serial execution as
    the reference implementation and default until parity and speedup are demonstrated.
40. **C16 — Make test selection dependency-aware, never test coverage optional.** Build a checked
    map from source modules, compiler/runtime identity and behavior to tests. Run focused impacted
    tests on edits, while preserving required full-suite and adversarial release runs. Mutation-test
    the selector by changing each semantic dependency and confirming the right tests are scheduled.
    Report skipped tests and reason in CI; unknown dependency means run the full suite.

### Gate D — expand the useful verified subset by common-case return

41. **D1 — Finish exact pure modular call composition before adding solver breadth (R-039).** Prove
    a helper with a conditional postcondition and its caller using exact named/positional actuals,
    generic identity, state snapshots and result binding. Keep swapped actuals, false contracts,
    changed body dependencies, aliasing, hidden effects and wrong call-site witnesses as negative
    controls. Publish one reusable summary package and prove a downstream caller without rerunning
    search.
42. **D2 — Consolidate weakest-precondition generation for the common sequential core (R-038).**
    Give assignments, sequencing, conditionals, returns and local initialization one typed
    substitution/state-update model. Separate partial correctness from termination. Cross-check
    bounded small programs with an independent interpreter, including shadowing, early return,
    dead code, mutation and error branches; replay each generated VC.
43. **D3 — Complete machine arithmetic semantics by width families (R-042).** Specify add/sub/mul,
    div/rem, casts, comparisons, shifts and bitwise operations for each admitted signed/unsigned
    width, including division by zero and overflow/trap/wrap behavior. Exhaustively test small widths,
    then test 8/16/32/64-bit boundaries across source checking, tactics, certificate replay and
    package import. Never infer unbounded-integer identities for bit-vectors without checked range
    evidence.
44. **D4 — Turn common loop reasoning into explicit invariant obligations (R-040/R-041).** Select
    one real bounded collection traversal. Generate initiation, preservation, exit, frame and
    variant obligations; support one explicit invariant and one structural/well-founded termination
    measure. Mutate the invariant, bound, update and variant; ensure the unrolled bounded result is
    never reported as an unbounded proof.
45. **D5 — Prove collection update and frame laws from source-linked epochs (R-044/R-049).** Model
    length, read-over-write, push/pop/swap and disjoint-field preservation with canonical places and
    mutation epochs. Prove a prefix/update property on a real sequence example. Reject out-of-bounds
    indices, unknown aliasing, stale epochs, forged footprints, reallocation-invalidated references
    and mismatched frame arguments.
46. **D6 — Close region/view/ownership guarantees as one end-to-end slice (R-046–R-050).** Preserve
    `new[r]` region identity, value-vs-reference representation, forwarding through calls, capability
    counts and `sview` backing lifetime. Prove a view remains backed while present; reject region
    escape, use after reset, aliased writes without permission, lost/duplicated linear resources and
    a view whose source argument differs from the actual place. Do not count source syntax support as
    proof until replay validates the ownership transition.
47. **D7 — Verify effect and error propagation over a wrapper chain (R-051/R-052).** Derive effect
    rows and handled/unhandled transitions from imported source; compose normal and exceptional
    postconditions through one wrapper and cleanup block. Test omitted effects, false handler
    declarations, exceptional resource leaks and skipped cleanup. Keep unmodelled FFI/unsafe effects
    explicit assumptions or unsupported.
48. **D8 — Add ADT cases, induction and symbolic quantifiers in one replayable family (R-055–R-057).**
    Start with option/list-like data, exhaustive cases, explicit induction motive and scoped
    hypothesis. Add symbolic-range quantification only with checked domain, binder hygiene and
    proof terms for every instantiation/induction step. Reject omitted constructors, escaped
    eigenvariables, malformed motive and trigger-free unbounded search. Track proof size and replay
    cost as well as coverage.
49. **D9 — Build reusable checked libraries around proven common facts (R-058/R-061).** Provide
    arithmetic, list/sequence and resource/frame lemmas with qualified identities, dependency
    closure and terminating rewrite measures. Every simplification emits replayable steps; cyclic
    rules, missing conditional premises, overflow-sensitive identities and import-name collisions
    refuse. Measure whether libraries reduce proof script length and search work on real clients.
50. **D10 — Introduce refinements, ghost state and abstract interfaces after invalidation is sound
    (R-053/R-062/R-063).** Prove one range/nonzero refinement and one representation-hiding module
    contract. Mutations invalidate dependent facts; implementation-only edits preserve clients only
    when the exported verified interface and semantic dependencies remain identical.

### Gate E — raise automation and self-assurance after the kernel boundary is dependable

51. **E1 — Stabilize the versioned structured goal API (R-064/R-065).** Return proposition, typed
    hypotheses, binders, resources/effects, dependencies, trust assumptions, attempt history, budget
    use and replay state. Add stable IDs, generation tokens, pagination and compact deltas with a
    full-snapshot fallback. Reject stale IDs and cross-request handle reuse. Keep JSON schema
    versioned and test round-trip clients.
52. **E2 — Make failure explanations evidence-derived.** Report `proved`, validated
    `counterexample`, `unknown`, `timeout`, `unsupported`, `incomplete` and trusted assumption
    distinctly. Tie each suggested missing premise to actual attempted engines/failed rules and
    identify the exhausted resource dimension. Mutation-test explanation payloads against actual
    search traces; natural-language confidence alone never upgrades status.
53. **E3 — Add bounded counterexamples before broad bounded proving (R-072/R-073).** Validate a
    candidate model against source-level widths, branches, calls, permissions and effects using an
    independent evaluator. Report the bound and uncovered behaviors; bounded success remains a
    bounded result. Invalid/partial models must not be called counterexamples.
54. **E4 — Round-trip a minimal readable proof language (R-066).** Parse/elaborate `have`, `apply`,
    `cases`, `rewrite` and `calc` outside the kernel, print focused goals, serialize proof terms and
    replay them from a fresh process without AI or search. Require deterministic output, source
    spans, useful error messages and stable proof-term format before adding tactic syntax.
55. **E5 — Add solver/ATP or AI search only through reconstruction (R-067/R-069–R-071).** Schedule
    normalization, congruence, arithmetic and existing deterministic tactics before optional
    external engines. Record solver binary/version/options/query and shared CPU/RSS budget; reconstruct
    a certificate checked by the kernel. Test malicious solver answers, timeout, crash, malformed
    model and unavailable process. AI edits run in immutable child snapshots and expose all
    contract/assumption/dependency changes.
56. **E6 — Specify and independently check a complete small trusted subset (R-082–R-088).** Publish
    exact modules/rules/types admitted and transitive compiler/runtime assumptions. Implement a
    representation-independent checker for one complete certificate family; mutation/generation
    campaigns compare it with production replay. Prove arena bounds, binder scope, context identity,
    DAG acyclicity and checked integer arithmetic; do not claim self-verification from helper
    examples alone.
57. **E7 — Dogfood the assistant only after avoiding circular trust (R-084–R-086).** State the
    formal calculus and rule soundness separately from proofs that Elisa code implements those
    rules. Select a small compiler pass with independent semantics, generate stage0/stage1
    differential regressions, and let Elisa-Proof discover candidate bugs; a compiler fix still
    requires an independent compiler test and fresh bootstrap/product provenance.
58. **E8 — Defer concurrency, liveness and temporal logic to a sound execution model (R-075–R-080).**
    First define happens-before, atomicity, ownership transfer, fairness and scheduler assumptions.
    Then prove one race-safety protocol slice and one progress/deadlock property with separate safety
    and liveness evidence. Never infer liveness from safety or fairness from observed executions.
59. **E9 — Qualify and release against exact snapshots (R-089/R-090).** Run macOS/Linux builds,
    full tests, no-AI/no-solver fresh-process replay, hostile inputs, compiler freshness, trust-ledger
    review and performance scorecard. Preserve all failing/timeout cases and unsupported semantics.
    Re-rank after each 5–10 small commits using new coverage, root-cause, latency, memory and
    assurance evidence; keep old incidents in the ledger.

### Performance stop rules and expected return

- Do not optimize by raising budgets, dropping facts/branches, shrinking imported source, suppressing
  replay gaps, reducing report detail needed for admission, or changing a hard case into an
  unreported skip. Those are semantic changes, not performance wins.
- No index, memo table, interning, incremental cache or parallel mode is presumed faster. First
  show its target cost is material in a complete representative profile; then retain an independent
  scan/uncached/serial oracle and compare exact proof outcomes.
- Prefer broad wins with a small trust footprint: eliminate duplicate parse/resolution, avoid
  repeated source-tree work, index repeated lookups, bound pathological scans, share immutable
  validated artifacts, and reduce avoidable allocations before adding complex global caches.
- Treat CPU, wall time, peak RSS, logical-live bytes, retained capacity, allocations, certificate
  size and developer iteration time as separate metrics. An improvement in one cannot conceal a
  regression in another. Include success and refusal workloads; refusal latency is part of the
  user-facing contract.
- Once B1–B10 establish stable data, set class-specific ratchets. As an initial review rule, a
  claimed local speedup should be repeatable across paired runs and large enough to exceed measured
  noise; a claim that materially increases code/trust complexity should normally demonstrate at
  least a 10% end-to-end gain on its intended workload or a clear asymptotic/work-count improvement
  plus a justified memory/latency benefit. This is a review threshold, not permission to reject
  smaller security or correctness improvements.
- The near-term performance objective is not one arbitrary “5k lines per minute” promise. It is a
  verified cost model: predictable interactive p95, bounded hostile-input refusal, scalable fact,
  branch and replay work, low-memory fresh-process replay, and incremental edits proportional to
  the affected dependency closure. Set numerical service targets from the pinned corpus and ratchet
  them only after they are reproducible.

**Next concrete batch:** A1, A2 and A3 first (the current call-summary replay gap); A4 and A5 then
commit that narrow repair. A6–A9 establish exact-current behavior before broader changes; A10–A14
remain explicit correctness/compiler blockers. In parallel, start B1–B4 with a small immutable corpus
and trustworthy counters, then finish B5–B10 before selecting C1–C16. Do not begin C optimizations
from profiler anecdotes or begin D/E feature work while a source/replay mismatch remains.
