#!/usr/bin/env bash
# Bootstrap the pinned Elisa toolchain on a Linux x86-64 host (for example a cloud container)
# and print the environment that scripts/build.sh, test.sh and dogfood.sh need.
#
#   eval "$(scripts/linux_toolchain.sh)"     # builds once into $ELISA_TOOLCHAIN_DIR, then reuses it
#
# Steps, each skipped when its output already exists:
#   1. stage0: Elisa-core at ELISA_STAGE0_REV, `go build` against ELISA_LLVM_DIR: Debian's shared
#      llvm-20-dev by default, or a static release tree such as LLVM-23.1.2-Linux-X64 from the
#      llvm-project GitHub releases (ELISA_LLVM_DIR=/opt/llvm-23), which ships no libLLVM.so.
#   2. stage1: Elisa-compiler at ELISA_COMPILER_REV compiled by stage0. The upstream seed script
#      links with Apple-only flags and at -O3, so the object is compiled at -O0 here and linked
#      with GNU ld flags; the native-callback entry points that Apple's dead stripping removes are
#      given aborting stubs (the compiler never reaches them).
#   3. the stage1 runtime object, built by stage1 itself.
# stage1 reads the host from ELISA_HOST_LINUX / ELISA_HOST_X86_64, which its wrapper normally
# exports; without them every product takes the macOS mmap flags and aborts at startup.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLCHAIN="${ELISA_TOOLCHAIN_DIR:-$HOME/.elisa-toolchain}"
CORE_REPO="${ELISA_CORE_REPO:-$ROOT_DIR/../Elisa-core}"
COMPILER_REPO="${ELISA_COMPILER_REPO:-$ROOT_DIR/../Elisa-compiler}"
LLVM_DIR="${ELISA_LLVM_DIR:-/usr/lib/llvm-20}"
STAGE0_REV="$(tr -d '[:space:]' < "$ROOT_DIR/ELISA_STAGE0_REV")"
COMPILER_REV="$(tr -d '[:space:]' < "$ROOT_DIR/ELISA_COMPILER_REV")"
STAGE0="$TOOLCHAIN/stage0/compiler/bin/elisac"
STAGE1="$TOOLCHAIN/elisac-stage1"
RUNTIME="$TOOLCHAIN/compiler/build/runtime/elisacore_runtime.o"

log() { printf 'linux_toolchain: %s\n' "$*" >&2; }
fail() { log "$*"; exit 1; }

[[ "$(uname -s)" == "Linux" && "$(uname -m)" == "x86_64" ]] || fail "only Linux x86-64 is supported"
[[ -x "$LLVM_DIR/bin/llvm-config" ]] || fail "missing $LLVM_DIR (install llvm-20-dev and clang-20)"
command -v go >/dev/null || fail "missing go"
mkdir -p "$TOOLCHAIN"
export ELISA_HOST_LINUX=1 ELISA_HOST_X86_64=1

# How to link LLVM: the shared library when the tree has one (Debian), otherwise every static
# component library in one group plus the system libraries they need (release tarballs).
if [[ -e "$LLVM_DIR/lib/libLLVM.so" ]]; then
    LLVM_STATIC=0
    LLVM_LINK=(-L"$LLVM_DIR/lib" -lLLVM -Wl,-rpath,"$LLVM_DIR/lib")
else
    LLVM_STATIC=1
    # shellcheck disable=SC2207
    LLVM_LINK=(-L"$LLVM_DIR/lib" -Wl,--start-group $("$LLVM_DIR/bin/llvm-config" --libs --link-static) -Wl,--end-group
               $("$LLVM_DIR/bin/llvm-config" --system-libs --link-static) -lstdc++)
fi
log "LLVM $("$LLVM_DIR/bin/llvm-config" --version) at $LLVM_DIR ($([[ "$LLVM_STATIC" == 1 ]] && echo static || echo shared))"

# A private checkout at an exact commit; fetches from the sibling repository, then its origin.
checkout() {
    local source="$1" target="$2" revision="$3"
    if [[ ! -d "$target/.git" ]]; then
        git clone -q --no-checkout "$source" "$target"
    fi
    if ! git -C "$target" cat-file -e "$revision^{commit}" 2>/dev/null; then
        if ! git -C "$target" fetch -q "$source" "$revision" 2>/dev/null; then
            git -C "$source" fetch -q origin "$revision"
            git -C "$target" fetch -q "$source" "$revision"
        fi
    fi
    git -C "$target" checkout -q --force "$revision"
}

