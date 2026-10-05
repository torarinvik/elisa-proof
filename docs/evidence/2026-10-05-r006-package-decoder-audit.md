# R-006 package decoder audit (2026-10-05)

Audited `src/portable/package_reader.elisa`, `src/portable/package_checker.elisa`, the shared bounded file reader, and `scripts/test_portable_replay.py` on the current branch.

No narrow malformed-input fix was justified by this pass. Existing admission checks include exact object schemas (including duplicate-key rejection), canonical bounded numeric forms, fixed-format and trust-field checks, node/child/theorem/hypothesis/string/identity budgets, arena span and shape admission, cycle/forward-reference rejection, and truncation/empty-input refusal. The package file reader also caps input at 64 MiB before parsing. Focused replay cases exercise these behaviors, including bad integer spellings and oversized node/child/theorem/hypothesis inputs.

This is not completion of R-006. The plan's combined parser/checker fuzzing gate has not been run or established here. The regression suite also does not directly establish the malformed-Boolean payload and invalid-UTF-8 policies at the package boundary. The JSON parser implementation is outside this repository's package-reader source, so those cases need an explicit parser/checker test before claiming the gate. No code or test behavior was changed in this audit.
