# Elisa Proof design

Elisa Proof is a self-hosted, AST-level verifier. Its executable is written in Elisa and
imports the parser, lexer, AST, and semantic implementation from the sibling `Elisa-compiler`
checkout. An input file is expanded using Elisa's include rules, parsed by the compiler frontend,
checked by the proof kernel, and then passed through the compiler's strongest built-in semantic
diagnostic mode.

## Trust boundary

The proof kernel is intentionally fail-closed:

1. A proof block is erased at runtime, so purity is checked before any fact is accepted.
2. An `assert` proof step is a checked `have`, not an axiom. It must follow from earlier facts.
3. A lemma contributes facts only after its `requires` are established and its own obligations
   are checked. Lemma call graphs are scheduled and checked before summary use; an invalid or
   unavailable lemma summary is rejected at every caller. Recursive lemma SCCs may use
   induction only when both sides provide matching checked lexicographic `decreases` measures and
   the mapped callee tuple is strictly smaller and nonnegative.
   Executable structural recursion may infer a ranking when one or more parameters have enum
   types and no `decreases` clause is written. With multiple enum parameters, the inferred ranking
   is the sum of their constructor heights: every recursive edge must leave each subject unchanged
   or pass a matched strict subterm, and at least one subject must be strict. The inferred measure
    is still checked by the same matched strict-subterm rule; it is not an assumption and does not
    apply to integer or reference parameters. Each accepted recursive edge now emits a
    source-neutral structural certificate containing every preserved/strict ranking component;
    the replay kernel checks that certificate before the report can claim zero replay gaps. The
    source correspondence between a typed match binder and an actual ADT subterm remains an
    explicit compiler/frontend boundary until inductive declarations and pattern typing are
    represented in the standalone kernel environment.
    Captured value blocks are checked against that same environment: an unrelated accumulator or
    cursor capture does not hide a recursive descent, while a capture that overlaps an active
    strict-subterm binder remains conservative and must still be structurally certified.
4. An executable call contributes only its declared `ensure` facts after its `requires` are
   established using the compiler's positional or named-argument mapping. A verified exact
   `changes` frame may preserve facts about disjoint fields; an unframed, lossy, or aliased call
   clears facts and fails any caller frame/preservation obligation. Calls whose omitted default
   arguments are materialized only when the default is supported, has no `old(...)` or unresolved
   formal, and every call is to a verified total-pure function; effectful or unresolved defaults
   are declined at the call boundary.
   Calls nested inside a summarized call's callee or arguments are checked in evaluation order;
   each validated child summary becomes the state seen by the next child, and only then is the
   outer summary applied.
   Recursive strongly connected components are not summarized as ordinary calls. An edge inside
   an SCC is admitted only when both caller and callee declare matching checked lexicographic
   `decreases` measures; every current and callee component is proven nonnegative, and the first
   differing component is proven strictly smaller while earlier components are equal. Missing,
   mismatched, unbounded, or unsupported measures remain rejected; otherwise a function could use
   a postcondition through a cycle as a circular proof.
    Direct structural recursion over an enum is a separate checked rule: the recursive argument
    must be a binder from a matched strict subterm of the decreasing parameter. The same rule
    admits a mutual SCC only when every structural member decreases the same enum type and every
    edge is checked against the callee's mapped decreasing parameter. Whole-value bindings,
    shadowed binders, opaque expression forms, and mixed-type structural SCCs are not treated as
    ranking certificates. Structural facts are intersected at control-flow joins, so a fact is
    retained only when it survives every branch.
   Executable summaries are certified in dependency order over the collected call graph. A
   nonrecursive callee is checked before its callers; recursive strongly connected components
   are checked as one scheduling unit with provisional intra-component summaries. If a body,
   structural check, or dependency boundary fails, its summary is marked unavailable and every
   dependent caller is checked without that summary. This prevents source order or a failed body
   from manufacturing a modular proof.
5. Direct writes are checked against the enclosing `changes`/`preserves` clauses. Calls through
   known summaries must fit the caller frame; opaque calls and writes through a framed or
   preserved alias are rejected rather than treated as pure. Tracked local aliases are resolved
   through the symbolic binding map, while unknown reference-producing expressions are opaque.
