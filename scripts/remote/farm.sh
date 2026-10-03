#!/usr/bin/env bash
# Run scripts/test.sh across a farm of Linux hosts. The Mac cross-compiles, every farm host links
# its own binaries and prefetches its weighted share of the fixtures and Python
# tests with all of its cores, and the first farm host gathers the shares and runs the serial
# assertions from that cache.
#
# Farm hosts must share one checkout path (reports name absolute source paths) and be provisioned
# with scripts/remote/provision.sh. ELISA_FARM lists them as "user@host#port" separated by spaces;
# the first is the main host. Cores are read from each host; ELISA_FARM_WEIGHT_CORES=0 weights
# evenly instead.
# Usage: scripts/remote/farm.sh     Log: $ELISA_REMOTE_WORK/farm.log; exits with test.sh's status.
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="${ELISA_REMOTE_WORK:-${TMPDIR:-/tmp}/elisa-proof-remote-build}"
# The first host runs the serial assertions, incl. the 180 s-watchdog kernel audit: put the
# least contended host first (vast3's quota is shared with other agents' jobs).
read -r -a FARM <<<"${ELISA_FARM:-root@171.227.197.156#47777 root@184.144.152.26#34348 root@76.71.171.67#40919}"
CTL="/tmp/epf-$(id -u)"; mkdir -p "$CTL"  # short: macOS caps socket paths at 104 bytes
T0=$(date +%s); step() { echo "[$(( $(date +%s) - T0 ))s] $*"; }

host_of() { echo "${1%%#*}"; }
port_of() { [[ "$1" == *"#"* ]] && echo "${1##*#}" || echo 22; }
# One multiplexed connection per host; ssh's own failures (255) are retried, a command's are not.
# Bulk copies get their own connections; a shared master stalled them. Dead links fail fast.
copy_opts() { echo "-o BatchMode=yes -o LogLevel=ERROR -o ConnectTimeout=20 -o ServerAliveInterval=15 -o ServerAliveCountMax=4 -p $(port_of "$1")"; }
ssh_opts() { echo "$(copy_opts "$1") -o ControlMaster=auto -o ControlPath=$CTL/%C -o ControlPersist=600"; }
rssh() {
    local target="$1"; shift
    local attempt status
    for attempt in 1 2 3; do
        # shellcheck disable=SC2046
        ssh $(ssh_opts "$target") "$(host_of "$target")" "$@"; status=$?
        [[ "$status" -ne 255 ]] && return "$status"
        sleep "$attempt"
    done
    return 255
}
rsync_to() { local target="$1" src="$2" dest="$3"; shift 3; rsync -az --delete --timeout=120 "$@" -e "ssh $(copy_opts "$target")" "$src" "$(host_of "$target"):$dest"; }
rsync_from() { local target="$1" src="$2" dest="$3"; rsync -az --timeout=120 -e "ssh $(copy_opts "$target")" "$(host_of "$target"):$src" "$dest"; }

# Rented hosts come and go: drop any that does not answer now rather than fail mid-run.
alive=()
for target in "${FARM[@]}"; do
    if ssh $(copy_opts "$target") -o ConnectTimeout=10 "$(host_of "$target")" true 2>/dev/null; then alive+=("$target")
    else echo "skipping unreachable farm host $target"; fi
