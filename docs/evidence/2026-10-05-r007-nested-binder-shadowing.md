# R-007 nested finite binder shadowing regression

This is a focused kernel regression, not completion of R-007. The runtime harness constructs
`forall x in 0..<2: forall x in 0..<1: x == 0`. The outer instance at `x = 1` must leave the
inner `x` bound to its own finite range; replay proves the nested proposition. A direct helper
control also verifies that substitution rewrites an inner quantifier's range, which is outside
that binder's scope, while preserving its body when the binder shadows the target. The
adversarial control substitutes free `y` for `x` beneath `forall y`; replay returns the explicit
`substitution-under-quantifier` unsupported node rather than capturing `y`.

## Focused validation

The runtime probe compiled with the pinned Stage1 product in the existing R-042 validation
worktree, then linked against that worktree's matching runtime object and profile hooks. The
repository snapshot `.rev` is exactly `7b27fa312c5af923f044f6ee0e5e1de4f811f595`, matching this
proof checkout's `ELISA_COMPILER_REV`. Product provenance reports compiler source revision
`e4a16fd24dacb2db54b7cc3aff2d19312ff2edf7` and source-tree SHA-256
`84fb7fa7127611ef47ece30bd63ab5aaf467a5dbbcba1da3a6238960dffb7142`.

- Proof source base: `71ede8b430af3b97917818496bbd6728563a024a`.
- Regression commit: `688f3a04370d883f69a110651d812dfb04b6ec15`.
- Stage1 product SHA-256: `7bcb8590304617b61d1462f6b40c0bff006e3fbe537489d1ce867766e918bd39`.
- Runtime object SHA-256: `b51e6114f0576681e432e1162a3dbdcdac46c140d3b7e7256c0069be0bd11897`.
- Profile hooks SHA-256: `ff7eb87b67bbc470ee95c320bb95ff125300f1edc8c2e67585d282e27e0e9711`.
- Probe object SHA-256: `f608c1dbf43d96af4fcb397e519ebb17eba42ec4c222842cd9d34df89bf9c059`.
- Linked probe SHA-256: `8a6448d8c6870638b054c4372e24a3f85949cf12d73cbbf821f4dbb308932042`.
- `git diff --check`: passed; linked runtime probe exit status: `0`.

The compiler product was invoked directly because this fresh worktree has no local pinned build
directory. The test compiled `examples/kernel_interval_contradiction_runtime.elisa` at O0, linked
it with the runtime object and profile hooks above, and ran the result. No broader suite was run.

This establishes only the tested same-name shadowing behavior and one free-name capture refusal.
Binders are still identified by source names, not distinct binder IDs. Differently named nested
quantifier substitution remains conservatively unsupported because the current kernel has no
alpha-renaming/binding-level representation; this regression does not test eigenvariable escape,
stale contexts, or mutation after certificate validation. R-007 remains open.