6. Assignments and effectful control-flow joins discard facts and forget symbolic values that this
   kernel cannot prove are preserved. Initializers and assignment RHS expressions are evaluated
   against the pre-write environment; only afterward is the new binding or target value committed.
   Unknown expression forms and opaque calls are not used to establish goals. Unsupported runtime
   expression forms remain rejected. Unlabeled `break`/`continue` transfers are modeled only
   inside a loop: every imported invariant is re-proved on the transfer path, and a `break` exit
   contributes the invariant but never the negated loop condition. Labeled transfers remain
   unsupported until loop-target resolution is imported.
   A verified call result may remain bound only as the newly assigned value; failed/unresolved
   call results are opaque and cannot establish a later postcondition. Pre-existing bindings are
   havocked at call boundaries. A call nested below arithmetic, a constructor, a conditional, or
   another non-call root—including a runtime `assert` expression—is admitted only when the
   complete nested call expression is certified total-pure; effectful nested calls remain rejected
   until the evaluator can retain their exact post-call value.
   Runtime ownership-transfer expressions are modeled as conservative state transitions: a moved
   root becomes unavailable and all symbolic facts are discarded across the move. The resource
   state rejects use-after-move before either a use or a new borrow can be established. It also
   models local region identities: both block and statement-form region declarations,
   bound/discarded `new[r]` allocations, same-region aliases, explicit `destroy r`, and implicit
   function-scope close are source-neutral transitions independently replayed by the kernel. Replay
   tracks region liveness separately from its source spelling, invalidating owned bindings and
   inherited aliases at close so a same-named later region cannot resurrect stale storage.
   A direct whole-binding region allocation carries one exclusive owner token; a same-region alias
   transfers that token rather than copying it. A whole-binding region assignment is the same
   move-like transfer for an existing target binding; self-assignment is the only no-op. This
   permits one controlled shared-to-mutable exposure while rejecting duplicate mutable capabilities
   and use of the consumed owner. Region-returning call results also receive the token from a
   fresh return allocation or transfer it from a returned direct owner; borrowed results receive
   no token. Region aliases and region assignments currently carry no source-path metadata, so
   field/index sources are rejected rather than widened to whole-root capabilities. Region
   assignment also rejects a target that is itself an active borrow handle; rebinding such a
   handle without modeling borrow release would leave stale alias metadata in the trace. Borrowed
   or external references have no such token and cannot be upgraded or duplicated as mutable
   aliases by region metadata; transferring a direct owner also requires no overlapping live
   borrow.
   Child resource snapshots additionally mark inherited region identities as protected, so a nested
   `destroy r` followed by a same-named reopen cannot be hidden by the child join even when no
   binding currently carries `r`.
   Region-owned values in logical contracts, opaque calls, and richer returned-reference forms
   remain rejected rather than treated as transparent values.
   `parallel for` is checked in a cloned worker state, but is then a hard proof-state barrier:
   sequential facts, symbolic values, and worker transfers are not allowed to cross its join until
   the kernel models worker isolation, reduction ownership, and structured-concurrency joins.
   Ordinary `for` loops are different: an explicit `invariant` is established at the iterable
   boundary, checked over one arbitrary body iteration, and exported as the only post-loop fact.
   Invariants mentioning a loop binder are rejected because that binder is out of scope at the
   join; missing invariants retain the older body-only, no-post-state behavior.
   Resource checking is a separate lexical state machine, not an imported compiler verdict. It
   resolves bounded named places (`&x` and arbitrary named-field paths within the kernel depth
   bound) to exact structural identities, permits
   disjoint shared borrows, requires mutable exclusivity, and rejects writes/moves whose places
   overlap a live borrow. Named uses and moves are explicit transitions, and the resource state
   rejects use-after-move. Unsupported dynamic indexes conservatively widen to whole-root places;
   small symbolic +/- index terms are separated only by explicit inequality events whose premises
   are independently replayed and source-traced. Successful transitions are lowered to a
   source-neutral resource trace with explicit place terms and scope nodes, then independently
   replayed by the kernel. A borrow-carrying call is admitted only with
   exact formal/actual mapping and a verified callee `resource-safety` root; the kernel replays
   that callee trace from an empty state, checks shared/mutable permissions at the call site, and
   propagates only summarized external writes back to the caller. Recursive-SCC, defaulted,
   dynamic, and opaque resource calls remain unsupported. Region-polymorphic calls additionally
   require one exact pinned-reference witness for every `[@r]` parameter; scalar-only calls cannot
   infer an ambient arena. A callee's `resource-region-return` and the caller's
   `resource-call-result` are replayed against that formal/actual map, so `T& @r` results from
   direct `new[r]` or direct region paths remain live only while the mapped caller region is live.
   Full resource-safety reports must balance every local region at the function boundary; only
   explicit external region parameters may remain active. Prefix replay is exposed separately for
   incremental summary construction and is never itself a proof admission result. Nested scope
   joins likewise require the child region stack to equal the inherited parent stack exactly, so a
   discarded snapshot cannot leak or reorder a lifetime.
   Field, conditional, aggregate, and other richer returned-reference expressions remain outside
   the resource kernel until their identities and lifetime summaries are explicit.
   Continuing control-flow joins emit explicit move-join transitions for inherited bindings moved
   on any branch. The source state and replay kernel both treat those bindings as unavailable
   afterward, while purely lexical child bindings remain scoped and are discarded at the join.
   Return and assignment boundaries classify the produced value separately from temporary resource
   use during its evaluation: a verified call returning an ordinary value may consume a borrow
   without making that borrow escape. A direct return of one reference formal may compose when the
   actual reference is externally owned; field, conditional, aggregate, and multi-source reference
   results remain conservative until their provenance is summarized. This resource distinction does
   still rejects effectful calls inside value-match arms; verified total-pure calls are admitted
   through the same branch-isolated return checker. Expression-catch arm values use the same
   restriction and branch-local summary handling.
