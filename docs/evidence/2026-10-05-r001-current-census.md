# R-001 exact-current census — 2026-10-05

This six-input inventory was run serially with `scripts/p07_support_census.py` against one
manifest-bound strict O2 product. The census now has an optional report capture directory and
retains declaration/support inventory when a complete JSON report has replay gaps. The
field-equality timeout emitted no JSON. The historical crash's disappearance is recorded as a
current observation, not a fix or cause analysis.

The product was built with the pinned compiler and matching runtime object:

```sh
ELISA_COMPILER_BIN=/private/tmp/elisa-p06-compiler-pinned-20261005/bin/elisac-stage1 \
ELISA_COMPILER_SRC=/private/tmp/elisa-p06-compiler-pinned-20261005 \
ELISA_RUNTIME_OBJ=/private/tmp/elisa-p06-compiler-pinned-20261005/build/runtime/elisacore_runtime.o \
ELISA_OPT_LEVEL=O2 ELISA_PROOF_COMPILE_MODE=strict ELISA_PROOF_BUILD_JOBS=1 scripts/build.sh
```

## Product and inputs

| Identity | Value |
| --- | --- |
| Proof source tree | `9b9391db94fac6af9fbeb6473ccb07d72c1d10cba108b63a9fedabc6954032e2` |
| Proof binary SHA-256 | `188f979b973157c57ce7fad122ae5d0aaafd4bd820c5c994cdd33a32d60b72a1` |
| Build manifest SHA-256 | `614af499b48febb752716535be6cc429e835005462f85bd14587421e6ff1ad43` |
| Build mode / target | strict O2 / `arm64-apple-darwin27.0.0` |
| Stage1 revision / tree | `7b27fa312c5af923f044f6ee0e5e1de4f811f595` / `ab8926f6080a13d21b06606af251e6f0027c2db5` |
| Pinned Stage1 executable SHA-256 | `f77278c716dea7f3dba8f4fcbcf76ecc473426ab3f163c95fea4e358f6337653` |
| Runtime object SHA-256 | `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897` |

The exact inputs and census outcomes follow. “Unverified” and “unsupported” are the census
declaration and source-site counts; complete raw CLI JSON is in
`/private/tmp/elisa-r001-current-census/reports/` and is identified by its SHA-256 in the table.
Each census invocation checked that its input and product identities were unchanged before and
after the run. Paths under `examples/` and `src/` resolve from
`/private/tmp/elisa-plan-r001-current-census`; the lexer path resolves from the pinned compiler at
`/private/tmp/elisa-p06-compiler-pinned-20261005`; mocap paths resolve from
`/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/mocap-cleaner`.

| Input | Input SHA-256 | Bound (seconds / KiB) | Obligations / proven | Certificates / replayed / gaps | Seconds / peak RSS KiB | Unverified / unsupported | Complete report SHA-256 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `mocap-cleaner/src/physics/balance.elisa` | `4bfe5f9c36a615c4e1223554455be19b6060286b6916745242c11e641662228f` | 30 / 1,000,000 | 240 / 240 | 240 / 240 / 0 | 0.177 / 19,840 | 14 / 0 | `cd3595b33ec08a6be1e5ab277d4956248b61380aecaa9295a32a7d4328db8b1a` |
| `mocap-cleaner/src/tools/track.elisa` | `2723d053f74f17cf3776db4a5833f6f6439cb158b4bef58f0cd2e34f37e2aa22` | 30 / 1,500,000 | 943 / 837 | 926 / 837 / 89 | 4.562 / 482,640 | 65 / 10 | `a252dcf077815587082aebffeb4a51a2eaf32ef248bbaad2e4ea913fb42cea6b` |
| `examples/field_equality_runtime.elisa` | `2c4c5154c015cdc05f4168f15caf6f97304f8a2889474cbfba11db32aa2eabfa` | 120 / 2,500,000 | no report | no report | timeout 120.156 / 2,066,144 | — | no stdout; zero bytes |
| `examples/kernel_comparison_runtime.elisa` | `905a041e2d2a517662a9707b25198f28856c285e6c46be43eeb7c510d1f2bc0a` | 45 / 2,500,000 | 4,004 / 2,526 | 2,526 / 2,526 / 0 | 19.533 / 835,424 | 743 / 1,249 | `abe2aa239b79c8c018c0a024ac5657253f5bc1e35e487108d2b2175bf2f8daad` |
| `src/proof/kernel_core.elisa` | `6e78ff9e07900b2d97da8044dc1cae855f84dd30fb8ef5348c9868b72335e590` | 30 / 1,000,000 | 37 / 37 | 37 / 37 / 0 | 0.074 / 15,776 | 43 / 0 | `fd2716551b26ff3ba419658352d156639d1802991e2372cbee2904a6d423393b` |
| pinned compiler `src/lexer/lexer.elisa` | `790f7e89330800c19c85b4a9e6e23259877cf5bc561a9f7700dedb451a6456e9` | 60 / 1,500,000 | 326 / 110 | 110 / 110 / 0 | 0.372 / 60,944 | 154 / 173 | `a276dc73c479068ec58a0d1de091c6647df55312e166094936df1da327f54239` |

