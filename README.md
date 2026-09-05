# Elisa Proof

This is the first self-hosted proof-assistant slice for Elisa. The executable is written in
Elisa and imports the compiler's own parser, lexer, AST, and semantic checker from the adjacent
`Elisa-compiler` checkout. The proof kernel therefore checks the same syntax and declarations
that Elisa compilation checks; it does not translate Elisa into a second host-language model.

## Build and run

The compiler source include is relative to the sibling checkout used by this workspace. Put the
stage wrappers on `PATH`; `build.sh` tries the self-hosted `elisac-stage1` first and falls back to
`elisac-stage0`:

```sh
PATH=/path/to/elisac-bin:$PATH scripts/build.sh
build/elisa-proof examples/verified.elisa
```

For AI tooling, `build/elisa-proof --json examples/verified.elisa` emits a deterministic machine
report with the compatibility verdict, an explicit `verification_state` (`proved`, `disproved`,
`unsupported`, or `unknown`), the expanded-source byte count and observational FNV-1a fingerprint,
trust-boundary counters, structured findings, replay coverage, compiler semantic diagnostics, and
every goal attempt (including failed goals) with its hypotheses and structured expression tree.
The `trust` object contains an itemized `boundary_facts` ledger (kind, source owner/line, and
source-neutral kernel root) whose length must equal `trusted_boundary_facts`, plus an explicit
`trusted_assumptions` ledger. The latter is empty in the current system, and future foreign axioms
or unchecked escape hatches must appear there explicitly.
`declaration_details` provides deterministic source-level
function/module metadata, parameter names, contract counts, recursion/purity/structural flags,
and executable-summary status. For executable functions, `verified` is true only after the body
has been checked in dependency order; `verification_reason` explains pending, verified, or
rejected summary status. This lets proof agents enumerate definitions and invalidate dependent
summaries without scraping source text. Lemmas use the same field to report whether their
proof-only summary was checked before a caller can consume it.
`repair_queue` is a deterministic projection of unresolved goals, carrying each goal's stable ID,
location, rule, replay status, structured failure classification/message, optional counterexample,
and theorem dependencies so an agent can request focused repair without scanning the complete goal
stream.
Use `build/elisa-proof --goal N file.elisa` to retrieve only one of those goals without loading the
full report or kernel arena. The deterministic `elisa-proof-goal-v1` response includes the source
fingerprint and completeness gate, proposition, exact hypotheses and origins, dependencies,
certificate/replay state, and the goal-bound failure classification. Retrieval exits `0` when the
goal exists—including an unresolved goal—and `2` for an invalid or missing ID; proof status is
carried explicitly as `proved`, `disproved`, `unsupported`, or `unknown` in the response.
`dependency_index` provides the reverse mapping from theorem/function-summary dependency names to
the stable goal IDs that consume them, making downstream invalidation direct and deterministic.
`build/elisa-proof --theorems file.elisa` emits a compact `elisa-proof-theorems-v1` catalog for
proof search. Each Elisa lemma includes its structured parameter names and Elisa type expressions,
preconditions, postconditions,
termination measure, recursion flag, verification state, and rejection reason. Unverified lemmas
remain discoverable for repair but are never presented as usable theorems; the catalog also carries
the source completeness and semantic-admissibility gates.
Every theorem also identifies its owned proof goals and their certificate/replay status.
`proof_replay_complete` is true only for a verified theorem with at least one owned obligation and
a replayed certificate for every one, making the evidence behind theorem search directly auditable.
Every consumed lemma or executable-function summary fact is additionally bound to its normalized
formal-argument mapping, selected postcondition index, and exact caller certificates for all
instantiated preconditions. Function summaries also bind the concrete `result` term. Independent
replay reconstructs each postcondition and rejects a mismatched fact; summaries therefore no
longer count as trusted-boundary facts.
The replay-side substitution is separately implemented across the kernel term language—including
calls, fields, indexing, aggregates, constructors, conditionals, comprehensions, and scoped
quantifier blocks—and preserves binder shadowing instead of reusing the elaborator's substitution.
`theorem_fingerprint` canonically hashes the theorem name, typed parameters, defaults, ordered
preconditions, postconditions, termination measures, and recursion mode using source-neutral kernel
terms. It survives unrelated declarations and line shifts but changes with the theorem statement.
Like the source and goal FNV identifiers, it is a cache/binding guard rather than proof evidence;
verification and independent replay remain mandatory admission gates.
Use `build/elisa-proof --suggest N file.elisa` to narrow that catalog to verified lemmas whose
conclusions first-order match goal `N`. The deterministic response includes inferred parameter
bindings, instantiated premises, and whether the current goal facts discharge every premise.
`premises_satisfied` reports local proof search independently, while `applicable` additionally
requires the imported source to pass its semantic/replay admissibility gates.
Suggestions are navigation hints only: they do not admit a goal or bypass tactic and kernel replay.
Goal-generated entries in `findings` also expose their exact `goal_id`; non-goal diagnostics use
`null`.
The `action_protocol` capability declaration identifies the Elisa-native `elisa-proof-tactics-v1`
state API. It exposes kernel-backed `assumption`, `exact`, `decide`, `intro`, `apply`, `simp`,
`have`, `instantiate`, `rewrite`, `split`, `left`, `right`, and `cases` operations; `simp` only
folds checked closed constants, `instantiate` only admits a checked member of a finite integer
range or literal collection, branch operations return independent child states, and a failed
operation cannot mark a goal solved. The implementation is in
`src/proof/tactics.elisa`, so AI or editor integrations can reuse the same state transitions
instead of inventing proof facts from the JSON report. Each tactic state also retains its
initial facts/goal and a deterministic post-state trace with complete flat fact snapshots;
`proof_tactic_replay` reconstructs that trace with the same kernel-backed operations and rejects
any transition or final-state mismatch. `proof_tactic_kernel_trace_replay` independently lowers
every snapshot and explicit argument into the source-neutral arena and checks each transition
with `proof_kernel_replay_tactic_step`, including rejected actions and solved-state provenance.
Solved states can additionally be checked with `proof_tactic_kernel_replay`, which lowers the
final facts and goal into the same arena and invokes the independent replay kernel; an unsupported
term or a forged `solved` bit is rejected.
Clients that need one final admission call can use `proof_tactic_kernel_certificate_replay`,
which requires both the complete transition trace and the independently replayed solved goal.
For `split` and `cases`, `proof_tactic_kernel_branch_certificate_replay` additionally binds the
parent proposition to both child contexts and requires both child certificates to close.
Portable proof scripts can be checked directly by the Elisa executable:

