# R-006 decoder boundary inventory — 2026-10-05

This is a source audit of the portable replay package path at proof revision
`40b8018e2fafa308f4e6a74b9a003308100b3c5d`. It records the controls visible in that path and
the evidence still needed. It is not a fuzzing result or a complete inventory of every decoder
named by R-006; the plan item remains open.

## Controls found in the portable replay path

| Boundary | Current control | Source |
| --- | --- | --- |
| Package file input | `proof_read_file_checked` reads in 64 KiB chunks and caps a file at 67,108,864 bytes before JSON parsing. An over-limit/read failure becomes the replay CLI's structured `unreadable` response (exit 2). | `src/app/portable_io.elisa`, `src/replay_main.elisa` |
| JSON object schema | `proof_package_has_exactly` checks object member count and presence of every distinct schema key. The JSON boundary exposes member count including repeated keys, so duplicate and extra keys fail closed. | `src/app/json_boundary.elisa`, `src/portable/package_reader.elisa` |
| Version/trust header | Only `elisa-proof-package-v1` and the fixed source/trust shapes are accepted; a package cannot claim authenticated source or stronger hypothesis/correspondence/fingerprint trust. | `proof_package_read_header` in `src/portable/package_reader.elisa` |
| Numeric indexes | Indexes must be JSON numbers, nonnegative, exactly representable integers below 2^53. Decimal node values use canonical strings parsed into the full signed i64 range. | `proof_package_index`, `proof_package_decimal_i64` in `src/portable/package_reader.elisa` |
| Arena allocation counts | Node and child array counts are checked against 1,000,000 and 4,000,000 before their elements are copied. Node strings are copied into a package-wide 65,536-byte pool with a remaining-capacity check before each append. | `proof_package_read_kernel`, `proof_package_read_node`; budgets in `src/proof/kernel_core.elisa` and `src/portable/package_reader.elisa` |
| Theorem work | Theorem count is capped at 65,536; each theorem's hypothesis count is capped at 4,096; canonical identity is capped at 16 MiB per theorem and 64 MiB cumulatively. | `proof_package_replay`, `proof_package_check_theorem`; `ProofPackageLimit` and `PROOF_RUNTIME_IDENTITY_BYTE_LIMIT` |
| Node tags, arities and graph | Arena shape dispatch rejects unrecognized kinds and malformed field combinations. Whole-arena validation checks every node, child ranges, backward references/acyclicity and depth before theorem replay. | `src/proof/kernel_replay/arena_shapes.elisa`, `src/proof/kernel_replay/quantifiers_and_arena.elisa`, `proof_kernel_replay_arena_all_report` |
| Theorem roots and rules | Hypothesis/conclusion indexes must point into the admitted arena; rule names have a fixed dispatch list; statements and fingerprints are recomputed before independent replay. | `src/portable/package_checker.elisa` |

## Existing focused evidence located

`scripts/test_portable_replay.py` contains mutations for duplicate object keys, extra fields,
wrong package versions, malformed decimal spellings and indexes, unknown node kinds, invalid
child spans, cycles, forward references, exponential DAG identity growth, node/child/hypothesis/
theorem count limits, truncation, empty input, six invalid raw UTF-8 encodings, and six invalid
JSON types for the `source.authenticated` Boolean field. It also requires positive package replay
and consistent forged statements before checking kernel refusals.

`scripts/tests/test_portable_package_string_budget.py` covers an under-budget node string and a
pair of individually valid strings whose aggregate exceeds the copied-string budget.

This source audit did not execute those tests or rebuild a product. The tests' source locations
show intended coverage but do not establish behavior for the current binary.

A separate isolated Luna review initially found no narrow fix. Its follow-up raw-byte probe
showed that malformed UTF-8 in a theorem presentation label could be replayed. Commit `de4bc101`
now validates the complete bounded input as UTF-8 before JSON parsing and validates decoded
strings read from the package; invalid input returns structured `malformed/utf8`. The six raw-byte
and six Boolean-type regressions passed in the agent's strict pinned O2 build and
`scripts/test_portable_replay.py`. That replay binary's SHA-256 was
`6b897fd8a11ef7f828fb7236d0662e6d6541eeca6ad0ba7f9f873caa5de77624`; see the concise cross-check
`docs/evidence/2026-10-05-r006-package-decoder-audit.md` and commits `df652ae0`, `58d07b65`.

## R-006 work still required

- The plan's full decoder inventory spans `src/portable/`, `src/proof/kernel_replay/` and
  admission. This note follows only the portable package path; it does not inventory declaration
  artifacts, caches, source admission payloads, every textual marker, or all integer IDs.
- No parser-plus-checker fuzz harness or retained minimized fuzz failure was located in the
  focused portable tests. Escaped unpaired-surrogate policy, parser nesting/resource limits, and
  malformed Boolean node payloads still need explicit end-to-end cases; the added UTF-8 tests
  cover raw input bytes and the header Boolean type only.
- Existing visible budget mutations cover selected over-limit values. A systematic below/at/above
  boundary matrix for every count, index range, typed-literal tag and theorem label is not
  established here.
- `goal_id` and `line` are parsed as bounded indexes and echoed as presentation labels, but the
  checker does not establish uniqueness. Their consumer-facing identity semantics need to be
  documented or tested before treating duplicate labels as harmless.
- The file cap bounds input bytes before parsing, but this audit contains no peak-memory evidence
  for parser/DOM expansion near that cap and no test that exercises the oversized-file response.

R-006 remains open until the complete inventory, parser/checker fuzz coverage, boundary matrix and
structured resource-failure behavior are evidenced against one immutable product.
