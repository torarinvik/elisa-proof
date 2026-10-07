# Original scalar bindings and array reads — 2026-10-07

The original-source frame inventory now tracks ordered immutable primitive scalar
local declarations. A call initializer retains its exact source invocation,
actual-argument mapping and callee changes ordinals; its primitive return type
must match the declared binding type. Duplicate/shadowed local names, reassigned
locals, unsupported initializers and unknown scopes refuse the entire inventory.
No producer alias spelling or summary row establishes original call identity.

Read-only primitive darray count/index expressions are reconstructed from original
formal types and locally declared scalar names. Primitive/container type shadowing
and implementation/import scopes refuse the environment. Only direct builtin
array formals and scalar element types are accepted; nominal containers, arbitrary
fields and computed container expressions remain unsupported. Bounds, numeric
results, borrow validity and logical preconditions remain ordinary source checker
obligations; the frame helper only establishes which writes occur.

The complete condition-call fixture now proves/replays all 30 original obligations
(previously 28/30), with zero findings or admission invariant failure. Exact-count
full/summary diagnostics check all sixteen frame attempt identities, including
the original guarded_index spec and initializer-call allowance. The 37-control
runtime probe passes at O0/O2; new controls reject return-type mismatch, local
reassignment, darray shadowing and unknown array fields. Existing direct/call-frame
CLI controls, six malformed source classes on twelve routes, and portable frame
replay/13 adversarial mutations pass.

Strict all-products O2 build passes on installed immutable compiler96761822 and
matching runtime/parser sources; generation ea3896a8da7a440ca20b90fc89d56882.
Evidence in engine build/validation: prover-frame-indexed-binding-build.log,
frame_indexed_binding-O0/-O2 and proof-frame-indexed-binding-sweep.log. The full
prover matrix, richer local/alias/loop/callee/type mappings and engine gates remain
open. Completing this regression does not complete the implementation plan.