```sh
build/elisa-proof --tactics examples/tactic_script.json examples/verified.elisa
```

The script uses the same `elisa-proof-tactics-v1` format with an ordered `actions` array. For a
reusable theorem-state check it may provide an `initial` facts/goal state; expressions use the
report's JSON AST shape, so an AI/editor can emit a script without constructing in-process Elisa
values. For declaration-level verification, it can instead provide `target: {"goal_id": N}`.

JSON tactic importer accepts integer numbers only from -9007199254740991 through
9007199254740991, because its JSON library stores numbers as `f64`. Larger source integers remain
supported by the source checker, but their JSON tactic states are rejected to prevent rounding
from changing the proposition. Source-bound quantifier kinds come from compiler annotations;
script annotations cannot override them.

The runner takes the exact goal and traced facts captured for imported source goal attempt `N`;
`initial` is rejected in this mode, so a proof of a different proposition cannot be relabeled as a
source proof. The command imports and checks the Elisa source, then requires the script's
transition trace and final certificate to replay independently; an optional unsigned
`source_fingerprint` makes any source edit invalidate the script. A source-bound script may
instead put the focused view's canonical value in `target.goal_fingerprint`; this binds the script
to the exact source-neutral proposition and ordered hypotheses while allowing unrelated
declarations or source-line shifts. The FNV value is an incremental identity guard rather than
cryptographic proof; the matching term and complete tactic certificate are still independently
replayed. The result is a compact
`elisa-proof-tactic-result-v1` document containing the source-goal binding, final state, and trace.
For a source-bound script, top-level `status: "proved"` means the selected target was admitted; it
does not claim that every source obligation is closed. The nested `source.complete` field retains
that whole-program verdict, `admission_scope` is `target`, and `source_goal_binding.previously_proven`
distinguishes replay of an existing certificate from repair of an open goal. Target repair remains
blocked by import failures, compiler semantic errors, or any certificate replay gap. Portable
scripts with an explicit `initial` state still require the complete imported source to pass.
A branch action is the final parent action and carries exactly two child action scripts under
`branches`; each child starts from the state produced by `split`/`cases`, and the independent
`proof_tactic_json_tree_certificate_replay` checks every nested child certificate and parent-to-
child transition. The runner uses a bounded depth-32 scratch pool and a flat postorder tree, so
child state injection, malformed edges, and excessive nesting fail closed.
Failed arithmetic/proposition goals may additionally carry `counterexample_found: true` and a
deterministic assignment whose facts evaluate true and goal evaluates false; absent witnesses mean
the bounded diagnostic search could not establish a concrete failure. Successful attempts additionally appear as certificates. The report's `kernel` object identifies
the source-neutral arena format and its node/child counts; `semantic_diagnostics` preserves the
compiler's structured location, severity, kind ordinal, typed context, effect references, and
canonical message; a zero replay-gap result means the certificates passed that independent kernel
path.

