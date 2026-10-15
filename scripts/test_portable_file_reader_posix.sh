#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLANG_TOOL="${CLANG:-clang}"
scratch="$(mktemp -d "${TMPDIR:-/tmp}/elisa-portable-file-test.XXXXXX")"
trap 'rm -rf "$scratch"' EXIT
"$CLANG_TOOL" -std=c11 -O2 -o "$scratch/portable-file-test" \
    "$ROOT_DIR/src/app/portable_file_posix.c" \
    "$ROOT_DIR/scripts/tests/portable_file_posix_test.c"
"$scratch/portable-file-test"
python3 "$ROOT_DIR/scripts/test_portable_file_reader_contract.py"
printf 'portable file reader: regular files accepted, FIFOs rejected without blocking, mutations and path retargeting detected\n'
