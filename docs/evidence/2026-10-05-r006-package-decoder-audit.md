# R-006 package decoder audit (2026-10-05)

Audited `src/portable/package_reader.elisa`, `src/portable/package_checker.elisa`, the shared bounded file reader, and `scripts/test_portable_replay.py` on the current branch.

The initial pass found no narrow fix. A follow-up byte-level probe then demonstrated that malformed UTF-8 in a theorem's presentation name was accepted and replayed. Commit `df652ae0` now validates the complete bounded input as UTF-8 before JSON parsing and returns the structured `malformed/utf8` verdict on invalid sequences. String fields also validate decoded UTF-8. This rejects invalid bytes even in presentation data that the checker otherwise ignores.

The portable replay regression now sends six malformed raw UTF-8 encodings and six non-Boolean payload types for the `authenticated` field. Every case produces a bounded structured malformed result; malformed Boolean values return `source-schema`. Strict pinned Stage1 O2 build passed, as did `scripts/test_portable_replay.py` (16 positive packages plus its refusal corpus). Replay binary SHA-256: `6b897fd8a11ef7f828fb7236d0662e6d6541eeca6ad0ba7f9f873caa5de77624`.

This is not completion of R-006. The plan's combined parser/checker fuzzing gate has not been run or established here; the deterministic mutations are a focused regression corpus only.