The current local compiler wrappers can be used as:

```sh
PATH=/Users/torarinvikbjarko/.elisac:$PATH scripts/test.sh
```

Run the source-neutral dogfood gate with `scripts/dogfood.sh`. It requires the formalized kernel
layers and standalone replay boundary to be fully independently replayable. Set
`ELISA_DOGFOOD_FULL=1` to additionally audit the complete imported implementation source; that
report is expected to remain `failed` until the checker covers the compiler and proof-language
surface, but it must still finish with zero certificate replay gaps.
Each dogfood probe is executed twice and must produce byte-identical JSON, making nondeterministic
proof IDs, certificate ordering, or report serialization a gate failure.

`scripts/test.sh` checks accepted proofs, textual imports, lemma application, structured results,
frames, defaults, direct and mutual recursive termination, lexicographic and structural recursion,
finite collection quantifiers, pure-call defaults, transitive and mutually recursive pure contract calls, assignment/declaration evaluation order, and rejected proof, lemma,
self-assertion, circular-summary, recursive-lemma, nested-call-state, shadowing, contract-call,
assert-nested-call, and overflow obligations. A
successful proof command exits `0` only when every obligation, compiler semantic check, and
certificate replay succeeds; failed obligations, semantic errors, or replay gaps exit `1`. The
matrix also runs `examples/dogfood_kernel_core.elisa`, which imports the actual AST-free replay
core and checks its foundational root, range, and depth contracts through the same proof/replay path.

The checker is designed to be dogfooded: the kernel boundary is analyzed through this same
import/check/replay path, with `src/proof/kernel_core.elisa` directly verifying its own
`root_valid`, `range_valid`, and replay-depth contracts. Arena admission, certificate provenance,
replay determinism, and the source-neutral replay module are exercised by the dogfood gate, with
no circular self-trust exemption. The replay module is also compiled independently from a fixture
that imports only `kernel_core.elisa` and `kernel_replay.elisa`; this dependency-isolation gate is
separate from proof acceptance and does not pretend that the complete AST-backed checker has
verified itself yet.
The full-source audit now reaches the complete imported implementation and has zero replay gaps;
its remaining failures are explicit semantic/unsupported obligations rather than unverified
certificates.

## Current proof surface

The native checker currently supports:

- `proof GOAL:` and `assert GOAL by:` blocks;
- proof-block purity, with checked `assert` steps and checked `lemma` calls allowed;
- program-point `assert ... by:` checking, including branch facts and publication of the proven
  runtime guard to subsequent statements; call-containing guards are published only when their
  substituted value is certified pure;
- structural equality and Boolean goals;
- conservative integer comparisons, explicit bounds, conjunctions, and overflow-safe constant
  arithmetic, plus bounded affine differences such as `x + 1 > x` when no-overflow bounds are
  available. Upper overflow and MIN_I64 subtraction/negation claims are adversarially rejected
  without compiler or replay traps. This tier also supports exact closed bitwise/shift evaluation
  and total fixed-width identities such as
  `x * 0`, `x * 1`, `x + 0`, `x / 1`, `x & x`, `x | 0`, and `x ^ x`;
- bounded model checking over explicit finite integer intervals, with exact enumeration of the
  product domain for small pure Boolean/integer goals (including nonlinear arithmetic);
- interval bounds for division by a proven constant and remainder by a nonzero constant, with
  the `i64` division edge case and divisor overflow boundaries rejected conservatively;
- bounded difference-constraint closure for transitive signed comparisons and safe affine
  relations between distinct identifiers;
- explicit identifier equality closure (`x == y`, including short chains) with safe bound
  propagation;
