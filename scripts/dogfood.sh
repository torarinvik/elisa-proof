#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# The gate runs as ordered parts sourced into this shell, so set -e/+e state, traps, functions
# and variables carry across them. Each part stays under the 600-line source boundary.
for dogfood_part in "$ROOT_DIR"/scripts/dogfood.d/[0-9][0-9]-*.sh; do
    # shellcheck source=/dev/null
    source "$dogfood_part"
done
