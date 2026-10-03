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
  # Objects are cached like scripts/build.sh's, keyed by source, compiler, flags and target.
  OBJECT_CACHE="${ELISA_PROOF_OBJECT_CACHE:-$HOME/.cache/elisa-proof/objects}"
  xc_key() { { printf '%s\n' "$REV" "$(shasum -a 256 "$CROOT/bin/elisac-stage1" | cut -d' ' -f1)" "$OPT" "$1" x86_64-unknown-linux-gnu
    (cd "$WORK/snap/elisa-proof" && find src -type f | LC_ALL=C sort | xargs shasum -a 256); } | shasum -a 256 | cut -d' ' -f1; }
  xc() { local key; key="$(xc_key "$2")"
    if [[ "$OBJECT_CACHE" != "0" && -f "$OBJECT_CACHE/$key.o" ]]; then cp "$OBJECT_CACHE/$key.o" "$WORK/$1"; echo "reused $2 ${key:0:12}"; return; fi
    xc_compile "$@"
    [[ "$OBJECT_CACHE" == "0" ]] || { mkdir -p "$OBJECT_CACHE"; cp "$WORK/$1" "$OBJECT_CACHE/$key.o.$$" && mv -f "$OBJECT_CACHE/$key.o.$$" "$OBJECT_CACHE/$key.o"; }; }
  xc_compile() { ELISA_HOST_LINUX=1 ELISA_HOST_X86_64=1 ELISA_STAGE1_MAX_RSS_KB="${ELISA_STAGE1_MAX_RSS_KB:-8388608}" \
    "$CROOT/scripts/elisac_stage1.sh" -emit obj "-$OPT" -target-triple x86_64-unknown-linux-gnu \
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
    clang -c -O2 -o build/profile_hooks.o $C/test/parity/profile_hooks.c
    clang -Wl,-dead_strip -o build/elisa-proof.tmp ../elisa-proof-linux.o build/profile_hooks.o $C/build/runtime/elisacore_runtime.o 2>&1 | grep -v -e no-pie -e "^$" || true
    mv -f build/elisa-proof.tmp build/elisa-proof
    clang -Wl,-dead_strip -o build/elisa-proof-replay.tmp ../elisa-proof-replay-linux.o build/profile_hooks.o $C/build/runtime/elisacore_runtime.o 2>&1 | grep -v -e no-pie -e "^$" || true
    mv -f build/elisa-proof-replay.tmp build/elisa-proof-replay
    python3 scripts/build_manifest.py --binary build/elisa-proof --compiler $C/scripts/elisac_stage1.sh \
      --compiler-product $C/bin/elisac-stage1 --compiler-root $C --stage stage1 --stage1-revision "" \
      --runtime $C/build/runtime/elisacore_runtime.o --profile-hooks build/profile_hooks.o \
      --frontend-repo $C --frontend-revision "$(git -C $C rev-parse HEAD)" --proof-root "$PWD" \
      --snapshot-root "$PWD" --opt-level '"$OPT"' --compile-mode strict --contract-flag "" \
      --installed-as build/elisa-proof --output build/elisa-proof.manifest.json
    build/elisa-proof examples/verified.elisa >/dev/null'
} || status=$?
echo "build=$status"
exit $status