- bounded one-binder `forall`/`exists` contracts over finite integer ranges (`..<` and `..=`),
  checked by explicit kernel instantiation with a fixed work budget;
- bounded `forall`/`exists` contracts over finite literal arrays, tuples, sets, and dictionaries
  (one binder for ordinary collections, two for dictionary key/value pairs), also checked by
  explicit instantiation;
- symbolic substitution through local declarations and assignments, including constructor and
  record-update field projection;
- compiler-checked `get collection[index] else fallback` accesses, where the runtime fallback
  discharges the outer bounds obligation while nested accesses and fallback expressions remain
  visible to the checker; the selected element is intentionally opaque to the arithmetic kernel;
- statement-level `get … else` control recovery, where the guarded value and the terminating
  `return`/`raise`/loop-transfer path are checked independently against cloned proof states;
  direct guarded indexes also emit a replayed `checked-get` safety certificate, while
  falling-through recovery blocks, nested recovery expressions, and labeled transfers remain
  rejected;
- restricted expression-position `catch` over a direct fallible call, with a verified call
  summary available only to the success arm and an independently checked error-arm result;
  verified total-pure calls may also produce arm values, while non-exhaustive, guarded, effectful,
  payload-binding, and multi-statement catch arms remain rejected;
- branch-sensitive return `ensure` checking and comparison complements;
- sound bounded case elimination for pure conditional expressions in comparison goals, checking
  both branches under the condition and its structural negation;
- loop invariant establishment and one-step preservation checks, with invariant plus negated
  condition facts available after a normally completing loop;
- fail-closed traversal of loop bodies even when an invariant is missing, so nested obligations
  remain visible instead of being hidden by the missing-invariant diagnostic; and
- checked loop lexicographic `decreases` measures (tuple or repeated clauses) for component
  nonnegativity at loop entry and after each fall-through step, plus strict progress; a
  straight-line update followed by an unlabeled `continue` is also checked at its exact back edge,
  and branch-local continuation edges are checked from their own captured states. Established
  while/for invariant entry facts replay as derived logical steps rather than trusted transitions;
- entry-state `old(...)` substitution for local postconditions;
- compiler-marked `lemma` summaries, including dependency-ordered proof checking, call-site
  precondition checking, and postcondition propagation; lemmas are proof-only, cannot enter
  executable summaries, and an unverified lemma emits `lemma-summary-unverified` instead of
  contributing facts; recursive lemma
  summaries require matching checked lexicographic `decreases` measures across the recursive SCC;
- recursive lemma bodies may branch over pure conditions; each recursive call is admitted only
  after its mapped measure tuple is proven nonnegative and strictly smaller, while external
  callers consume the verified summary without re-proving induction;
- executable function summaries, with dependency-ordered callee verification, fail-closed
  `function-summary-unverified` boundaries, callee `requires` checking, named-argument mapping,
  `ensure` propagation, and independent replay that reconstructs the exact selected contract from
  report-owned executable signatures, normalized arguments, concrete result binding, and replayed
  precondition certificates; plus
  conservative bounded nested-path `changes`/`preserves` frames with subtree permissions,
  overlap-aware alias mapping, and direct-write checking,
  interprocedural frame conformance, nested-call checking, and disjoint fact preservation;
- compositional resource summaries for exact borrow-carrying calls: a callee's independently
  replayed lexical resource trace is instantiated at the caller with formal/actual permission
  checks and bounded external-write propagation; named fields, closed literal indexes, and
  closed literal multi-index paths are preserved as exact path components; small symbolic index
  paths may be separated only by explicit replayed inequality facts, while recursive-SCC, defaulted,
  dynamic, and opaque
  resource calls remain explicitly unsupported;
- pure parameter-default materialization, including defaults that call verified total-pure
  functions; unresolved, effectful, later-formal, or `old(...)` defaults fail closed, and pure
  summaries apply the same rule to omitted defaults; and
- recursive calls inside a strongly connected component when both caller and callee provide
  matching explicit lexicographic `decreases` measures, checked for component nonnegativity and
  first-different-component strict descent before the recursive postcondition summary is applied;
  and
- direct and mutually recursive structural calls over one enum type when each recursive argument
  is a binder from a matched strict subterm; whole-value bindings, opaque forms, and mixed-type
  structural SCCs are rejected conservatively; and
