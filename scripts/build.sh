#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPILER="${ELISA_COMPILER_BIN:-}"

if [[ -z "$COMPILER" ]]; then
    COMPILER="$(command -v elisac 2>/dev/null || true)"
fi

if [[ -z "$COMPILER" || ! -x "$COMPILER" ]]; then
    printf 'Set ELISA_COMPILER_BIN to the self-hosting elisac executable (or put elisac on PATH).\n' >&2
    exit 2
fi

if ! command -v clang >/dev/null 2>&1; then
    printf 'clang is required to link the generated Elisa object.\n' >&2
    exit 2
fi

mkdir -p "$ROOT_DIR/build"
cd "$ROOT_DIR"
"$COMPILER" -emit obj -O0 -o "build/elisa-proof-stage.o" "src/main.elisa"
clang -Wl,-dead_strip -o "build/elisa-proof" "build/elisa-proof-stage.o"