7. Function and loop contracts are logical expressions, not executable effect contexts. The kernel
   rejects executable calls and unsupported expression forms in `requires`, `ensure`, `invariant`,
   and `decreases` clauses because structural equality of a call-shaped AST is not a purity proof
   and an unknown AST is not a contract. The modeled exceptions are `old(...)` and calls to a
   verified total pure function. Such functions are checked for immutable parameters, no declared
   effects/frames, no writes, no reads of `global mutable` bindings, and a transitive pure call
   graph. A recursive SCC may qualify only
   when every member has an explicit bounded decreases tuple and every recursive edge still passes
   the ordinary nonnegative/strict-descent checks. Local purity is computed for the whole SCC
   before fixed-point propagation, so declaration order cannot manufacture a recursive summary.
   `old(...)` is checked through entry-state substitution separately.
   Runtime `assert ... by:` and `proof ...:` goals remain runtime guards and are handled at their
   statement boundary.
   A loop without an invariant is still traversed in an isolated entry state, so missing
   invariants cannot hide nested memory-safety, call, ownership, or return obligations.
8. `old(...)` is resolved only from a function's entry snapshot. It is not exported through an
   executable summary until the call state model can carry pre-state snapshots.
9. Integer reasoning is over fixed-width `i64` values. Constant folding and interval arithmetic
   decline overflow, division-by-zero, and other boundary cases instead of treating machine
   arithmetic as mathematical integers.
10. Structural reductions such as projecting a named field from a literal constructor or record
   update are definitional AST rewrites. They do not grant any proposition that is not present in
   the constructed value.
11. `assert ... by:` is checked at its program point. Its proof body must discharge the goal from
    the current facts, and only a successful runtime guard publishes that goal to later statements.
    A substituted assertion containing an unresolved or effectful call is not exported as a
    reusable fact; only call-free or certified-pure expressions survive beyond that evaluation.
12. Arithmetic identity rewrites are limited to operations total for every fixed-width `i64`
   input (`+ 0`, `- 0`, `* 0`, `* 1`, `/ 1`, `% 1`). No cancellation or unbounded algebra is
   assumed.
13. Positive equalities between bare identifiers may form an alias relation and transport explicit
   interval bounds. Calls, fields, and arithmetic expressions are not generalized by this rule.
13a. Reflexivity, symmetry, and coherence between equality and ordering are properties of the
    language's own operators, not of every type. Elisa rewrites `==`, `!=`, `+`, `-`, `*`, `/`
    and the four ordering operators to a user `__eq__`/`__add__`/`__cmp__` whenever an operand's
    type is a struct, there is no built-in struct equality to fall back on, and an aggregate
    value has no `==` at all. Every rule that concludes a comparison because its operands denote
    the same value therefore requires both operands to be witnessed as primitive scalars: the
    reflexive identity shortcut, the definitional-identity test, the identifier-alias rule, the
    cancellation tier's zero difference, and the affine and difference-constraint closures, in
    both the producer and the replay kernel. An unwitnessed operand shape declines; nothing is
    admitted by default.
    A term is witnessed in exactly four ways. A scalar literal (an integer, Boolean, character,
    or one-segment `const enum` value) is self-evident. A term the producer resolved a declared
    primitive scalar type for carries a `__elisa_primitive_scalar_type` marker keyed by that
    exact term, matched structurally — a bare name, a struct field, or the `count` of a built-in
    container; an unsigned width marker is accepted for a name. An element of a built-in
    container carries a `__elisa_primitive_scalar_element(container, depth)` marker and is a
    scalar only when exactly `depth` subscripts, each over a witnessed term, reach it. A former
    whose operator is the language's own is a scalar when all of its operands are.
    The producer records these from declared parameter and local types, following struct fields
    to a fixed depth and built-in container spellings (`darray[T]`, `view[T]`, `array[T, N]`,
    `T[N]`) to their element, and from counting-range binders; each witness is retained and
    invalidated with its root symbol. A call is witnessed only when the callee is a verified
    total-pure function with a scalar declared return type and every argument is witnessed: that
    classification is what makes two occurrences of the call text one value. An opaque call, a
    subscript on a struct (an `__index__` protocol call), a plain enum, a reference to a scalar,
    and every aggregate stay unwitnessed.
