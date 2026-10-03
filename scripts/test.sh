#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/link_flags.sh
source "$ROOT_DIR/scripts/link_flags.sh"
# The matrix runs as ordered parts sourced into this shell, so state (set -e/+e, traps,
# variables such as SELF_HOST_COMPILER and the helper run_json_report) carries across them.
# Each part stays under the 600-line source boundary that check_source_length.py enforces.
for test_part in "$ROOT_DIR"/scripts/test.d/[0-9][0-9]-*.sh; do
    # shellcheck source=/dev/null
    source "$test_part"
done
