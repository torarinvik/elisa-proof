# Ordinary enum equality admission — 2026-10-07

The engine's action-input and animation proofs exposed missing nominal enum
support in proposition formation and executable operator admission.

The kernel typing environment now registers every zero-payload enum variant
as a value member, retaining exact declaration identity and scope paths.
Executable equality witnesses are restricted to uniquely resolved ordinary
enums whose variants all have zero payload, with no enum hierarchy or source
Eq override. Override checks follow aliases. These witnesses admit Eq only;
enum operands receive no arithmetic scalar witness.

A checked, call-free enum comparison may receive a Boolean result witness at
the return boundary. This permits return identity without treating the enum
as an integer. A bool Eq override also prevents that witness. Existing source
admission, type formation and independent certificate replay still apply.

`scripts/test_plain_enum_propositions.py` passes five outcome regressions:

- `plain_enum_member_proposition`: return identity accepted with complete replay.
- `rejected_plain_enum_owner_proposition`: another enum's member refused.
- `rejected_plain_enum_overloaded_equality`: direct Eq override refused.
- `rejected_plain_enum_alias_equality`: alias Eq override refused.
- `rejected_plain_enum_comparison_claim`: a false Boolean claim refused.

The override cases assert zero semantic errors and an executable-operation
refusal, so unrelated syntax/type failures cannot satisfy them. The accepted
case requires status `proved`, no open obligations and no replay gaps. These
tests and the compiler-recipe regression are wired into the standard Python
stage of `scripts/test.sh`. Source-length and diff-whitespace checks pass.

Builds use frontend/product revision `96761822`, strict mode and `-O2`.
Build logs are retained in the engine's `build/validation/prover-enum-*.log`.
The focused nine-row engine rerun still fails all nine rows; this does not
close the engine proof gate. Action input has 31/74 proven obligations after
this change, versus 30/79 before enum registration; animation events have
45/58 versus 43/61. Obligation inventories differ because previously refused
expressions now enter analysis. Indexed fields, borrow tracking, loop/callee
summaries and replay gaps remain. The complete prover matrix has not been run
for this slice. Payload/hierarchy enum completeness is not established.