13b. Ground congruence closure is a separate, kernel-owned equality rule over the primitive
    scalar fragment. Its universe is the set of subterms of the premises and the goal, its
    relation is seeded only by positive equalities (`and` is transparent and `not (a != b)` is
    the same premise), and it is saturated to a fixed point: two terms are merged when they are
    built by the same former with pairwise equal operands.
    Elisa's operators are not unconditionally primitive. `==`, `!=`, `+`, `-`, `*`, `/` and the
    four ordering operators dispatch to a user `__eq__`/`__add__`/`__cmp__` whenever an operand's
    type is a struct, and a user `__eq__` need not be Leibniz equality: it may compare a subset of
    the fields, so `p == q` does not entail `p.x == q.x`. Indexing and the aggregate constructors
    are user-implementable in the same way. The universe is therefore closed under integer,
    Boolean and character literals, identifiers the producer witnessed as having a declared
    primitive scalar type, and the arithmetic, comparison, bitwise, logical and conditional
    formers over those. A goal outside the fragment declines; a premise outside it contributes
    nothing, which is conservative. The scalar witness travels through the same traced-fact
    channel as unsigned widths: it is a compiler-derived type statement, opaque to every
    arithmetic tier, that proves no proposition by itself, and replay still requires its source
    trace to identify it as a type bound of the owning declaration. An unsigned width marker is
    accepted as the same witness. A field selector, a construction field name, and a literal
    payload belong to a former's identity, not to its operands.
    Excluded formers are not merged at all: `call` carries no determinism witness and no known
    result type, `move` transfers ownership rather than denoting a value, unary `&` is an address
    and two equal values may live at different addresses, `is`/`as` are type operations, `::` is a
    namespace path, `get … else` marks a guarded access, and a quantifier binds names, so its body
    is never entered and a bound occurrence can never join a free term's class. The conclusion is
    always an equality; order and disequality goals are left to the arithmetic tiers. The rule
    runs only after the fixed-width safety guards have rejected every wrapping premise and goal,
    which keeps an equality between operands of different widths from travelling through a
    wrapping former. Term and saturation-round budgets are fixed, and exceeding them declines the
    rule rather than reasoning over a truncated universe. The AST producer does not own this rule:
    it lowers the premises and goal into a scratch arena and calls the same kernel routine that
    re-derives the certificate during replay, so the producer can never find a congruence the
    checker cannot reproduce.
    Admitting field selection, indexing, or the aggregates needs a witness that the receiver's
    selector is the language's own and that the selected type's equality is primitive. That
    witness is not represented in the term language, so those formers stay excluded.
14. Quantifiers are checked only when the compiler-preserved kind is unambiguous and the lowered
    expression has one integer binder over an explicit finite `..<`/`..=` range, or a finite
    literal collection (with exactly two binders for dictionary key/value pairs). The kernel
    instantiates every `forall` candidate or a checked `exists` witness, with a 65,536-instance
    budget and four nested levels. Dynamic collections, missing bounds, unsupported bodies,
    additional binders, and budget overflow are failures, never solver assumptions.
15. A disjunctive fact is used only by bounded case splitting. Each branch receives one disjunct
    and the original disjunction is removed; the goal must be proven in every branch. The split
    depth is capped, and unsupported Boolean forms remain unproven.
    Pure conditional expressions in comparison goals use the same exhaustive shape: the replay
    kernel checks the then branch under the condition and the else branch under its structural
    negation. It never treats either branch as unconditional, and the split depth is bounded.
15b. An unproven obligation is reported with the reason it was not proven. `disproved` carries a
    concrete counterexample, `unsupported` names a form outside the modeled fragment, `timeout`
    means a fixed budget ran out before the search reached a verdict, and `unknown` means no rule
    applied. The decision procedures thread an advisory exhaustion flag out of the quantifier
    instantiation limits, the quantifier nesting cap, and the bounded model-checking domain and
    step limits. The flag never widens what is provable: an exhausted attempt is unproven exactly
    as before, and a counterexample outranks a budget so a refuted goal is never a timeout. Its
    only purpose is to stop the report from telling a client "no rule applied" when the honest
    answer is that the obligation was never decided.
16. Bounded model checking may discharge a goal only when every identifier in the pure
    integer/Boolean fragment has a finite explicit interval, the complete product domain is at
    most 65,536 states, every fact and the goal evaluates without overflow at every state, and
    all states satisfy the facts and goal. It is exhaustive within that finite domain; it is not a
    substitute for an unbounded arithmetic or SMT decision procedure.
17. Every successful logical goal is copied into a flat certificate stream containing its goal,
    source context, and rule tag. It is also lowered into the source-neutral
    `elisa-proof-kernel-v1` arena: canonical operator/literal/name nodes, child indices, and
    explicit certificate/trace root ranges. A separate replay module independently checks the
    arena for structural fact entailment, literal `true`, safe closed arithmetic, bounded
    intervals including `/` and `%`, affine fixed-width identities, bounded difference-constraint
    closure, bounded integer-range and literal-collection quantifiers, bounded disjunctive and
    conditional case splitting, and bounded model-checking certificates. The arena, term
    normalization, and goal walkers that consume potentially malformed nodes carry explicit finite
    depth budgets; malformed or excessively deep terms become replay failures rather than
    host-recursion hazards. Replay requires every certificate fact root to match a source-level fact
    trace. Proof-step traces retain kernel premise roots and are recursively re-proved by the
    source-neutral kernel; modular summary traces retain their callee dependency and recursively
    replay every non-cyclic certificate owned by that dependency. A dependency already on the
    replay stack is treated only as an explicit SCC induction boundary, and still requires proven
    goals with no findings. A goal outside the replay surface remains a visible replay gap and
    makes the command non-successful. This is a materially smaller trust boundary than replaying
    compiler AST nodes, but it is not yet a separately compiled/minimized kernel: trace
    production, summary semantics, and program-state derivation remain in the main checker.
