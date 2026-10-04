# shellcheck shell=bash
# Sourced by build.sh, test.sh and dogfood.sh: the flags that dead-strip a linked Elisa product.
# Apple ld spells it -dead_strip. GNU ld spells it --gc-sections, needs -no-pie because the
# compiler's objects are not position independent, and needs libm, which Apple's libSystem
# carries implicitly; --no-as-needed keeps libm even though it precedes the objects.
if [[ "$(uname -s)" == "Darwin" ]]; then
    ELISA_DEAD_STRIP_LINK=(-Wl,-dead_strip)
else
    ELISA_DEAD_STRIP_LINK=(-no-pie -Wl,--gc-sections -Wl,--no-as-needed -lm)
fi

# Honor the same explicit LLVM tools as the compiler wrapper. Linux provisioned
# toolchains need not be installed globally or added to the login shell's PATH.
elisa_resolve_clang() {
    local selected="${ELISA_CLANG:-}" config="${LLVM_CONFIG:-}"
    if [[ -z "$selected" && -n "${ELISA_LLVM_BIN_DIR:-}" ]]; then
        selected="$ELISA_LLVM_BIN_DIR/clang"
    fi
    if [[ -z "$selected" && -n "$config" ]]; then
        if [[ "$config" != */* ]]; then config="$(command -v "$config" || true)"; fi
        if [[ -z "$config" || ! -x "$config" ]]; then
            printf 'LLVM_CONFIG is not executable: %s\n' "${LLVM_CONFIG}" >&2
            return 2
        fi
        selected="$(dirname -- "$config")/clang"
    fi
    if [[ -z "$selected" ]]; then
        selected="$(command -v clang || true)"
    elif [[ "$selected" != */* ]]; then
        selected="$(command -v "$selected" || true)"
    fi
    if [[ -z "$selected" || ! -f "$selected" || ! -x "$selected" ]]; then
        printf 'clang is required; set ELISA_CLANG or LLVM_CONFIG to an executable toolchain\n' >&2
        return 2
    fi
    printf '%s\n' "$selected"
}

elisa_clang() {
    local tool
    tool="$(elisa_resolve_clang)" || return $?
    "$tool" "$@"
}

# Link with clang; on GNU ld, retry once with aborting stubs when the only undefined symbols are
# the runtime's optional native-callback and varargs entry points. Apple's -dead_strip removes
# those unreachable references; --gc-sections does not, because the runtime object keeps them in
# shared sections. Any other undefined symbol still fails the link, with the linker's diagnostics.
# Usage: elisa_link_native STUB_DIR clang-arguments...
elisa_link_native() {
    local stub_dir="$1" log stub undefined symbol index=0
    shift
    log="$stub_dir/link.$$.log"
    if elisa_clang "$@" 2>"$log"; then
        rm -f "$log"
        return 0
    fi
    if [[ "$(uname -s)" == "Darwin" ]]; then
        cat "$log" >&2
        return 1
    fi
    undefined="$(grep -o "undefined reference to \`[^']*'" "$log" | sed "s/.*\`//;s/'//" | sort -u || true)"
    if [[ -z "$undefined" ]]; then
        cat "$log" >&2
        return 1
    fi
    stub="$stub_dir/unreachable-stubs.$$.c"
    printf '#include <stdlib.h>\n' >"$stub"
    for symbol in $undefined; do
        case "$symbol" in
            elisa_native_callback_*|va_start|va_end|va_copy) ;;
            *) cat "$log" >&2; return 1 ;;
        esac
        index=$((index + 1))
        printf 'void elisa_unreachable_%d(void) __asm__("%s");\nvoid elisa_unreachable_%d(void) { abort(); }\n' "$index" "$symbol" "$index" >>"$stub"
    done
    rm -f "$log"
    elisa_clang "$@" "$stub"
}
