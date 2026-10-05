# P-04 artifact readiness

**Status: prerequisite missing; no reusable artifact is shipped.**

P-04 requires immutable frontend and declaration-verification artifacts that can be safely
reused after a source edit or process restart. The current proof checker does not expose the
identity and dependency data needed to make such reuse sound, so this milestone remains open.

## Existing pieces

- `ProofReport` in `src/proof/model.elisa` retains parsed `source_declarations`, annotations,
  declaration summaries, theorem summaries, and replayable certificate arenas for one check.
- `ProofFunctionTable` carries resolved call rows and targets, and the checker computes recursive
  components for scheduling. `ProofLemmaTable` similarly carries lemma calls/components. These
  are mutable checking-session tables; they are not emitted as a stable per-declaration graph.
- `scripts/build_manifest.py` records a proof build's source closure, compiler tree/product,
  runtime, target, mode, and environment. It is build evidence only. The proof executable does not
  load this manifest or use it to validate a persisted frontend or declaration artifact.
- `scripts/report_cache.py` caches complete JSON reports for exact fixture/include bytes,
  executable bytes, and relevant environment. It reruns cache misses as whole checks; it does not
  selectively reuse declarations or certificates.

## Missing interfaces

1. **Canonical compiler artifact identity.** The proof checker needs a compiler-owned, versioned
   frontend identity for serialized parse/resolution/type artifacts. The plan explicitly binds
   P-04 to compiler C-04 identities, while the compiler plan still lists C-04 as future work
   ([Elisa compiler plan](../../Elisa-compiler/IMPLEMENTATION_PLAN.md), C-04). Build provenance
   hashes are not a substitute for a stable semantic artifact format or compatibility contract.
2. **Stable declaration records.** There is no canonical declaration ID plus immutable semantic
   summary covering types, constants/defaults, overload/protocol resolution, contracts, effects,
   regions, termination, imported lemmas, and bodies when unfolded. Existing AST nodes and table
   indices are tied to one parse/check lifetime.
3. **Complete dependency and invalidation ledger.** Resolved call edges and SCCs cover only part
   of the required dependency kinds. The checker does not retain reverse edges or dependencies
   for failed/unsupported checks and unresolved names, where declaration additions can change
   resolution.
4. **Artifact reload/admission path.** There is no bounded versioned decoder and no shared loader
   that rechecks source/compiler/dependency identities and independently replays reused
   certificates before they affect admitted theorem sets.

## Acceptance work that must follow

Once those interfaces exist, P-04 needs an edit-corpus test proving that one declaration body
change invalidates its reverse dependency closure while unrelated declarations are reused, plus
fresh-versus-incremental equality for admitted theorem sets, completeness, and trust ledgers.
Persisted artifact tests must reject corrupt/truncated bytes, stale source/compiler/dependency
identities, missing dependencies, and incompatible schemas. No such test is meaningful against
the current report-only cache because it has no declaration artifact to load.