18. Statement-match arms contribute a positive variant-tag fact when the compiler AST gives a
    stable dotted path (`value is Enum.Variant`) and exact equality/range facts for boolean and
    integer literal patterns. Character literal text is also lowered as an exact scalar equality
    without escape normalization; string pattern text is not type-tagged by the imported AST and
    remains unsupported. Pinned patterns contribute an equality with the existing binding. Named
    struct and named variant payload binders receive symbolic
    field projections, and tuple binders receive indexed projections. Closed OR-patterns with no
    payload binders contribute one disjunctive fact; OR-patterns with payload binders, null,
    positional enum payloads, or richer nested shapes whose lowering is not represented precisely
    remain unsupported. The checker never turns an opaque binder into an axiom. A pure
    value-match expression is admitted through a stricter lowering: closed
    literal/range/tag/or-patterns, single-expression arms, named variant-field projections,
    no positional/opaque payload binders or effectful calls/moves, only verified total-pure calls,
    and a final unguarded wildcard are translated to the kernel's conditional AST. Each arm is
    checked against an isolated state before its value is checked against the enclosing ensures.
    Partial or richer value matches remain rejected until their exact decision-tree semantics and
    certificate representation are available.
19. Every runtime single-index access emits two memory-safety obligations: `0 <= index` and
    `index < place.count`. Exclusive slices additionally emit `0 <= low`, `high <= place.count`,
    and `low <= high` for explicit endpoints; open endpoints inherit the implicit `0`/`count`
    bounds. The initial heap slice recognizes only directly tracked collection-like places
    (identifiers, fields, scopes, and refinements); calls, nested dynamic indexes, and incomplete
    or aliased multi-index shapes are unsupported and cannot silently pass. A direct index,
    multi-index position, or slice endpoint may contain a call only when the callee is total-pure,
    already verified, its preconditions are proven, and its summary exports an exact call-free
    result expression; purity without a result bound remains opaque. Direct nested
    fixed-array parameters with literal dimensions are checked per index argument. Counting-range facts can discharge these
    obligations. A direct function parameter whose type is a literal fixed array (`array[T, N]` or
    primitive shorthand `T[N]`) contributes no bound by itself: the checker must first prove
    `index < N`, then imports `index < parameter.count` as a traced type-bound fact. Generic
    `array[T, N]` forms accept any element expression with a literal nonnegative extent; the
    shorthand `T[N]` is restricted to primitive scalar element heads. Aliases, dependent extents,
    arbitrary paths, and dynamic arrays remain explicit obligations. Resource traces additionally
    retain closed literal index components, including all components of a bounded multi-index path,
    for exact disjointness; symbolic/dynamic heap aliases
    and element-level validity remain future work.
    The compiler's `value.cast[Type]` form is an AST `Index` only because its type argument uses
    brackets; the checker recognizes the reserved `.cast` selector and excludes it from runtime
    bounds obligations. This exception does not apply to ordinary collection indexing. The
    compiler's `get collection[index] else fallback` form is a separate checked-index operator:
    its runtime fallback handles both negative and out-of-range positions, so the proof checker
    does not invent ordinary index obligations for that outer access. It still recursively checks
    the receiver, index expression, and fallback; the resulting element value remains opaque
    until the heap/content model can express its semantics. Each admitted checked access emits a
    dedicated `checked-index` certificate, and the independent replay kernel validates its arena
    shape before counting the safety boundary as replayed. A statement-level `get EXPR else
    return/raise/break/continue` is a separate control-flow form: the guarded value is checked on
    its normal path, while the recovery body is checked in a cloned state and must terminate on
    every path. For a direct guarded index, the runtime no-load boundary is emitted as a distinct
    `checked-get` certificate and replayed independently from the recovery proof. A recovery block
    that falls through, a nested GetElse expression, or a labeled transfer remains unsupported;
    no recovery-side binding or fact is allowed to leak into the success path.
    Expression-position `catch` is currently a deliberately closed fragment: it must catch a
    direct fallible call with an unguarded success arm, a final explicit error catch-all, and one
    pure value expression per arm. The success branch may consume the callee's verified result
    summary; error branches receive only a disposable call/frame probe and retain ambient facts
    only for a verified pure callee. This avoids applying a success-only postcondition to an error
    result. Nested catch, effectful arm values, payload projections, and statement-valued arms stay
    rejected until the kernel has an explicit error-state and arm-decision representation.
20. Independent kernel expression equality must preserve receiver structure for fields and scopes:
    `left.value` and `right.value` are unequal unless their receiver terms are equal. The replay
    kernel never compares a selector name in isolation, because doing so would let a certificate
    transfer a fact between distinct storage paths.
21. The checker imports only the compiler's exact lower-bound guarantee for bare unsigned primitive
    types (`u8`, `u16`, `u32`, `u64`, `usize`, and `uint`) and records it as `type-bound` provenance.
    This narrow type fact survives call, assignment, and control-flow havoc because the binding's
    static type still guarantees it; all other symbolic facts retain the ordinary pure-call/frame
    rules. Shadowed loop, pattern, and scoped bindings remove inherited bounds, and ownership
    moves still discard the complete fact state.