Each row used this command shape, with its listed input, bound, and output filename; runs were
serial:

```sh
ELISA_PROOF_BIN="$PWD/build/elisa-proof" python3 scripts/p07_support_census.py \
  --timeout-seconds SECONDS --rss-limit-kib KIB \
  --reports-dir /private/tmp/elisa-r001-current-census/reports \
  --out /private/tmp/elisa-r001-current-census/NAME.json INPUT
```

Field equality's recorded outcome is a timeout, not proof failure: the process emitted no bytes.
An earlier invocation of the same product, input and configured bounds hit the 2,500,000 KiB RSS
limit at 25.120 seconds with sampled RSS 2,543,136 KiB. The later bounded repeat ran the full 120
seconds and peaked at 2,066,144 KiB. Both outcomes are preserved because the resource behavior
varied between attempts.

## Changed versus the prior six-input census

The prior census used proof source `1f273bf1…`, binary `ba640c47…`, and the same Stage1 revision.
Five input byte hashes are unchanged: balance, track, field equality, kernel comparison, and
lexer. `kernel_core.elisa` changed from `a2ca3f4d…` to `6e78ff9e…`. The current proof source and
binary are different, so the results below describe this exact product only.

| Input | Prior result | Current result |
| --- | --- | --- |
| balance | 240/240, full replay | 240/240, full replay |
| track | 943 obligations, 926 proven, 928 certs with 2 gaps | 943 obligations, 837 proven, 926 certs with 89 gaps |
| field equality | 120 s timeout, about 601,536 KiB | 120.156 s timeout at 2,066,144 KiB; an earlier same-bound run hit RSS limit |
| kernel comparison | 3,800 obligations, 2,544 proven/replayed; 1,109 unsupported sites, 691 unverified declarations | 4,004 obligations, 2,526 proven/replayed; 1,249 unsupported sites, 743 unverified declarations |
| kernel core | 37/37, full replay (prior input hash `a2ca3f4d…`) | 37/37, full replay (input changed) |
| lexer | 326 obligations, 110 proven/replayed; 173 unsupported sites, 154 unverified declarations | same counts; exact input hash unchanged |

The current kernel-comparison report's largest unsupported site groups are
`function-summary-unverified` (605), `contract-proposition-type` (274), and
`control-flow-analysis-budget` (220). Lexer groups are `contract-expression-unsupported` (58),
`contract-proposition-type` (56), and `borrow-call-opaque` (27). These remain coverage limits,
despite complete replay of every emitted certificate in both reports. Track also has 10
`function-summary-unverified` unsupported sites. Its 65 unverified declarations and 10 unsupported
sites were extracted from the complete captured JSON; the census marks track incomplete because
of replay gaps but still includes this inventory in the rankings.

## Focused current failure controls

- The current six-input runs produced complete JSON for both historical P-00 crash workloads
  (`kernel_comparison_runtime` and `track`), with no SIGSEGV. These focused commands passed:
  `ELISA_PROOF_BIN=build/elisa-proof python3 scripts/test_qualified_constants.py`,
  `ELISA_PROOF_BIN=build/elisa-proof python3 scripts/test_compact_mutating_call_summary.py`, and
  `ELISA_PROOF_BIN=build/elisa-proof python3 scripts/test_long_difference_chain.py`. Qualified
  constants include the minimized qualified-return case (1/1 replayed) and wrong-value/module/
  shadowing controls. The summary control covers composed mutating calls; the difference-chain
  control covers its 32-name boundary and 33-name refusal. This does not explain the earlier
  invalid write or establish that it was fixed in the unavailable historical product.
- The simple conditional-return regression now proves 2/2 with 2/2 replayed. The `Slide.inner`
  minimal fixture remains refused with two replay gaps (6 certificates, 4 replayed); the wrong
  guard remains failed with zero replay gaps. The current full `track` report has 89 gaps overall.
  Its two `Slide.inner` roots are certificate IDs 510 and 511 at `slide.elisa:710`; both remain
  unreplayed. Full fixture report hashes are `468caf74…` (simple), `8004345f…` (`Slide.inner`),
  and `82ba2f55…` (wrong guard), in the same raw report directory.

## Gate and remaining limits

R-001's six-input gate is met: this note binds all six inputs to one current manifest-bound
product; each produced a complete report or an explicit timeout record; complete reports are
retained by digest; and the historical findings are labeled by exact-current reproduction. This
does not close P-00's cause analysis, P-07's support bottlenecks, the 89 track replay gaps, or the
field-equality timeout. The census covers the six requested inputs and the focused controls above;
it is not a full proof suite or Linux qualification.
