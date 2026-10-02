#!/usr/bin/env bash
set -euo pipefail
ROW_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROW_COMPILER="${ELISA_COMPILER_BIN:-$ROW_ROOT/build/elisac-stage0-a891}"
source "$ROW_ROOT/scripts/compiler_provenance.sh"
elisa_compiler_is_stage0 "$ROW_COMPILER" || exit 2
elisa_verify_stage0_provenance "$ROW_COMPILER" "$ROW_ROOT"
ROW_REV="$(tr -d '[:space:]' < "$ROW_ROOT/ELISA_COMPILER_REV")"
[[ "$(<"$ROW_ROOT/build/snapshot/Elisa-compiler/.rev")" == "$ROW_REV"* ]] || exit 2
ROW_SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/elisa-extern-row.XXXXXX")"
cleanup_rows() {
    rm -f -- "$ROW_SCRATCH/runtime.o" "$ROW_SCRATCH/row.o" "$ROW_SCRATCH/probe"
    rmdir -- "$ROW_SCRATCH"
}
trap cleanup_rows EXIT
for ROW_FIXTURE in extern_effect_rows_runtime extern_effect_rows_parser_runtime source_call_coverage_parser_runtime effect_source_validation_parser_runtime extern_return_text_runtime numeric_literal_sort_runtime kernel_typed_literals_runtime; do
    "$ROW_COMPILER" -emit obj -O0 -o "$ROW_SCRATCH/row.o" "$ROW_ROOT/examples/$ROW_FIXTURE.elisa"
    "${CLANG:-clang}" -Wl,-dead_strip -o "$ROW_SCRATCH/probe" "$ROW_SCRATCH/row.o" "$ROW_ROOT/build/profile_hooks.o"
    "$ROW_SCRATCH/probe"
done
printf 'strict native extern-row, declaration identity, direct call coverage and source-bound effect replay controls pass; reduced return-text/literal-sort metadata controls pass, new parser correspondence and typed-literal/native-resource admission remain pending\n'