22. Branch complements use only structural Boolean rules that preserve the source proposition:
    double-negation and De Morgan normalization for `and`/`or`. A guarded Boolean call may then
    consume its exact verified summary equality to expose the equal postcondition; the replay kernel
    repeats that same call-shaped equality rule, while arbitrary equalities are not generalized into
    unrestricted rewriting.

23. A leading-dot const-enum value with exactly one selector (`.Variant`) is a closed source
    value and is lowered to a distinct `shorthand` leaf in the certificate arena. It is never
    normalized to an identifier, because that would conflate an enum value with a variable of
    the same spelling. The independent arena validator requires the shorthand leaf to have no
    child edges, payload metadata, or secondary selector. Multi-segment shorthand remains
    outside the kernel until the certificate carries the enclosing enum/type identity needed to
    distinguish qualified paths.

24. Slice expressions are lowered to `slice(object, low, high)` with all three child roots
    explicit. An omitted endpoint is represented by an `absent` leaf rather than a null/sentinel
    index, so `[:high]`, `[low:]`, and `[:]` remain structurally distinct from malformed terms.
    Arena admission recursively validates the three edges and requires both node kinds to be
    metadata-free apart from their defined payloads; replay equality and substitution preserve
    the complete slice structure.

25. Multi-argument index/application expressions are lowered to an `index-n` node whose receiver
    and nonempty argument child slice are both explicit. The node is a logical identity boundary,
    and executable nested access receives a memory-safety rule only when the receiver is a direct
    parameter with literal nested fixed-array dimensions: each argument gets an independent
    lower/upper obligation in receiver-to-element order. Dynamic, aliased, generic, or incomplete
    shapes remain opaque. Arena replay nevertheless validates every argument edge, range, and
    metadata field, and substitution preserves them.

26. Kernel quantifier instantiation must substitute through every admitted composite term, not
    just arithmetic leaves. Arrays, tuples, sets, dictionaries, conditionals, checked accesses,
    calls, field initializers, and record construction/update retain their child graphs and
    metadata under substitution; an invalid child range or unsupported substitution shape is a
    replay failure, never a quantified assumption.
27. A declared effect row is contained, not inferred. When a function writes `can[...]`, the
    checker proves that its row covers the declared row of every function it calls, and the
    kernel re-derives that containment from `effect`/`effect-row`/`effect-call` nodes alone. The
    claim is exactly "the declared rows of this function's callees are members of this function's
    declared row" and nothing more: a callee whose row was never imported makes the obligation
    `unsupported` instead of treating the missing row as empty, an abstract row has no comparable
    members and is refused, and what a body performs without going through a call is the
    compiler's effect checker's obligation, not this one's. A function with no written row states
    no claim and is not checked.

The arithmetic kernel also has a bounded affine-difference rule for one bare identifier plus a
constant. It may establish a relation such as `x + 1 > x` only after fixed-width overflow safety
is proven from explicit bounds (including bounds transported across identifier equalities).

It also closes a bounded graph of normalized constraints `x - y <= c`. This proves transitive
relations between distinct identifiers and affine offsets when each source and target expression
is overflow-safe. The graph has fixed node and constraint caps; overflow in a path sum makes that
path unavailable, and unsupported forms remain unproven.

The interval tier also bounds `/` when the divisor is a known nonzero constant and both dividend
endpoints are known, and bounds `%` by the absolute divisor minus one. The `MIN_I64 / -1`
case and `MIN_I64 % -1` are declined rather than relying on backend-specific overflow behavior.

For a normally completing loop, the post-loop state contains only checked invariants and the
negated loop condition. Symbolic values for locals are forgotten across iterations unless the
invariant reintroduces the needed relationship; this is an intentional soundness boundary.

An unlabeled `break` is a separate loop-exit path: it must re-establish the nearest loop's
invariant, and its post-loop state retains that invariant without assuming the loop condition is
false. An unlabeled `continue` must likewise re-establish the invariant before the next condition
check. Transfer paths with no invariant state are allowed only when the surrounding loop's
post-state is discarded; labeled transfers remain unsupported.

The same forgetting rule applies after a potentially mutating branch, match arm, loop body,
value block, or embedded call. Embedded calls are evaluated in source order; after each child
call, facts and symbolic values are updated before the next sibling or enclosing call is
summarized. This prevents a branch-local assignment or call side effect from being mistaken for
the pre-branch symbolic value at a later return. A declaration does not enter the symbolic scope
until its initializer has finished, and a local call result is not re-applied when returned later.

An explicit loop lexicographic `decreases` measure is checked independently: every component must
be nonnegative at the loop head and after every body path that can fall through to another
iteration. A straight-line body ending in an unlabeled `continue` is checked at that transfer
edge as well. On those paths, the first differing component must be strictly smaller while
preceding components are equal. Both `decreases (outer, inner)` and repeated `decreases outer` /
`decreases inner` clauses are accepted; `decreases*`, empty tuples, and unsupported components
are rejected rather than treated as termination certificates.

