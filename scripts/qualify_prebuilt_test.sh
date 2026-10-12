#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/compiler_snapshot.sh
source "$ROOT_DIR/scripts/compiler_snapshot.sh"
python3 "$ROOT_DIR/scripts/prebuilt_qualification.py" \
    --proof-root "$ROOT_DIR" \
    --snapshot-root "$SNAPSHOT_ROOT" \
    --compiler-snapshot "$SNAPSHOT_COMPILER" \
    --compiler-repository "${ELISA_COMPILER_SRC:-$ROOT_DIR/../Elisa-compiler}"
