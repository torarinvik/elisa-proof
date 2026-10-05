# R-011 branch-join workload (2026-10-05)

The P-01 sentinel corpus now pins the existing branch-join acceptance/refusal pair in
`scripts/p01_sentinels.json`. This fills a semantic-shape gap in the small baseline corpus: the
positive file checks a branch that preserves an invariant, a branch that assigns a bounded value,
conditional indexed access, and a joined value; the negative file checks a too-wide replacement,
an invalid claim that the old value is always kept, and a stale fact after rebinding.

| Fixture | Bytes | SHA-256 | CLI status/exit | Obligations | Proven / unproven / failed | Trust assumptions / boundary facts | Proof certificates | Replay certificates / replayed / gaps |
| --- | ---: | --- | --- | ---: | --- | --- | ---: | --- |
| `branch_join` | 1,135 | `bc7bcbfa81ef187405e5e0ac3b3348d800b4ef4787848bad959760eb03eb190f` | `proved` / 0 | 12 (IDs 0–11) | 12 / 0 / 0 | 0 / 68 | 12 | 12 / 12 / 0 |
| `rejected_branch_join` | 1,047 | `42ee1d1323fc8beefe6b691bc231f2a566c56a66db023399c88ee9474680705f` | `failed` / 1 | 6 (IDs 0–5) | 3 / 3 / 3 | 0 / 42 | 3 | 3 / 3 / 0 |

The manifest also pins each obligation's ID, function, source line, rule and result. Both fixtures
share the `standard-bounded` budget classification: 20 seconds, 1,500,000 KiB RSS, and 128 MiB
captured output. The P-01 runner checks the pinned identities and expected statuses, plus the
obligation IDs/details, trust totals, proof totals and replay totals for this pair.

## Outcome-validation product identity

The CLI outcomes were checked against the explicit installed proof/replay generation
`bde26d342f264036a8bcfa58b5ba63c8`. The proof and replay manifests each had a valid SHA-256
sidecar and matching executable digest. Their pair generation, proof source, frontend, compiler,
runtime, target, optimization, compile mode and compiler flags matched. Binary SHA-256 values were
`0d5846988abb6859c15b4ab55b08ce46b837726d75a53f406a8112a86d1a3f91` (proof) and
`154cd6d58d87a1819b926eacd7d28522d4ac4d7ed4a6e03547ad523076826cc1` (replay).

This is not a build of this branch's clean `c21b9785` source. The proof manifest names source head
`045dae8d3589c9be3089d1d7d7b53d860cf0b7b9`, marks it dirty, and records source-tree SHA-256
`45ae7d36a37be910a17e92b977d02846d7b92a0b46eddbcbc7ce6e9aa04037f6`. These identities are
reported to bound the fixture-outcome evidence; no current-clean-source or performance claim is
made. The focused test validates the manifest and runner contract independently.

## Runner integration smoke

A one-round, no-warm-up P-01 runner smoke using the same installed proof binary exercised all
eleven manifest fixtures and wrote `/tmp/p011-branch-join-p01-smoke.json`. The new pair matched
its pinned statuses, obligation profiles, trust counts and replay counts in every scenario. The
overall run was incomplete because the pre-existing `qualified_constants` fixture had three replay
gaps in cold, warm and comment-edit invocations. That separate fixture issue is not evidence about
the branch-join pair; the smoke is not a seven-round performance baseline.
