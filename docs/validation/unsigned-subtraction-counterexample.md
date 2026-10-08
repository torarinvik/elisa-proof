# Exact unsigned subtraction counterexamples

The original strict-negative branch fixture was refused with a budget timeout;
the diagnostic evaluator could not evaluate its computed subtraction. The machine
diagnostic now admits same-width u8/u16/u32 subtraction only when both operands
inhabit that domain and the sampled left operand is at least the right operand.
Underflow, mixed signed/unsigned sorts and full-width arithmetic remain unknown.
Source operator guards cover the complete comparison and its premises, including
imported subtraction and ordering replacements. Theorem acceptance is unchanged.

Frozen compiler 52d60fcf and its matching runtime pass the compiled harness in
13.63 seconds / 1,785,392 KiB under the original 3 GiB focused budget. Controls
cover exact differences, zero, underflow, negative/out-of-range values, mixed
widths, untyped names, depth exhaustion and overloaded subtraction/ordering.
The original return-branch fixture retains 23 replayed certificates and now emits
a concrete disproving model for the strict-negative declaration.

The first two harness attempts failed on an inline darray argument that this
compiler backend declined as an aggregate expression. Explicit typed argument
arrays resolve that fixture construction issue. Logs are retained in
`build/unsigned-subtraction-controls*.log`; the passing run is `-values.log`.
The focused harness is registered in the integrated feature matrix. Clean paired
build, original CLI regressions, engine inventory and full compatibility remain
pending. Production prover is unchanged.
