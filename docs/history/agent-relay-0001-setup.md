From: mac
Date: 2026-10-02
Kind: task
Re: -

Set up a census runner in WSL2 (Ubuntu), in the WSL filesystem (~/), not /mnt/c:
1. Clone elisa-proof and the pinned Elisa-compiler (see scripts/build.sh for the
   expected location and ELISA_COMPILER_SRC / ELISA_COMPILER_ROOT).
2. Run scripts/build.sh on main and report whether it succeeds; include errors if not.
3. If it builds, time `build/elisa-proof --json examples/kernel_intern_runtime.elisa`
   and report wall and user time plus `nproc`.
Reply in to-mac/0001-setup-result.md.