- implicit structural termination for recursive functions with one or more enum-typed parameters
  when no `decreases` clause is written; the same matched-strict-subterm checker remains mandatory,
  every inferred subject must be unchanged or strictly descended on each edge, and ambiguous or
  nondecreasing recursion is rejected. Captured value blocks are accepted for this termination
  check only when their captures do not overlap the active strict-subterm binders; and
- lexical binding safety at proof-state boundaries: initializer/RHS expressions are evaluated
  before a new binding or assignment target is committed, shadowed bindings do not inherit the
  outer symbolic value, and branch joins retain only names soundly available on every path; and
- executable-call and unsupported-expression rejection in logical `requires`, `ensure`, `invariant`,
  and `decreases` contracts. `old(...)` and calls to verified total pure functions are the only
  call-shaped logical operators currently modeled; pure summaries are checked for immutable
  parameters, no declared effects/frames, no writes, no mutable-global reads, and a transitive pure call graph; recursive
  pure functions may additionally qualify when every member of their SCC has an explicit bounded
  decreases tuple and every recursive edge is checked for nonnegative, strictly descending measures;
  runtime call-containing statements must be call-rooted unless every nested call is certified
  total-pure; effectful nested calls remain rejected until a general expression evaluator exists;
  and
- a flat certificate trace for every successful logical goal, including recursively replayable
  premises for derived proof steps and recursively replayed non-cyclic callee certificates for
  modular summaries, plus an independent replay pass for
  structural facts, bounded integer intervals, affine fixed-width identities, and bounded
  difference constraints, and bounded disjunctive/conditional case splitting. Replay rejects facts that have
  no source trace, and the report exposes replayed certificates and replay gaps so the remaining
  arithmetic, quantifier, and recursion surface can be reduced rule by rule; and
- deterministic report-local `goal_id`, `certificate_id`, goal-to-certificate links, and explicit
  theorem dependencies in JSON, so an editor or proof agent can target one obligation, invalidate
  affected summaries, and request a focused repair/replay; and
- a source-neutral `elisa-proof-kernel-v1` term arena for certificate goals, facts, and derived
  premises. Its independent replay path consumes canonical node/index data rather than compiler
  AST nodes; malformed or unsupported lowered terms remain replay gaps; and
- exact scalar literal terms (`int`, `bool`, `float`, `string`, and `char`) are represented in
  that arena so source-backed literal facts remain provenance-checkable; guarded Boolean calls may
  use an exact verified `result == postcondition` equality, but only when the same call or its
  negation is present in the branch context; and
- one-segment leading-dot const-enum values (`.Variant`) are represented as distinct `shorthand`
  leaf terms rather than identifiers. Qualified shorthand remains unsupported until the
  source-neutral term carries its enclosing enum/type identity; shorthand arena leaves are
  independently shape-validated as edge-free nodes; and
- slice expressions are represented as `slice(object, low, high)` terms, with omitted endpoints
  encoded by a distinct `absent` leaf. The validator recursively checks all three edges and
  rejects hidden metadata or child slices; and
- multi-argument index/application terms are represented as `index-n` nodes with an explicit
  receiver and bounded child slice. This preserves logical term identity; nested fixed-array
  parameters with literal dimensions additionally receive independent per-dimension lower and
  upper obligations, while dynamic or aliased shapes remain opaque; and
- kernel quantifier instantiation substitutes through conditionals, collections, calls, checked
  accesses, slices, and record construction/update terms while preserving their exact structure;
  malformed substitution paths become unsupported rather than assumptions; and
- successful certificates are provenance-bound to the exact successful goal attempt that emitted
  them, including owner, rule, source fact range, and source-neutral arena roots; orphan or
  fabricated roots become replay gaps, while the source-level goal remains a report mirror; and
- a fail-closed arena admission check before logical replay: every reachable node edge, child
  slice, and collection element is range-checked through the standalone Elisa kernel core, while
  cycles are rejected and valid DAG sharing is retained. This is the first concrete defense for
  future serialized or cross-process certificates; and
- a narrow public source-neutral arena-admission entry point, exercised by an adversarial
  cyclic-arena fixture. The malformed graph is rejected while an unrelated `true` certificate
  still replays, so malformed arena input cannot be hidden by certificate mixing; and