done
[[ ${#alive[@]} -gt 0 ]] || { echo "no farm host reachable"; exit 1; }
FARM=("${alive[@]}")
MAIN="${FARM[0]}"
step "sync ${#FARM[@]} farm hosts"
pids=()
for target in "${FARM[@]}"; do
    rsync_to "$target" "$DIR/../../" "work/elisa-proof/" --exclude=/build/ --exclude=__pycache__/ >/dev/null & pids+=($!)
done
for pid in ${pids[@]+"${pids[@]}"}; do wait "$pid" || { echo "farm sync failed"; exit 1; }; done

# Each host links its own binaries from the cross-compiled objects (cached after the first), so
# only compressed objects cross the Mac's uplink and no single linker host is on the path.
step "build (compile once, link on every host)"
build_on() { ELISA_REMOTE_HOST="$(host_of "$1")" ELISA_REMOTE_PORT="$(port_of "$1")" ELISA_REMOTE_WORK="$WORK/build-$2" bash "$DIR/build.sh" | tail -1; return "${PIPESTATUS[0]}"; }
build_on "$MAIN" 0 || exit 1
pids=()
for i in "${!FARM[@]}"; do [[ "$i" -eq 0 ]] && continue; build_on "${FARM[$i]}" "$i" & pids+=($!); done
for pid in ${pids[@]+"${pids[@]}"}; do wait "$pid" || { echo "farm build failed"; exit 1; }; done

# Weighted shards: a host allowed c CPUs owns ceil(c/4) of the shard indices.
cores=(); total=0
for target in "${FARM[@]}"; do
    # The cgroup CPU quota, not nproc: a container showing 80 cores may be throttled to 19.
    c="$(rssh "$target" "cd ~/work/elisa-proof && python3 scripts/report_cache.py --cpus")"
    # ELISA_FARM_CPUS caps our share of a host whose quota other sessions also use.
    [[ -n "${ELISA_FARM_CPUS:-}" && "$c" -gt "$ELISA_FARM_CPUS" ]] && c="$ELISA_FARM_CPUS"
    [[ "${ELISA_FARM_WEIGHT_CORES:-1}" == "0" ]] && c=4
    w=$(( (c + 3) / 4 )); cores+=("$c:$w"); total=$(( total + w ))
done
step "fixtures on ${#FARM[@]} hosts (${cores[*]} cpus:shards, $total shards)"
CACHE=/tmp/elisa-proof-farm-cache
# phase <name> <cache-preparation>: every host runs its weighted shard of one prefetch phase.
run_phase() {
    local phase="$1" prepare="$2" next=0 pids=() i target c w mine
    for i in "${!FARM[@]}"; do
        target="${FARM[$i]}"; c="${cores[$i]%%:*}"; w="${cores[$i]##*:}"
        mine="$(seq -s, "$next" $(( next + w - 1 )))"; next=$(( next + w ))
        # Python tests start their own fixture pools; keep those small so a host is not oversubscribed.
        rssh "$target" "cd ~/work/elisa-proof && $prepare && ELISA_PROOF_PREFETCH_PHASE=$phase ELISA_PROOF_REPORT_CACHE=$CACHE ELISA_PROOF_JOBS=2 ELISA_PROOF_SHARDS='$mine/$total' python3 scripts/prefetch_reports.py scripts/test.sh \$PWD/build/elisa-proof $CACHE \$PWD $c" & pids+=($!)
    done
    for pid in ${pids[@]+"${pids[@]}"}; do wait "$pid" || return 1; done
}
run_phase fixtures "rm -rf $CACHE && mkdir -p $CACHE" || { echo "fixture prefetch failed"; exit 1; }

step "gather and redistribute"
rm -rf "$WORK/farm-cache"; mkdir -p "$WORK/farm-cache"
for target in "${FARM[@]}"; do rsync_from "$target" "$CACHE/" "$WORK/farm-cache/" & done; wait
rm -rf "$WORK/farm-cache/pending" "$WORK/farm-cache/slots"
pids=()
for target in "${FARM[@]}"; do rsync_to "$target" "$WORK/farm-cache/" "$CACHE/" & pids+=($!); done
for pid in ${pids[@]+"${pids[@]}"}; do wait "$pid" || { echo "redistribute failed"; exit 1; }; done

step "python tests on ${#FARM[@]} hosts"
run_phase tests "true" || { echo "test prefetch failed"; exit 1; }
rm -rf "$WORK/farm-cache"; mkdir -p "$WORK/farm-cache"
for target in "${FARM[@]:1}"; do rsync_from "$target" "$CACHE/" "$WORK/farm-cache/" & done; wait
rsync -az --timeout=120 -e "ssh $(copy_opts "$MAIN")" --exclude=pending/ --exclude=slots/ "$WORK/farm-cache/" "$(host_of "$MAIN"):$CACHE/" || exit 1

step "serial assertions on $(host_of "$MAIN")"
rssh "$MAIN" "cd ~/work/elisa-proof && export ELISA_STAGE1_MAX_RSS_KB=\${ELISA_STAGE1_MAX_RSS_KB:-16777216} GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0=\$HOME/work/Elisa-compiler LLVM_CONFIG=/usr/lib/llvm-19/bin/llvm-config PATH=\$HOME/work/Elisa-compiler/tools/linux_shim:\$PATH && rm -rf $CACHE/pending && ELISA_PROOF_SKIP_BUILD=1 ELISA_PROOF_JOBS=${ELISA_FARM_CPUS:-\$(python3 scripts/report_cache.py --cpus)} ELISA_PROOF_REPORT_CACHE=$CACHE ELISA_FULL_AUDIT_TIME_LIMIT=${ELISA_FULL_AUDIT_TIME_LIMIT:-600} bash scripts/test.sh > /tmp/elisa-proof-farm.log 2>&1; echo test=\$? >> /tmp/elisa-proof-farm.log"
rsync_from "$MAIN" /tmp/elisa-proof-farm.log "$WORK/farm.log"
step done
tail -5 "$WORK/farm.log"
grep -q '^test=0$' "$WORK/farm.log"
