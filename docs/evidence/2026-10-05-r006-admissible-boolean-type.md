# R-006 `source.admissible` boolean type mutation — 2026-10-05

Added a single-field package mutation to `scripts/tests/portable_replay_package_validation.py`:
the otherwise valid theorem package changes `source.admissible` from JSON `true` to integer `0`.
The focused assertion requires a structured `malformed` / `source-schema` refusal with zero
theorems and zero replayed or not-replayed entries.

Validation attempted with `python3 scripts/test_portable_replay.py`. It could not start because
this worktree has no published product generation at `build/elisa-proof-generations/CURRENT`;
the runner's paired proof and replay binaries are therefore unavailable here. `git diff --check`
passed. This records one deterministic schema mutation only and does not establish R-006 completion.
