# Original-source indexed scalar snapshots

The engine's `AudioVirtual.position` captures `pool.frames[slot]` into an
immutable `length`, then returns a conditional value bounded by that length.
The producer had an equality for the capture, but independent replay did not
support indexed local initializers. It also substituted an unrelated equation
to executable `elapsed_frames()` call text while deciding the final theorem.

## Changes

* Replay resolves the original owner's formal-rooted field path and builtin
  array element type. The immutable local's integer type must match exactly.
  The index reads immutable integer formals through supported pure arithmetic.
* Replay reconstructs the complete suffix after capture. Only independently
  typed scalar reads, immutable scalar declarations, returns and branches are
  supported. Calls, writes, loops, shadowed bindings, unknown statements and
  unresolved operator environments refuse this equality. Both branches are
  checked; no alias-disjointness assumption is needed when all writes are absent.
* Arithmetic can read an earlier unique immutable scalar's captured value.
  This admits an equation to that value, never an equation to its initializer
  or a repeatable non-pure invocation.
* A failed goal may retry with only type/constant premises, or with unrelated
  traced local equations to executable call text omitted. These retries remove
  assumptions. Goals, ordinary operator checks and independent kernel replay
  remain unchanged.

The public field-type resolver and snapshot predicate do not authenticate an
arbitrary source AST. Report replay supplies independently checked source and
still requires the exact original declaration, initializer, positions and owner.

## Evidence

Compiler `63585c5f56bd3c18d9ff983503bac8f005df40b4`, matching runtime and
archived parser; strict O2 pair generation `402fbf9514a648e7aaf45c3c79399e0b`.

`test_indexed_scalar_snapshot.py` passes both JSON routes for nine cases:
three accepted captures, three invalid bounds, and writes/calls/branch writes
after capture. The isolated capture replays 5/5 obligations. The guarded-call
control goes from 12/13 to 13/13 after call-equation premise reduction. The
independent source runtime probe passes O0 and O2. The source-call-result,
guarded-call, source-admission, frame-source, frame-call and portable-frame
controls pass, including their existing refusal mutations. Source length and
whitespace checks pass.

The engine AudioVirtual report now has 109 obligations, 107 replayed, no
findings, and two remaining replay gaps in `next_virtual` and its sentinel
wrapper. `position` and its wrapper prove. The uncached engine sweep remains
68/73; this is a partial repair, not a green engine or complete matrix claim.
Engine logs: `prover-indexed-snapshot-final-build.log` and
`proof-indexed-snapshot-final-sweep.log` under `build/validation`.
