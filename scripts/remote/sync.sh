#!/usr/bin/env bash
# Mirror this working tree (incl. .git, excl. build/) to <host>:work/elisa-proof.
# Usage: scripts/remote/sync.sh [host [port]]   (default $ELISA_REMOTE_HOST, else winpc)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOST="${1:-${ELISA_REMOTE_HOST:-winpc}}"
PORT="${2:-}"
rsync -az --delete --exclude=/build/ --exclude=__pycache__/ -e "ssh -o BatchMode=yes -o LogLevel=ERROR${PORT:+ -p $PORT}" "$ROOT/" "$HOST:work/elisa-proof/"
echo "sync=ok ($HOST)"
