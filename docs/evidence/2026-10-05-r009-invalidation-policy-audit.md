# R-009 artifact invalidation policy audit — 2026-10-05

This source/test inventory was reviewed on proof HEAD `710733757fcbf533f505adfea1df101b35fc9f1d`.
It describes existing identity and replay controls. It does not claim a complete inventory of
historical incidents, run the tests, or establish a current product's behavior.

## Existing version and invalidation controls

- `scripts/report_cache.py` keys reports by its cache schema, the top-level input and every
  textual include's SHA-256, exact executable path and bytes, host system/machine, proof-affecting
  `ELISA_`/loader/locale environment, and the report-cache implementation recipes. A changed
  binary at the same path therefore changes the key. Cached payloads need a matching SHA-256,
  parseable report, and status/exit-code pair. An invalid or incomplete entry is a cache miss.
- `scripts/declaration_artifact_identity.py` accepts a fixed artifact schema and binds each
  record to the build manifest's proof source, proof executable, frontend revision/tree, compiler
  product, runtime, target and compile mode. It also binds the exact declaration source slice,
  payload digest, and ordered dependency identities. Store reads validate the current inputs and
  reject unsupported schemas, truncated/oversized entries, identity mismatches and payload
  corruption. Publication is immutable and atomic.
- `src/app/package_output.elisa` labels hypotheses and source correspondence as adapter-trusted
  and source authentication as false. `src/portable/package_reader.elisa` dispatches only
  `elisa-proof-package-v1`; `src/portable/package_checker.elisa` ignores any disk success claim
  (the schema has none) and recomputes the sequent identity and fingerprint before invoking the
  kernel on each theorem. Packages are therefore rechecked by the executable that reads them.

## Existing focused test sources located

- `scripts/test_report_cache_identity.py` mutates included inputs, same-path executable bytes,
  target and proof-affecting mode; it also covers recipe changes, corrupt report payloads, pending
  entries, and cached-versus-fresh result agreement. `scripts/test_report_cache_executable_swap.py`
  and the dependency-mutation tests add real build-product replacement and include-resolution
  cases.
- `scripts/test_declaration_artifact_identity.py` covers stale source/dependency/build context,
  changed frontend identity, unsupported schemas, corruption, truncation, and deliberate digest
  path collisions. `scripts/test_declaration_artifact_concurrency.py` covers concurrent immutable
  publication.
- `scripts/test_p05_package_restart.py` starts a fresh replay process and checks stale source
  admission, forged success metadata, elevated trust, statement/fingerprint mismatch and
  truncation. `scripts/test_portable_replay.py` checks rejection of a package version it does not
  recognize.

These are locations and claimed test intents from source review only; this audit did not execute
them against the current executable.

## Missing R-009 policy and evidence

- The report/declaration caches have versioned identities, and stale results miss when the
  executable or manifest changes. No separate registry was found mapping a confirmed soundness
  incident and affected rule semantics to all affected product, report, package and artifact
  versions.
- The portable package names its wire format, not the checker build or rule-semantic version.
  Its safety relies on mandatory replay by the current executable. That is useful invalidation by
  rechecking, but it does not provide migration/refusal metadata or warn when an old package came
  from a known affected checker.
- `AUDIT.md` contains historical soundness and corruption narratives, but a complete incident
  inventory, exact affected-product classification, rule-to-artifact impact map, and tested
  old/new version policy remain to be built. The P-00 qualified-rewrite crash is still
  causally unresolved, so no affected version range can be assigned to that event yet.
- The tests cited above have not been run as a single R-009 gate on one immutable product; no
  migration test exists for a rule-semantics incident with persisted old and new packages.

R-009 is partial. Existing cache identities and mandatory package replay limit stale reuse, but
the incident registry, affected-version classification, semantic migration behavior, and full
downstream invalidation evidence remain open.
