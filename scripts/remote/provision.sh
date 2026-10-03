#!/usr/bin/env bash
# Prepare an Ubuntu 24.04 x86_64 host as a scripts/remote/test.sh test host: clang-19 and
# llvm-19-dev from apt, and ~/work/Elisa-compiler copied from a Linux build at the pinned revision
# (default ~/.cache/elisa-proof/linux-compiler-<rev4>, itself copied once from winpc).
# Usage: scripts/remote/provision.sh <host> [port]
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOST="$1"; PORT="${2:-}"
REV4="$(cut -c1-4 "$ROOT/ELISA_COMPILER_REV")"
LOCAL="${ELISA_LINUX_COMPILER:-$HOME/.cache/elisa-proof/linux-compiler-$REV4}"
if [[ ! -f "$LOCAL/build/runtime/elisacore_runtime.o" ]]; then
    mkdir -p "$LOCAL"; rsync -az "${ELISA_REMOTE_HOST:-winpc}:work/Elisa-compiler/" "$LOCAL/"
fi
SSH="ssh -o BatchMode=yes -o LogLevel=ERROR -o StrictHostKeyChecking=accept-new${PORT:+ -p $PORT}"
$SSH "$HOST" 'export DEBIAN_FRONTEND=noninteractive; command -v clang-19 >/dev/null && command -v rg >/dev/null && python3 -c "import z3" 2>/dev/null && [ -x /usr/lib/llvm-19/bin/llvm-config ] ||
    { apt-get update -qq >/dev/null && apt-get install -y -qq clang-19 llvm-19-dev ripgrep python3-z3 >/dev/null; }; mkdir -p ~/work'
rsync -az --delete -e "$SSH" "$LOCAL/" "$HOST:work/Elisa-compiler/"
$SSH "$HOST" 'test -f ~/work/Elisa-compiler/build/runtime/elisacore_runtime.o && /usr/lib/llvm-19/bin/llvm-config --version' >/dev/null
echo "provision=ok ($HOST, $($SSH "$HOST" nproc) cores)"
