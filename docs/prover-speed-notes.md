# Prover speed work (WIP)

- Branch `prover-speed` from `mocap-cleaner-proofs` 7571dfa.
- ELISA_COMPILER_REV bumped d8b5d305 -> 6a4dc861 (studio-globals stage1, newest).
- Build: build.sh already defaults to -O2 (project.json "opt": "0" is not what build.sh uses).
  Build needs HOME pointed at an empty dir: otherwise build.sh reads ~/.elisac/stage1/SNAPSHOT
  (b841e64b) and reports a false stage1/frontend mismatch for the studio-globals binary.
  Local O2 build: ~9 min wall, ~4 GB peak.
- The prover has no external SMT solver (no z3/process spawn); obligations go to built-in
  linear/difference-constraint procedures. "SMT query cache" therefore means caching
  built-in decision results.
- Baseline timings (build/proof-baseline-19611a2.tsv, winpc, 3 jobs): corpus total 734 s;
  slowest: cli/main 55, retime_apply 45, presets 42, rig_physics 39, rig_cache 35,
  ops_file 34, rig_stack 32, corrections 25, glb_tracks 25, retime_laws 24.
- Mac load average was ~300 at 09:46, so local timing is not usable; time on v80/v32/v20.

## Next
1. Profile cli/main, retime_laws, glb_tracks, rig_physics, track with elisa-profiler
   (--mode sample, ELISA_COMPILER_ROOT=elisa-compiler-worktrees/studio-globals) or `sample`.
2. Cross-compile (scripts/remote in mocap-cleaner) and time on the fleet.

## Decision-procedure result cache (branch `agent/prover-result-cache`, not yet built)

Code: `src/proof/check/goal_result_cache.elisa`, used from `proof_certify_goal_with_rule`
(`check/bounds_and_facts.elisa`), reset in `proof_reset_report`.

**What is cached.** The boolean returned by `proof_goal_with_operator_mask` -- the entry point
of the built-in decision procedures -- for each call made while certifying a goal (the plain
decision, the `__elisa_linear_certificate` probe, and the certificate/hint-extended retries).
Nothing downstream is skipped: a hit still records the goal attempt, encodes the facts, emits the
certificate, and independent kernel replay checks it exactly as before. Other `proof_goal`
callers (tactics, alias transfer, indexed writes, ...) are untouched.

**Key.** Exact, not normalized:
- the premise list, in order, node by node;
- the goal;
- the source operator mask;
- and, as a cache-wide precondition, the enum annotation table.
Node equality compares variant, operator, literal payload, names, *parentheses*, and the full
source position of every node. A 32-bit FNV-style hash of the same data only chooses the probe
path in an open-addressed table; a hit always requires full equality, so a collision is a miss.
Any term outside the plain expression shapes (blocks/quantifiers, records, lambdas, ...) makes
the call uncacheable and it simply runs. Cache scope is one verification run (one report), which
covers every function in it -- the useful cross-function hits are callee contracts and
summaries substituted into many callers, which keep the callee's source positions.

**Why not canonical variable names or sorted hypotheses (as first proposed).** Both can change
verdicts here:
- the procedure is incomplete and order-sensitive: fact membership is first-match, disjunct and
  linear pruning walk facts in order, and the case-split budget is spent in that order, so a
  permutation of the premises can turn a proof into a non-proof without any budget flag;
- names carry meaning: call names resolve to contracts, `__elisa_*` identifiers are markers
  that switch tiers on and off, and bounds are keyed by identifier;
- positions carry meaning: an integer literal's u64/usize type is looked up in the annotations by
  its `(line, offset)` (`proof_integer_literal_tag`) and a quantifier's kind by its line
  (`proof_quantifier_kind`), so equal shapes at different places can decide differently. That is
  also why positions are in the key and parentheses are not stripped (`proof_expr_equal` strips
  them; `proof_goal_depth` matches some shapes on the unstripped goal).
Normalization could be added later only for a sub-language shown to be order/name/position
insensitive, and only with a corpus run proving identical verdicts.

**Invalidation.**
- New run: `proof_reset_report` clears the cache (entries hold AST handles of that run).
- Different annotation table than the one the entries were computed under: whole cache flushed.
- Full (65,536 entries or 4M stored premises): stops inserting; calls still run normally.
- Prover version: not needed in-run (one binary per run). There is no on-disk cache yet; see below.

**Never cached.** Any call that set `exhausted` (a budget ran out) -- so a budget-limited "no" is
never replayed as a decided failure -- and any call entered with `exhausted` already set. The
procedure has no wall-clock timeouts; budgets are counters local to the call.

**Why verdicts cannot change.** `proof_goal_with_operator_mask` is a pure function of exactly the
inputs in the key: it takes no report, declares no effects beyond allocation/panic, and starts its
split budget at zero on every call (`linear/goal_api.elisa`). The procedure reads positions only
from the AST it is given, and those are in the key. So equal key => the rerun would return the
same `(proven, exhausted=false)`, which is what the hit returns. Certificates are still built and
replayed per attempt, so even a hypothetical cache bug would surface as a replay gap, not as an
unchecked proof.

**Measuring.** `report.goal_cache_hits` / `goal_cache_misses` are counted but not yet printed.
To validate: build, run the corpus with and without the cache (e.g. temporarily make
`proof_goal_cached` call straight through), and diff the reports -- they must be byte-identical
apart from timing. Then compare `build/proof-baseline-*.tsv` timings.

**Persistent cross-run cache: not implemented.** It would need an exact on-disk serialization of
the key (every node with positions, names and the annotation table) keyed additionally by
`ELISA_COMPILER_REV` plus a hash of the prover's own sources, since a source position is only
meaningful for an unchanged file. Because positions are in the key, any edit above a goal in a
file invalidates every goal below it, so the hit rate on an edited file would be low; worth it
only if in-run measurements show the procedure (not encoding/replay) dominates.

### Duplicate-work fix: certificate fact-trace lookup

`proof_certificate_fact_trace_index` (`model/report_recording.elisa`) runs for every premise of
every goal attempt (and inside the existing index-goal memo) against every trace of the current
function, and each comparison was a full `proof_expr_equal`, which re-validates both whole terms
before comparing -- O(premises x traces x term size) per attempt. It now rejects an unsupported
fact once, and skips traces whose root (parentheses stripped, as the comparator strips them) is a
different variant / operator / name / literal, which `proof_expr_equal` would reject anyway. Same
index returned in every case.

Looked at and left alone: the double decision in `proof_certify_goal_with_rule` (plain, then with
the certificate marker) is two different fact lists by design and now benefits from the cache
when repeated; `proof_facts_propositionally_inconsistent` is quadratic in facts
(`proof_fact_denies` per fact) but runs once per goal and is cheap per pair; the next candidate is
an incremental hash index for fact traces, which needs a build to validate.
