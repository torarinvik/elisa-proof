#!/usr/bin/env bash
# Build elisa-proof for $ELISA_REMOTE_HOST (default winpc), a Linux x86_64 machine reached over ssh.
# winpc's WSL VM has ~7.7 GB RAM and a native stage1 compile of src/main.elisa is OOM-killed there
# (~7.4 GB peak), so both objects are CROSS-compiled here with the pinned stage1
# (-target-triple x86_64-unknown-linux-gnu) and only linked on the remote host.
# The remote needs ~/work/Elisa-compiler at the pinned revision with build/runtime built.
# Usage: scripts/remote/build.sh [O0|O1|O2|O3]   (default O0, like scripts/build.sh). Run scripts/remote/sync.sh first.
set -uo pipefail
OPT="${1:-${ELISA_OPT_LEVEL:-O0}}"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOST="${ELISA_REMOTE_HOST:-winpc}"
PORT="${ELISA_REMOTE_PORT:-}"
RSH="ssh -o BatchMode=yes -o LogLevel=ERROR -o ConnectTimeout=20 -o ServerAliveInterval=15${PORT:+ -p $PORT}"
CROOT="${ELISA_COMPILER_ROOT:-$HOME/.cache/elisa-proof/compiler-$(cut -c1-4 "$SRC/ELISA_COMPILER_REV")}"
WORK="${ELISA_REMOTE_WORK:-${TMPDIR:-/tmp}/elisa-proof-remote-build}"
REV="$(tr -d '[:space:]' < "$SRC/ELISA_COMPILER_REV")"
TARGET="x86_64-unknown-linux-gnu"
CROSS_RSS="${ELISA_STAGE1_MAX_RSS_KB:-8388608}"
GENERATION="$(python3 "$SRC/scripts/build_manifest.py" --new-pair-generation)"
status=0
{
  set -e
  rm -rf "$WORK/snap/elisa-proof"; mkdir -p "$WORK/snap/elisa-proof" "$WORK/snap/Elisa-compiler"
  if [[ "$(cat "$WORK/snap/Elisa-compiler/.rev" 2>/dev/null)" != "$REV" ]]; then
    rm -rf "$WORK/snap/Elisa-compiler"; mkdir -p "$WORK/snap/Elisa-compiler"
    git -C "$CROOT" archive --format=tar "$REV" src elisacore_std test/parity/profile_hooks.c | tar -x -C "$WORK/snap/Elisa-compiler"
    echo "$REV" > "$WORK/snap/Elisa-compiler/.rev"
  fi
  cp -R "$SRC/src" "$SRC/examples" "$WORK/snap/elisa-proof/"
  t0=$(date +%s)
  # Objects bind to every source tree included by the proof entry point, the exact stage1
  # executable and driver, its runtime ABI, target, compile flags, and inherited environment.
  OBJECT_CACHE="${ELISA_PROOF_OBJECT_CACHE:-$HOME/.cache/elisa-proof/objects}"
  xc_key() { python3 "$SRC/scripts/remote/object_cache_key.py" \
    --revision "$REV" --compiler-product "$CROOT/bin/elisac-stage1" \
    --compiler-driver "$CROOT/scripts/elisac_stage1.sh" \
    --runtime "$CROOT/build/runtime/elisacore_runtime.o" \
    --opt "$OPT" --main "$1" --target "$TARGET" \
    --proof-source-root "$WORK/snap/elisa-proof" \
    --compiler-source-root "$WORK/snap/Elisa-compiler" \
    --set-env ELISA_HOST_LINUX=1 --set-env ELISA_HOST_X86_64=1 \
    --set-env "ELISA_STAGE1_MAX_RSS_KB=$CROSS_RSS"; }
  xc() { local key; key="$(xc_key "$2")"
    if [[ "$OBJECT_CACHE" != "0" && -f "$OBJECT_CACHE/$key.o" ]]; then cp "$OBJECT_CACHE/$key.o" "$WORK/$1"; echo "reused $2 ${key:0:12}"; return; fi
    xc_compile "$@"
    [[ "$OBJECT_CACHE" == "0" ]] || { mkdir -p "$OBJECT_CACHE"; cp "$WORK/$1" "$OBJECT_CACHE/$key.o.$$" && mv -f "$OBJECT_CACHE/$key.o.$$" "$OBJECT_CACHE/$key.o"; }; }
  xc_compile() { ELISA_HOST_LINUX=1 ELISA_HOST_X86_64=1 ELISA_STAGE1_MAX_RSS_KB="$CROSS_RSS" \
    "$CROOT/scripts/elisac_stage1.sh" -emit obj "-$OPT" -target-triple "$TARGET" \
    -o "$WORK/$1" "$WORK/snap/elisa-proof/src/$2"; }
  # The replay checker (test.sh's build/elisa-proof-replay) compiles alongside the main tool.
  xc elisa-proof-replay-linux.o replay_main.elisa & replay_pid=$!
  xc elisa-proof-linux.o main.elisa
  wait "$replay_pid"
  echo "cross-compile: $(( $(date +%s) - t0 ))s"
  rsync -az --timeout=120 -e "$RSH" "$WORK/elisa-proof-linux.o" "$WORK/elisa-proof-replay-linux.o" "$HOST":work/
  $RSH "$HOST" 'set -e; cd ~/work/elisa-proof; C=~/work/Elisa-compiler; mkdir -p build
    export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0=$C  # rsynced checkout, other owner
    export LLVM_CONFIG=/usr/lib/llvm-19/bin/llvm-config PATH=$C/tools/linux_shim:$PATH
    generation='"$GENERATION"'; stage="build/.remote-pair-$generation"
    mkdir "$stage"
    trap '\''rm -rf "$stage"'\'' EXIT
    clang -c -O2 -o build/profile_hooks.o $C/test/parity/profile_hooks.c
    clang -Wl,-dead_strip -o "$stage/elisa-proof" ../elisa-proof-linux.o build/profile_hooks.o $C/build/runtime/elisacore_runtime.o
    clang -Wl,-dead_strip -o "$stage/elisa-proof-replay" ../elisa-proof-replay-linux.o build/profile_hooks.o $C/build/runtime/elisacore_runtime.o
    frontend_revision=$(git -C "$C" rev-parse HEAD)
    for product in elisa-proof elisa-proof-replay; do
      python3 scripts/build_manifest.py --pair-generation "$generation" \
        --binary "$stage/$product" --compiler "$C/scripts/elisac_stage1.sh" \
        --compiler-product "$C/bin/elisac-stage1" --compiler-root "$C" --stage stage1 --stage1-revision "" \
        --runtime "$C/build/runtime/elisacore_runtime.o" --profile-hooks build/profile_hooks.o \
        --frontend-repo "$C" --frontend-revision "$frontend_revision" --proof-root "$PWD" \
        --snapshot-root "$PWD" --opt-level '"$OPT"' --compile-mode strict --contract-flag "" \
        --installed-as "build/elisa-proof-generations/$generation/$product" \
        --output "$stage/$product.manifest.json"
      sha256sum "$stage/$product.manifest.json" | cut -d" " -f1 > "$stage/$product.manifest.json.sha256"
    done
    python3 scripts/verify_product_pair.py publish \
      --generation-root build/elisa-proof-generations --generation "$generation" \
      --proof-binary "$stage/elisa-proof" --proof-manifest "$stage/elisa-proof.manifest.json" \
      --replay-binary "$stage/elisa-proof-replay" --replay-manifest "$stage/elisa-proof-replay.manifest.json"
    for product in elisa-proof elisa-proof-replay; do
      cp "build/elisa-proof-generations/$generation/$product" "build/$product.$generation.tmp"
      mv -f "build/$product.$generation.tmp" "build/$product"
      cp "build/elisa-proof-generations/$generation/$product.manifest.json" "build/$product.manifest.json.$generation.tmp"
      mv -f "build/$product.manifest.json.$generation.tmp" "build/$product.manifest.json"
      cp "build/elisa-proof-generations/$generation/$product.manifest.json.sha256" "build/$product.manifest.json.sha256.$generation.tmp"
      mv -f "build/$product.manifest.json.sha256.$generation.tmp" "build/$product.manifest.json.sha256"
    done
    pair_json=$(python3 scripts/verify_product_pair.py resolve --generation-root build/elisa-proof-generations)
    proof_binary=$(printf "%s\n" "$pair_json" | python3 -c '\''import json,sys; print(json.load(sys.stdin)["products"]["elisa-proof"]["binary"])'\'')
    "$proof_binary" examples/verified.elisa >/dev/null'
} || status=$?
echo "build=$status"
exit $status