Continue termination edges are represented as flat, region-safe snapshots of names, values, and
facts with explicit start/count offsets. Branches, blocks, and recovery paths propagate their own
snapshots, and the checker proves every captured edge independently; a normal fallthrough edge is
checked separately when it coexists with continues. If a path cannot produce a precise snapshot,
the edge remains rejected rather than being collapsed into a potentially unrelated join state.

The command succeeds only when the proof report has no failed finding, the compiler semantic pass
has no error-severity diagnostic, and every emitted certificate replays. A green result therefore
means that every obligation the current main kernel knows how to generate was discharged and that
the current replay kernel independently checked each successful certificate. Unsupported features
are conservative failures or explicit replay gaps, not implicit axioms.

The `--json` command mode exposes the same result as a stable structured document: a compatibility verdict,
an explicit verification state, expanded-source identity metadata (`bytes` plus an observational
FNV-1a-32 fingerprint), trusted-boundary counters,
and an explicit `trust.trusted_assumptions` ledger (empty for the current system),
summary counters, findings, replay coverage, every logical goal attempt (including failed goals),
    and flat successful certificates whose facts and goals are encoded as expression trees. The
    `declaration_details` array gives source-level names, parameters, contract counts, recursion,
    purity, structural metadata, and executable-summary status/reason for proof-state clients; it
    is observational and does not
    affect kernel acceptance. Every
    goal and certificate has a deterministic report-local identifier, each goal links to its
    certificate when one exists, and summary-derived facts expose explicit theorem dependencies,
    so an agent can target one obligation and invalidate affected summaries without scraping human
    output. The
    `semantic_diagnostics` array carries the compiler's filtered structured findings (stable
    append-only kind ordinal, severity, source span, typed context, effect references, and the
    canonical compiler message), so an agent can distinguish a proof hole from a frontend/resource
    error without scraping human output. Failed
    logical findings include an optional exact `counterexample` assignment. Each fact
    also has a parallel `fact_origins` entry identifying its checked source category and location, or
    `null` if the certificate is not replayable. The top-level `kernel` object reports the stable
    arena format and its node/child/certificate-fact counts. This is the initial agent-facing proof-state
    contract; future interactive operations can add dependency edges without requiring agents to
    parse the human report.
    The `repair_queue` is a deterministic projection of failed goal attempts. It carries the same
    report-local goal IDs, source locations, rules, replay status, structured failure diagnostic,
    optional counterexample, and theorem dependencies as the full goal stream, allowing an agent to
    focus repair work without scanning successful goals.
    `dependency_index` supplies the reverse mapping from dependency names to consuming goal IDs,
    so a changed theorem or executable summary can invalidate downstream obligations directly.
    The report also advertises the stable `elisa-proof-tactics-v1` action protocol. Its Elisa-native
    state layer provides kernel-backed `assumption`, `exact`, `decide`, `intro`, `apply`, `simp`,
    `have`, `instantiate`, `rewrite`, `split`, `left`, `right`, and `cases`; `simp` is restricted
    to checked closed constants and `instantiate` to checked finite integer-range or literal-
    collection members;
    branch actions produce independent child states and failed actions do not
    mutate a goal into a proof. This is a capability declaration, not an unchecked proof escape
    hatch: all closing actions reuse the same bounded prover and all structural actions are
    restricted to their corresponding proposition shapes.
    Every tactic state records its initial facts and goal plus a deterministic post-state trace
    containing the action, accepted bit, explicit arguments, reason, and resulting goal/fact
    snapshot. `proof_tactic_replay` rebuilds the state from that snapshot and checks every
    recorded transition, including rejected attempts. `proof_tactic_kernel_trace_replay` then
    lowers every snapshot and argument into one source-neutral arena and invokes the independent
    `proof_kernel_replay_tactic_step` rule for each transition. This makes AI/editor proof scripts
    auditable and reproducible at both the AST protocol layer and the independent kernel layer.
    A solved tactic state also exposes `proof_tactic_kernel_replay`: it lowers the final facts and
    goal into the source-neutral arena and calls the independent replay kernel, so mutable state
    flags cannot by themselves certify a false proposition.
    `proof_tactic_kernel_certificate_replay` composes the two checks into one admission boundary:
    a client must provide a valid complete trace and an independently replayable solved goal.
    `proof_tactic_kernel_branch_certificate_replay` composes two solved child certificates with
    a parent `split` or `cases` transition, checking the proposition shape and exact child fact
    contexts in the source-neutral arena. The portable runner generalizes this relation with
    `proof_tactic_json_tree_certificate_replay`: each nested branch is stored in postorder and
    every child certificate and parent-to-child transition is checked iteratively by the same
    source-neutral rules.
    The executable also imports a portable JSON action script through `--tactics SCRIPT SOURCE`.
    Its ordered `actions` are reconstructed into a fresh compiler AST store; expected action
    outcomes are checked when present, then the complete trace and final certificate are replayed
    through the same two independent layers. A reusable script may provide explicit `initial`
    facts/goal state. A declaration-level script may instead provide `target: {"goal_id": N}`;
    the runner selects the exact goal and traced facts from imported `ProofReport.goal_attempts[N]`
    and rejects `initial` in that mode. This makes the source-goal identity part of the checked
    input, rather than relying on a source fingerprint to prove that a script addresses the right
    proposition. An optional exact unsigned `source_fingerprint` still binds the script to the
    expanded imported source, and the command fails on a mismatch. The JSON interchange now
    accepts one final parent `split`/`cases` action with
    exactly two child action scripts under `branches`; child states are initialized only by that
    structural action and both are included in an admitted result. Nested branches are bounded
    to depth 32 and represented by a flat postorder certificate tree; child state injection and
    malformed tree edges remain rejected.

