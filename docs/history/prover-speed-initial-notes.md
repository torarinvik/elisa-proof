# Prover speed work (WIP)

- Branch `prover-speed` from `mocap-cleaner-proofs` 7571dfa.
- ELISA_COMPILER_REV bumped d8b5d305 -> 6a4dc861 (studio-globals stage1, newest).
- Build: build.sh already defaults to -O2 (project.json "opt": "0" is not what build.sh uses).
  Build needs HOME pointed at an empty dir: otherwise build.sh reads ~/.elisac/stage1/SNAPSHOT
  (b841e64b) and reports a false stage1/frontend mismatch for the studio-globals binary.
  Local O2 build: ~9 min wall, ~4 GB peak.
- The prover has no external SMT solver (no z3/process spawn); obligations go to built-in
  linear/difference-constraint procedures. "SMT query cache" therefore means caching
  built-in decision results.
- Baseline timings (build/proof-baseline-19611a2.tsv, winpc, 3 jobs): corpus total 734 s;
  slowest: cli/main 55, retime_apply 45, presets 42, rig_physics 39, rig_cache 35,
  ops_file 34, rig_stack 32, corrections 25, glb_tracks 25, retime_laws 24.
- Mac load average was ~300 at 09:46, so local timing is not usable; time on v80/v32/v20.

## Next
1. Profile cli/main, retime_laws, glb_tracks, rig_physics, track with elisa-profiler
   (--mode sample, ELISA_COMPILER_ROOT=elisa-compiler-worktrees/studio-globals) or `sample`.
2. Cross-compile (scripts/remote in mocap-cleaner) and time on the fleet.