- an executable arena-admission harness compiled from the same Elisa module and linked against
  the Elisa runtime. It rejects cyclic, out-of-range, malformed call-child, and hidden-metadata
  graphs while accepting valid DAG sharing, covering behavior beyond the AST-level report mirror;
  admission uses an explicit DFS work stack with the same 127-level certificate bound; and
- compiler-compatible match arms add replayable variant-tag facts and exact boolean/integer
  equality or range facts, character patterns add replayable exact equality facts, pinned patterns
  add replayable equality facts, and named struct/variant payload binders are
  substituted as symbolic field projections; closed OR-patterns add one replayable disjunctive
  fact, while string, positional, null, opaque payload, or richer nested pattern shapes fail
  closed; and
- pure value-match expressions with closed literal, range, tag, or-pattern, and wildcard arms are
  lowered into the same replayable conditional kernel path. They require single-expression arms,
  reject positional/opaque payload binders and effectful calls/moves, admit named variant-field
  projections plus verified total-pure calls, and
  require an explicit unguarded wildcard fallback; each arm is checked in an isolated proof state
  so a callee postcondition cannot cross a branch join. Partial or richer value matches remain
  unsupported; and
- counting-range loops add traced lower/upper bounds for their binders, allowing later indexed
  collection obligations to consume the same semantic facts without treating loop syntax as an
  unchecked axiom; and
- ordinary `for` loops may carry replayable `invariant` contracts. Each invariant is checked at
  entry and after one arbitrary body iteration, including unlabeled `break`/`continue` paths;
  only invariants over bindings that remain in scope after the loop are exported at the join.
  A missing invariant keeps the existing conservative body-only behavior, while a binder-scoped
  invariant is rejected explicitly rather than emitting a certificate with a free variable; and
- direct single-index reads and writes over tracked collection-like places emit explicit lower and
  strict-upper bound obligations, while exclusive slices emit lower, upper, and endpoint-order
  obligations. Compiler cast syntax (`value.cast[Type]`) is classified as a type operation rather
  than runtime indexing. Direct fixed-array parameters with literal primitive extents (`i64[4]`
  or `array[i64, 4]`) may discharge the upper `.count` obligation after the index is separately
  proven below the exact extent; direct nested fixed-array parameters receive the same treatment
  per `IndexN` dimension. Direct pure index-producing calls are admitted only when their verified
  executable summary proves an exact call-free result expression; purity alone, missing summaries,
  and result expressions that still exceed the bound remain rejected rather than being treated as
  safe. Resource places preserve arbitrary named-field paths and closed literal index selectors
  for exact disjointness and borrow-summary composition, including each component of a literal
  multi-index path. Small symbolic +/- index terms are retained as paths only when an explicit
  inequality is emitted and independently replayed; unsupported dynamic selectors still widen to
  the whole root; and
- compiler-defined lower bounds for bare unsigned primitive types (`u8`, `u16`, `u32`, `u64`,
  `usize`, and `uint`) enter the proof context as traced `type-bound` facts. This narrow typing
  fact survives call, assignment, and control-flow havoc, while shadowed loop/pattern/scoped
  bindings and ownership moves remove inherited bounds; all other facts retain the existing
  pure-call/frame havoc behavior; and
- recursive, deduplicated `include` expansion resolved relative to the including file; and
- the compiler's complete semantic diagnostic pass after the proof pass.

Functions declaring unsigned locals (including aliases and refinements) currently report
`unsupported` before logical obligations are published. Substituting their initializers would
erase fixed-width arithmetic semantics. This also temporarily excludes `kernel_core.add_node`;
the core bounds predicates and their call-site proofs still verify and replay. Full typed symbolic
bindings are required to restore these functions, including bounded-safe unsigned locals.

Unknown expressions and opaque calls remain unproven; unresolved call results are made opaque in
the symbolic environment rather than being reused as facts. The compiler semantic pass is run with its
strongest built-in refinement/invariant mode, but the custom kernel still has no SMT backend,
symbolic bit-vector decision procedure, or dependent-type kernel in this first slice. Successful logical
goals are recorded in a flat certificate stream, and the standalone replay kernel independently
rechecks structural facts,
literal `true`, safe closed arithmetic, bounded interval consequences including `/` and `%`, affine
  `i64` identities, bounded difference-constraint closure, bounded integer-range and literal-
  collection quantifiers, bounded disjunctive case splitting, and bounded model-checking certificates.
  Any certificate outside that
  replay surface is reported as a gap and cannot produce a zero exit status. Recursive SCCs with missing, mismatched,
