# R-016 compact report route evidence

Date: 2026-10-05

## Product identity

- Source repository: `elisa-proof`
- Source base: `da2b0706675c5cade1306694183517a635f7d272`
- Frontend source revision: `7b27fa312c5af923f044f6ee0e5e1de4f811f595`
- Frontend source tree: `ab8926f6080a13d21b06606af251e6f0027c2db5`
- Compiler source revision: `e4a16fd24dacb2db54b7cc3aff2d19312ff2edf7`
- Compiler product SHA-256: `7bcb8590304617b61d1462f6b40c0bff006e3fbe537489d1ce867766e918bd39`
- Runtime object SHA-256: `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`
- Build: strict stage1, `-O2`, `arm64-apple-darwin27.0.0`
- `elisa-proof` binary SHA-256: `1d3f7c49f41e2dc65b495a78296d7222fb10fb4122b489676a3470cf3ec788e7`

## Commands

```sh
ELISA_OPT_LEVEL=O2 ELISA_PROOF_COMPILE_MODE=strict ./scripts/build.sh
python3 scripts/test_report_summary.py
```

The strict O2 build completed. The focused comparison printed `compact/full report conclusions and authoritative counts agree` and exited 0.

## Comparisons

`--json` is the full route; `--summary-json` is the compact route. Source objects (including source byte count and fingerprint), status, verification state, engine state, trusted assumptions, obligation counts, replay-confirmed proven and unproven counts, finding counts by status, diagnostic counts, trusted boundary fact count, and replayed certificate count were compared.

| Exact source and identity (`fnv1a32`, full / summary) | Result | Full JSON bytes | Summary JSON bytes | Obligations | Proven/unproven (full / summary) | Replayed certificates | Trusted boundary facts |
|---|---|---:|---:|---:|---:|---:|---:|
| `examples/loop_invariants_compile.elisa` (1514 bytes, `1597998471` / `1597998471`) | `proved` / `proved` | 115557 | 593 | 23 / 23 | 23/0 / 23/0 | 23 / 23 | 53 / 53 |
| `examples/rejected.elisa` (179 bytes, `3660784360` / `3660784360`) | `failed` / `failed` | 10750 | 589 | 3 / 3 | 1/2 / 1/2 | 1 / 1 | 3 / 3 |

Both summary outputs explicitly mark details omitted and direct users to `elisa-proof --json <file.elisa>`. These measurements establish smaller serialized output for these two fixtures only. They do not measure retained report memory or establish a bound for arbitrary large refusal reports. The report and complete evidence are still materialized in memory before either serializer runs.
