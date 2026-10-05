# P-05 local session readiness

## Current evidence

[`scripts/test_p05_package_restart.py`](../scripts/test_p05_package_restart.py) checks that a producer can persist a nonempty package and a separate, fresh `elisa-proof-replay` process independently replays every theorem. It also checks refusal of a package marked source-inadmissible, a forged disk `proven` field, forged `source.authenticated: true` and elevated trust, altered statements/fingerprints, and truncated JSON. This establishes package restart/replay behavior for the tested fixture; it does not establish that a package is bound to current source. Packages explicitly report `source.authenticated: false`, and their FNV fingerprints are identity hints.

The CLI currently runs synchronously from file import and parsing through semantic checks, proof search, replay, and final output. The checker API creates a fresh report and reconstructs its declaration tables. There is no retained frontend store, request/session identity, cancellation signal, source version, publication callback, or generation check. Package replay checks abstract sequents without the source frontend, so it cannot stand in for current-source admission.

## Interfaces required before a session can reuse or publish results

1. Immutable source snapshots with cryptographic identities, including imported-file closure and the compiler/frontend/type-checker, target, kernel, and checker identities that affect admission.
2. Immutable parsed/resolved/typed artifacts with explicit per-declaration dependencies, including failed name resolution and dependencies on types, constants, defaults, overloads, instantiated callees, contracts, effects, regions, termination, imports, and checker versions.
3. Reverse dependency edges and SCC grouping, so an edit invalidates the complete affected closure and recursive summaries are verified and published atomically.
4. Certificates bound to the exact source snapshot, declaration context, dependency identities, and checker version. A reused certificate must pass the shared admission path and independent replay; a package `proven` bit or source fingerprint is insufficient.
5. A request generation/version token checked at the publication boundary, with results staged privately and committed atomically only if their source/session generation is still current. Cancellation must invalidate that token before any result can become visible.
6. CLI and session entry points that call the same source-admission and replay implementation, preserving the CLI as a supported one-shot route.

P-04 now has a versioned proof-side declaration envelope bound to its build/checker context, exact declaration source slice, ordered dependency identities and payload digest. It is not yet emitted from canonical resolved/typed frontend artifacts, and no source dependency graph or reverse invalidation scheduler exists. The current API therefore has no basis for computing source-edit invalidation or proving that a certificate belongs to the current declaration context. A session wrapper around the current whole-file CLI would add orchestration without safe reuse or stale-publication guarantees.

## Remaining P-05 acceptance tests

- For cold and incremental runs, compare admitted theorem sets, completeness states, and trust ledgers exactly.
- Edit a declaration body and verify invalidation of its reverse dependency closure; change a public contract/type/import and verify all affected callers invalidate; edit an unrelated declaration and verify unaffected artifacts are reused. Include newly added declarations and formerly failed name resolution.
- Verify recursive dependency SCCs invalidate and publish as one unit, including interrupted checks.
- Reload artifacts in a fresh process and independently replay all reused certificates against their bound identities. Reject stale source/context/checker identities, missing dependencies, invalid dependency cycles, and incompatible schema versions.
- Reject malformed, truncated, digest-mismatched, or over-budget artifacts without changing the current admitted result.
- Race two source generations and cancel an in-flight request. Confirm only the current generation can publish, including when cancellation or process interruption occurs during staged persistence.
- Exercise CLI and local-session admission on the same positive and negative fixtures and compare their proof/admission outcomes.

Until these interfaces exist, P-05's restart/replay slice has evidence, while incremental invalidation and canceled-request publication remain unimplemented.
