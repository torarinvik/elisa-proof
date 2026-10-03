#!/usr/bin/env bash
# git bisect run step: build this commit, audit kernel_replay_standalone untimed, bad if replay gaps.
cd "$(git rev-parse --show-toplevel)"
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_PREFIX
ulimit -s unlimited
export ELISA_COMPILER_SRC=${ELISA_COMPILER_SRC:-$PWD/../Elisa-compiler} ELISA_HOST_LINUX=1 ELISA_HOST_X86_64=1 ELISA_COMPILER_BIN=${ELISA_COMPILER_BIN:?run scripts/linux_toolchain.sh first} ELISA_RUNTIME_OBJ=${ELISA_RUNTIME_OBJ:?}
rm -rf build
# Older build.sh has the Apple-only link line; link with GNU flags from the kept object instead.
scripts/build.sh >${TMPDIR:-/tmp}/bisect_build.log 2>&1
if [[ ! -x build/elisa-proof ]]; then
    obj=$(ls build/*.o build/*/*.o 2>/dev/null | grep -v profile_hooks | head -1)
    obj=${obj:-$(ls -t /tmp/elisa-proof*.o 2>/dev/null | head -1)}
    [[ -f build/elisa-proof-stage.o ]] && obj=build/elisa-proof-stage.o
    [[ -n "$obj" ]] || exit 125
    clang -no-pie -Wl,--gc-sections -o build/elisa-proof "$obj" build/profile_hooks.o "$ELISA_RUNTIME_OBJ" -lm || exit 125
fi
build/elisa-proof --json examples/kernel_replay_standalone.elisa > ${TMPDIR:-/tmp}/bisect_report.json 2>/dev/null
gaps=$(python3 -c 'import json;print(json.load(open("${TMPDIR:-/tmp}/bisect_report.json"))["replay"]["gaps"])' 2>/dev/null) || exit 125
echo "$(git rev-parse --short HEAD) gaps=$gaps" >> ${TMPDIR:-/tmp}/bisect_trace.txt
[[ "$gaps" -eq 0 ]]