unbounded, or unsupported measures are rejected. Recursive lemma SCCs use the same bounded
lexicographic rule, while external callers consume only the verified summary.
Unsupported runtime expression forms remain rejected at the proof-state boundary. Unlabeled
`break` and `continue` are modeled for loops: an imported invariant must hold on each transfer
path, and a `break` exit does not contribute the loop condition's negation. Labeled transfers
remain unsupported until loop-target resolution is imported.
`parallel for` is a separate fail-closed boundary: its worker body is checked in an isolated
state, but no sequential fact, symbolic value, or worker control-flow result is exported across
the join until isolation, reduction ownership, and join semantics are represented explicitly.
Runtime ownership transfers (`move`) are modeled as conservative state transitions: the moved
root becomes unavailable and all symbolic facts are discarded across the transfer. The resource
kernel now also models the sound local region subset: `region r(size)` and `region r(size):`
introduce tracked lifetimes, `new[r] value` records allocation into `@r` whether its result is
bound, discarded, or passed directly to a reference parameter, aliases/reassignments retain the
region identity, and explicit or implicit region close transitions are replayed. Fresh call
temporaries have no caller-visible place; mutable callee effects are checked but cannot escape or
be exported into caller state. Region-owned values in logical contracts and opaque calls remain
rejected until their provenance is summarized. Exact region-polymorphic
calls are supported when a pinned reference formal witnesses each `[@r]` parameter: the callee
summary records the region return and the kernel replays the mapped `resource-call-result` against
the caller's live region. Scalar-only calls to a region-polymorphic function remain rejected
because an ambient arena is not a proof of a lifetime mapping.
Nested control-flow snapshots also protect inherited region identities: a child cannot destroy and
reopen the same spelling and then make the parent's older lifetime appear live at the join.
The proof checker now carries a separate lexical resource state for a useful ownership slice:
bounded named places (`&x`, `&box.inner`, and arbitrary named-field paths within the kernel depth
bound) have stable structural identities,
shared aliases may coexist, mutable aliases are exclusive, and writes/moves are checked with
prefix-overlap semantics. Named uses and ownership transfers are also emitted as replayable
resource transitions, so use-after-move is rejected by the resource checker and the independent
kernel. Unsupported dynamic indexes conservatively widen to their whole root; small symbolic
 +/- index terms are disjoint only when an explicit inequality is recorded and independently
replayed, rather than guessed. Borrow handles cannot escape. Borrow-carrying calls are admitted only when exact
formal/actual mapping succeeds and the callee has a verified, independently replayed resource
summary; the kernel then replays the callee trace and propagates only checked external writes.
Recursive-SCC, defaulted, dynamic, and opaque calls remain unsupported.
Successful resource checks emit a source-neutral transition trace with explicit lexical scope
nodes, explicit place terms, and post-branch move-join transitions; the independent kernel replays
that trace before counting the resource obligation as certified. A move on any continuing branch
therefore makes the inherited root unavailable after the join. Region allocation is supported
only through the explicit local lifetime transitions described above; richer returned-reference
forms remain an explicit unsupported boundary. Return and assignment boundaries now distinguish a
temporary borrow passed to a verified value-returning call from the value that actually escapes;
direct region-polymorphic reference results with an exact mapped `@r` are also replayed, while
field/conditional/aggregate reference results remain conservative until their source provenance is
summarized. The
  logical expression engine now accepts verified total-pure calls inside value-match arms while
  retaining the independent rejection of effectful or unresolved calls.
The architecture leaves those as later proof engines behind the same AST-level obligation interface.
Quantifiers are deliberately limited to one integer binder for ranges and ordinary finite collections,
or two binders for finite dictionary key/value literals, understood kernel expressions, a
65,536-instance budget, and four nested quantifier levels; dynamic collection quantifiers and
unbounded domains fail closed. Disjunctive facts are handled by bounded case splitting, with each
branch checked independently and the original disjunction removed from the branch context. Loop
termination is checked only for explicit, supported lexicographic `decreases` measures; fall-through paths and
each captured `continue` path are checked at their exact next-iteration state, while missing path states and
unsupported termination forms fail closed. The checker intentionally declines effectful or unresolved default-argument summaries and arithmetic
it cannot establish, including unbounded fixed-width overflow cases. See
[`DESIGN.md`](DESIGN.md) for the trust boundary and extension plan.
