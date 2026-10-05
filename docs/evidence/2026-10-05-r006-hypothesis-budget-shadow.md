# R-006 hypothesis-count cap is shadowed by statement string limit (2026-10-05)

## Finding

`ProofPackageLimit::HYPOTHESES` is 4,096, but the theorem's canonical `statement` is also read
through `proof_package_string_field`, whose `STRING_BYTES` limit is 65,536. The shortest valid
proposition node identity is `(bool::1:"":"")` (15 bytes). Each hypothesis adds `F` plus that
identity; the sequent prefix is `elisa-proof-goal-v1:` and the conclusion adds `G` plus its
identity. A self-assumption with 4,096 copies therefore needs a 65,572-byte statement. It is
refused as `malformed/theorem-schema` before `package_checker.elisa` reaches the hypothesis-count
check. A canonical 4,097-hypothesis statement would be 65,588 bytes and is blocked the same way.

The new bounded test keeps a 4,096-item exact-count package with the complete canonical statement
and asserts this string-cap refusal. Its 4,097 control preserves the original short statement so
the count check is reached; it returns `over-budget/hypothesis-budget`, with zero replay and one
explicit theorem-level refusal row. This proves the count check's ordering, not a valid 4,096
positive boundary or a canonical 4,097 refusal. There is no valid compact proposition construction
that avoids the minimum Boolean identity: numeric leaves are shorter but the independent kernel
rejects them as propositions.

## Runtime evidence and identities

Ran the registered `scripts/test_portable_replay.py` entry from source worktree commit
`948220c610f98ac6305b9352876fe7df35455679` with the suite's exact/over controls in
`scripts/tests/portable_replay_structure_fuzz.py` (SHA-256
`e6b9781ccd208d1d72ec672ce8be932a4f06fa85f1198b036bdfb7c50b8965d4`). The worktree is branch
`codex/r006-hypothesis-budget-20261005` at
`/private/tmp/elisa-proof-r006-hypothesis-budget`.

The explicit matched product generation was `79948cae3ccc4190aeebd778041c4b0b`:

- `elisa-proof` SHA-256 `93015d90f2e8b0dadf7fe5fa92a0dde013b525244a50441ec827fc0d564c3365`
- `elisa-proof-replay` SHA-256 `71e313a6c87c339ee89e1d588c639edfe90e581f408c78583792ccb27e8fc4ea`
- Both strict O2 manifests name proof source commit `414e569369fd8a3cc8b0fc6afba03475291e23a4`,
  clean tree digest `558d7e9f7e09be3d3ab76bd05b78babd2b666e808223d38e4144294a26e04a9e`, frontend
  revision `7b27fa312c5af923f044f6ee0e5e1de4f811f595`, and target `arm64-apple-darwin27.0.0`.

Command (from the isolated worktree):

```sh
ELISA_PROOF_BIN='/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/elisa-proof/build/elisa-proof-generations/79948cae3ccc4190aeebd778041c4b0b/elisa-proof' \
ELISA_PROOF_REPLAY_BIN='/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/elisa-proof/build/elisa-proof-generations/79948cae3ccc4190aeebd778041c4b0b/elisa-proof-replay' \
python3 scripts/test_portable_replay.py
```

The full suite passed: 16 positive packages replayed, the deterministic structure-aware cases and
new hypothesis-cap controls passed, and 512 raw-byte mutations plus 16 positive encodings were
checked. Three raw-byte mutations remained valid. There were no crashes or partial theorem replays.
The new controls ran each child with limits of 4 seconds CPU, 5 seconds wall time, 512 MiB RSS,
and 4 MiB stdout/stderr capture. The structure-aware matrix peaked at 0.050 seconds wall,
0.045 seconds CPU, and 26,525,696 bytes RSS. The direct count check returns one `over-budget` theorem row;
the summary is `{theorems: 1, replayed: 0, not_replayed: 1}` rather than an empty theorem array.

This product pair is from source commit `414e5693`, not current worktree HEAD `948220c6`. No
production decoder change was made. If the 4,096 exact positive and canonical 4,097 over-budget
cases are required, the narrowest justified cap change is raising `STRING_BYTES` from 65,536 to
at least 65,588 (+52 bytes), which would allow the canonical 4,097 string to reach the existing
hypothesis gate. This also raises the general per-string/copy-pool allowance by 52 bytes; it does
not materially change the package-wide 64 MiB identity budget. R-006 remains open pending a
reviewed policy choice or a revised test contract.