## Current proof language

The initial surface supports `requires`, `ensure`, `changes`, `preserves`, `invariant`,
`proof GOAL:`, and `assert GOAL by:`. Bare `proof GOAL:` blocks are isolated proof walls;
`assert GOAL by:` additionally supplies the caller's current facts. It handles Boolean structure,
bounded integer comparisons, safe constant arithmetic, local symbolic substitution,
branch-sensitive returns and comparison complements, loop invariant establishment/preservation,
entry-state `old(...)` postconditions, compiler-marked lemmas, compositional executable function
summaries with pure default-argument materialization, constructor/record result projection, a
conservative bounded nested-path frame calculus with subtree permissions and overlap-aware alias
mapping, checked lexicographic loop and recursive `decreases`
measures, direct structural enum recursion, bounded integer `forall`/`exists` contracts over ranges
and finite literal collections by finite instantiation, and recursive-lemma cycle rejection.
Runtime single-index reads and writes also produce replayed lower/upper bound obligations for
directly tracked `.count` places. Direct fixed-array parameters with literal primitive extents may
add the exact `.count` relation only after proving the index below that extent; opaque heap shapes
and dynamic array counts remain unsupported without an explicit bound.

Dogfooding is a hardening milestone, not a trust shortcut. The kernel boundary is checked through
the same import/check/replay pipeline: `src/proof/kernel_core.elisa` verifies its own source-neutral
`root_valid`, `range_valid`, and replay-depth contracts, while the dogfood gate exercises arena
admission, certificate-root provenance, replay determinism, and the isolated replay module.
Progressively larger checker modules remain the next self-verification target. Self-verification
must not special-case the proof binary or count its own claims as external evidence.

`scripts/dogfood.sh` makes this measurable: the foundational layers must be proved and replay
complete, while `ELISA_DOGFOOD_FULL=1 scripts/dogfood.sh` audits the complete imported
implementation and requires every emitted certificate to replay even though unsupported compiler
obligations still keep the overall verdict failed.
The gate also repeats every probe and compares the JSON reports byte-for-byte, so proof artifacts
must be deterministic as well as replayable.

The public source-neutral arena-admission entry point is exercised by an adversarial fixture whose
unary node points to itself. The admission layer rejects that cycle before logical replay, while a
separate `true` certificate in the same input remains replayable; this prevents malformed arena
input from being masked by unrelated valid certificates.
The dogfood gate also compiles and executes a native Elisa harness against the runtime; that
harness rejects cycles, out-of-range edges, malformed call-child shapes, and hidden node metadata
while accepting valid DAG sharing. Arena admission uses an explicit DFS work stack, so hostile
certificate depth cannot consume the host call stack; the same 127-level bound is carried in each
work item and remains fail-closed.

The first arena-boundary slice is now active: before either source-neutral logical replay entry
point consumes a certificate, it walks the reachable `ProofKernelNode` DAG. Node roots and child
indices must be in range, collection/call child slices must satisfy the standalone Elisa
`range_valid` contract, recursion depth must satisfy the standalone `depth_valid` contract, call
children must have the `call_arg` shape, every node kind must use its canonical field layout, and
back-edges are rejected. The admission walk is iterative with explicit DFS colors, rather than
depending on host recursion; the old recursive traversal is not on the public admission path.
Repeated visits to a completed valid node are allowed as ordinary DAG sharing; the validator also
memoizes invalid results so a malformed shared node cannot pass on a later visit. This validation
is deliberately separate from the producer and is the admission boundary required before accepting
future serialized or cross-process certificates.

Before arena replay, every certificate is also matched to the exact successful goal attempt that
emitted it: owner, rule, source fact range, and source-neutral goal/fact roots must agree. The
source-level goal is retained as a report mirror; the arena root is the canonical semantic identity.
A replayable orphan root is therefore still rejected as a provenance gap.

The replay engine is a named `ElisaProofKernelReplay` module that imports only the AST-free
`ElisaProofKernelCore` layer. A standalone semantic-compilation fixture checks that this module
does not accidentally acquire a compiler-AST or report-model dependency. That is a dependency
isolation check, not a claim that the full replay implementation has already been formally
verified by Elisa-Proof; progressively annotating and dogfooding the replay engine remains work.

The next high-value kernel extensions are symbolic index/heap alias reasoning beyond the current
closed-literal indexed-place calculus, interprocedural region/resource summaries that can replay
borrow lifetimes, an independently checked SMT/bit-vector backend behind
the same obligation interface, and structured-concurrency isolation/reduction rules. These should
extend the kernel without weakening the rules above.
