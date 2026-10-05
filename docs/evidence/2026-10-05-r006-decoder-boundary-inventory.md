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

After integration, an isolated detached worktree at root commit
`e9d27ef62933944a08f5901f0d5524dfce1a5315` passed the strict pinned Stage1 O2 build. Its replay
binary SHA-256 was `d77669e81223424b16496c689e486a2ed2f0fbb3dbf9084b6c807bde4444e552`.
`scripts/test_portable_replay.py`, `scripts/tests/test_portable_package_string_budget.py`, and
`scripts/test_p05_package_restart.py` passed against those products. This updates product-level
evidence for the focused regression; the deterministic suite remains short of the plan's fuzzing
and exhaustive decoder-boundary gates.

## R-006 work still required

- The plan's full decoder inventory spans `src/portable/`, `src/proof/kernel_replay/` and
  admission. This note follows only the portable package path; it does not inventory declaration
  artifacts, caches, source admission payloads, every textual marker, or all integer IDs.
- No parser-plus-checker fuzz harness or retained minimized fuzz failure was located in the
  focused portable tests. Parser nesting/resource limits remain untested. End-to-end cases for
  escaped surrogate handling and malformed Boolean node payloads are recorded below; the earlier
  UTF-8 cases cover raw input bytes and the header Boolean type.
- Existing visible budget mutations cover selected over-limit values. A systematic below/at/above
  boundary matrix for every count, index range, typed-literal tag and theorem label is not
  established here.
- A focused Boolean kernel-payload regression was added to
  `scripts/tests/portable_replay_package_validation.py`. Five non-string JSON payloads (`true`,
  numeric `1`, `null`, array and object) return structured `malformed/node-schema` before arena
  admission. Canonical decimal strings `-1`, `2` and `9223372036854775807` pass package decoding
  and return structured `malformed/arena-inadmissible`; the kernel's Boolean scalar shape requires
  value 0 or 1 (`proof_kernel_replay_arena_bool_scalar_shape`). The malformed nodes are reachable
  from a theorem with a recomputed statement and fingerprint, so the result exercises package
  parsing, arena admission and theorem checking as one path. All 16 positive packages and the
  complete portable replay refusal corpus passed against strict pinned O2 proof revision
  `15560c60aab2540b8fd18137c8d2fd1ed2282e1e`. Replay product SHA-256:
  `6664442a5e7de99cd99763b0c1fa2c630c13c69d5215bc0908c485f1aa7e6a84`; proof product SHA-256:
  `54824e53bab5aa7f6c031f3db527dedf1515b44d594f0624cf44e78c65f6bbcb`. Pinned Stage1 SHA-256:
  `f77278c716dea7f3dba8f4fcbcf76ecc473426ab3f163c95fea4e358f6337653`, runtime SHA-256:
  `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`, target
  `arm64-apple-darwin27.0.0`. These probes found no malformed Boolean payload accepted by this
  product; they do not establish parser/checker fuzz coverage or the remaining decoder inventory.
- Escaped UTF-16 handling now has an explicit package policy regression: a valid high/low pair
  (`\\ud83d\\ude00`) in `source.path` is accepted and the package replays; isolated high and low
  surrogates, high-surrogate followed by ordinary text or another high surrogate, repeated low
  surrogates, and low-then-high ordering all fail closed as `malformed/json`. The escaped cases
  are sent as ASCII JSON bytes, so they exercise JSON escape decoding rather than invalid raw
  UTF-8. These results were checked with the strict pinned O2 replay product from source revision
  `15560c60aab2540b8fd18137c8d2fd1ed2282e1e`, SHA-256
  `6664442a5e7de99cd99763b0c1fa2c630c13c69d5215bc0908c485f1aa7e6a84` (Stage1
  `f77278c716dea7f3dba8f4fcbcf76ecc473426ab3f163c95fea4e358f6337653`, runtime
  `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`, target
  `arm64-apple-darwin27.0.0`). The package reader's decoded-string UTF-8 check remains an
  additional boundary; this policy evidence does not establish parser/checker fuzz coverage.
- `goal_id` and `line` are parsed as bounded indexes and echoed as presentation labels, but the
  checker does not establish uniqueness. Their consumer-facing identity semantics need to be
  documented or tested before treating duplicate labels as harmless.
- The file cap bounds input bytes before parsing, but this audit contains no peak-memory evidence
  for parser/DOM expansion near that cap and no test that exercises the oversized-file response.

R-006 remains open until the complete inventory, parser/checker fuzz coverage, boundary matrix and
structured resource-failure behavior are evidenced against one immutable product.
