# R-006/R-088 unknown portable node tag regression

## Change

Commit `d628b02134ccaffbbdbf2f5b5ce95b8187ec7db7` adds one case to the existing fresh-process
portable replay mutation matrix. It changes the `kind` field of a theorem-reachable kernel node to
`unknown-kind`, then checks the same structured refusal and no-partial-replay invariants as the
other package mutations. The prior matrix exercised shape, arity, indices, cycles, and forward
references, but did not explicitly mutate a node's textual kind tag. Commit
`19db84a89c48180467d6a3cc8794e29cceabaafe` updates the matrix summary to count this case. No decoder
implementation changed.

## Validation

The isolated worktree was created from committed proof `main` at `71ede8b430af3b97917818496bbd6728563a024a`.
The regression was tested at test-code commit `19db84a89c48180467d6a3cc8794e29cceabaafe` with:

```sh
ELISA_COMPILER_BIN='/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/Elisa-compiler/bin/elisac-stage1' \
ELISA_RUNTIME_OBJ='/Users/torarinvikbjarko/Documents/Coding Projects/Elisa Projects/Elisa-compiler/build/runtime/elisacore_runtime.o' \
ELISA_PROOF_PRODUCTS=all ELISA_PROOF_BUILD_JOBS=2 scripts/build.sh
python3 scripts/test_portable_replay.py
```

The replay test passed: 16 positive packages and the full refusal suite, including the 29-case
structure-aware matrix. The new reachable unknown-tag mutation was refused in a fresh replay process,
with no theorem-level partial replay. The matrix reported peak observed wall time 0.049 s, child CPU
0.042 s, and sampled RSS 26,509,312 bytes, under its 5 s wall, 4 s CPU, and 512 MiB RSS limits.

The exact paired O2 strict build manifests identify proof HEAD `d628b02134ccaffbbdbf2f5b5ce95b8187ec7db7`,
proof source-tree SHA-256 `843aea66d982ae07ad31f2c8dc1c096d140a8da18102b5961b5a5f905f62321b`, and frontend
revision `7b27fa312c5af923f044f6ee0e5e1de4f811f595`. The Stage1 product SHA-256 was
`3e23836002e5b6035dba43185ea84a9ab5358707c1ee4148c4752cacb2f41a70`; the runtime object SHA-256 was
`b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`. The resulting proof binary
SHA-256 is `64a1aadc426c5be6e1cbe56d98bce14579ad78bf9d9cbd44f11bf7ea54a35442`; replay binary SHA-256
is `bdb2978a89cb0b448d4cb6ac2c9241147c55898592ad53cfea237fd36465a3f3`. Product paths and full
build identities are in the paired manifests generated under the isolated worktree's `build/`.

The matrix harness SHA-256 at test time was
`10106201ef8cda5ab11e290042a4b6982b330b16afe3f6c17ddef8ee16e8f248`.
This deterministic tag mutation is one focused extension; it is not broad coverage-guided fuzzing
or completion of R-006.
