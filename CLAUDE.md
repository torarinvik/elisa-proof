# elisa-proof working rules

- Every source file stays at or under 600 lines: `src/**/*.elisa`, `examples/**/*.elisa`,
  `scripts/**/*.sh`, `scripts/**/*.py` and `test/**/*.py`. `scripts/check_source_length.py`
  enforces it and runs first in `scripts/test.sh`.
- When a file nears the limit, split it by responsibility into a sibling module (for Elisa,
  another file under the same `src/proof/...` directory extending the same module) rather than
  compressing code or comments.
- `scripts/test.sh` and `scripts/dogfood.sh` are drivers that source ordered parts from
  `scripts/test.d/` and `scripts/dogfood.d/`. Add new checks to the part for that theme; when a
  part nears 600 lines, start a new numbered part. Parts share one shell, so a later part may
  use variables and functions from an earlier one, never the reverse.
