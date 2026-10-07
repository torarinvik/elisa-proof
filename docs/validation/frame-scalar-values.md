# Source frame events with builtin scalar arithmetic

`frame_source_scalar_values.elisa` reconstructs call-free scalar arithmetic and
comparisons in direct write RHS expressions and returns. It checks ordered
formal names/types from the original owner, unwraps only parentheses and
mutable/borrow/lmut type qualifiers, and requires direct primitive scalar leaves.
Supported unary/binary operations are the builtin scalar arithmetic, bitwise,
comparison and Boolean operators. Unknown identifiers, nominal operands, calls,
fields and other expression forms invalidate the complete inventory. Arithmetic
results are not proved by this helper: it establishes absence of additional
writes, while ordinary checker obligations retain numeric semantics and bounds.

The existing bounded declaration guard must exclude imports, implementation
scopes and primitive type shadowing before arithmetic can enter the inventory.
Value expressions share a 4096-node work cap and refuse depth 64. Compound
assignment operators remain unsupported pending their complete source mapping.
The composed event probe passes 29 controls at O0/O2, adding the original bump
and measure body shapes plus refusal of nominal operands, nested calls and
primitive operator implementations.

The full condition-call fixture retains all 30 obligations and now replays 18
certificates (previously 14): bump and measure each gain distinct source-backed
frame-spec and frame-allow certificates. Admission still refuses the report at
goal-attempt-coverage until the remaining caller/callee mappings are established.
Contract-placement remains fully proved with 31/31 certificates. Both exact
counts and helper frame identities are checked in invariant diagnostics. Frame
CLI/portable probes, malformed-source admission and 193-entry kernel inventory
pass. The fresh engine sweep remains 66/73 with the same seven failures.

Compiler provenance: the live compiler checkout advanced to 1a7b0d96 during this
turn and its old product became stale. Validation uses the installed immutable
96761822 snapshot, its matching runtime object and parser sources archived at
that exact full revision. ELISA_STAGE1_ROOT is supplied explicitly so the build
manifest resolves the installed binary provenance. No stale-product override is
used. Strict all-products O2 build succeeds, generation
13f91374164147aab0349f145eb44869. Evidence: engine build/validation/
prover-frame-scalar-values-build.log, proof-frame-scalar-values-sweep.log and
frame_scalar_values-O0/-O2 artifacts. Broader callee, alias, dynamic, branch and
operator/type mappings, full compiler qualification and the engine plan remain
open; the original scope is unchanged.