if [[ ! -x "$STAGE0" ]]; then
    log "building stage0 at $STAGE0_REV"
    checkout "$CORE_REPO" "$TOOLCHAIN/stage0" "$STAGE0_REV"
    # The cgo flags name -lLLVM-C, which Debian's packages fold into libLLVM. A static tree has
    # neither name, so empty archives satisfy both and the component libraries do the work.
    mkdir -p "$TOOLCHAIN/llvm-c"
    if [[ "$LLVM_STATIC" == 1 ]]; then
        rm -f "$TOOLCHAIN/llvm-c/libLLVM-C.so" "$TOOLCHAIN/llvm-c/libLLVM.a" "$TOOLCHAIN/llvm-c/libLLVM-C.a"
        ar rc "$TOOLCHAIN/llvm-c/libLLVM.a" && ar rc "$TOOLCHAIN/llvm-c/libLLVM-C.a"
    else
        ln -sf "$LLVM_DIR/lib/libLLVM.so" "$TOOLCHAIN/llvm-c/libLLVM-C.so"
    fi
    (cd "$TOOLCHAIN/stage0/compiler" \
        && CGO_CFLAGS="-I$LLVM_DIR/include" CGO_LDFLAGS="-L$TOOLCHAIN/llvm-c ${LLVM_LINK[*]}" \
           go build -o bin/elisac ./src)
fi

if [[ ! -x "$STAGE1" ]]; then
    log "building stage1 at $COMPILER_REV (stage0, -O0; several minutes)"
    checkout "$COMPILER_REPO" "$TOOLCHAIN/compiler" "$COMPILER_REV"
    ulimit -s unlimited
    if ! "$STAGE0" -emit obj -O0 -o "$TOOLCHAIN/stage1.o" "$TOOLCHAIN/compiler/src/driver/elisac.elisa" \
        > "$TOOLCHAIN/stage1.log" 2>&1; then
        # stage0 at ELISA_STAGE0_REV cannot discharge some of the compiler's own contracts (at
        # 2678ff10, ten `ensure`s on elisacore_std/arena.elisa's clamp). -permissive compiles
        # those into runtime checks instead of refusing, so the compiler still traps if one fails.
        log "stage0 refused a contract in strict mode; retrying with -permissive (runtime checks)"
        "$STAGE0" -emit obj -O0 -permissive -o "$TOOLCHAIN/stage1.o" "$TOOLCHAIN/compiler/src/driver/elisac.elisa" \
            > "$TOOLCHAIN/stage1.permissive.log" 2>&1 \
            || fail "stage0 refused the compiler; see $TOOLCHAIN/stage1.log and stage1.permissive.log"
    fi
    bash "$TOOLCHAIN/compiler/scripts/write_profiler_hook_fallbacks.sh" > "$TOOLCHAIN/stage1_hooks.c"
    undefined="$("$LLVM_DIR/bin/clang" -no-pie -o "$TOOLCHAIN/probe" "$TOOLCHAIN/stage1.o" "$TOOLCHAIN/stage1_hooks.c" \
        "${LLVM_LINK[@]}" -lm 2>&1 | grep -o "undefined reference to \`[^']*'" | sed "s/.*\`//;s/'//" | sort -u || true)"
    {
        echo '#include <stdlib.h>'
        index=0
        for symbol in $undefined; do
            case "$symbol" in
                elisa_native_callback_*|va_start|va_end|va_copy) ;;
                *) fail "unexpected undefined symbol in stage1: $symbol" ;;
            esac
            index=$((index + 1))
            printf 'void elisa_stub_%d(void) __asm__("%s");\nvoid elisa_stub_%d(void) { abort(); }\n' "$index" "$symbol" "$index"
        done
    } > "$TOOLCHAIN/stage1_stubs.c"
    "$LLVM_DIR/bin/clang" -no-pie -o "$STAGE1" "$TOOLCHAIN/stage1.o" "$TOOLCHAIN/stage1_hooks.c" "$TOOLCHAIN/stage1_stubs.c" \
        "${LLVM_LINK[@]}" -lm
    rm -f "$TOOLCHAIN/probe" "$TOOLCHAIN/stage1.o"
fi

if [[ ! -f "$RUNTIME" ]]; then
    log "building the stage1 runtime object"
    (ulimit -s unlimited; ELISA_STAGE1_BIN="$STAGE1" ELISA_CLANG="$LLVM_DIR/bin/clang" \
        bash "$TOOLCHAIN/compiler/scripts/build_runtime_object.sh" >/dev/null)
fi

# stage1 recurses once per AST level; give it the stack its macOS link reserves.
printf 'ulimit -s unlimited\n'
printf 'export ELISA_HOST_LINUX=1 ELISA_HOST_X86_64=1\n'
# build.sh links with the `clang` on PATH; use the one that matches the LLVM stage1 was built with.
printf 'export PATH=%q:"$PATH"\n' "$LLVM_DIR/bin"
printf 'export ELISA_COMPILER_BIN=%q\n' "$STAGE1"
printf 'export ELISA_RUNTIME_OBJ=%q\n' "$RUNTIME"
printf 'export ELISA_STAGE0_BIN=%q\n' "$STAGE0"
