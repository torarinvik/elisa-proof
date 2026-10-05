# P-02 cache identity controls

Report-cache identities include the top-level fixture and recursive include closure, executable
digest, runtime system/machine, proof-affecting environment, and the report reader/writer recipe
digests. A cached report is accepted only when its payload digest and reported exit status agree.
Remote object identities include proof/compiler source trees, compiler product and driver, runtime,
target, effective compiler environment, and remote build/key/environment recipe digests.

The focused cache tests use a small fake executable to compare cached and uncached report bytes
across identical input and a source dependency edit that switches the fixture's modeled float
mode. This validates cache transport, invalidation and exit/verdict handling. It does not establish
that the real proof assistant admits the same theorem set in `proof_float_mode` and integer mode;
that requires running the proof CLI against a built verifier, which was outside the allowed checks
for this cache-only task. The run-local goal decision cache separately records `proof_float_mode`
in each entry identity, alongside ordered facts, exact goal syntax/positions, enum annotations,
and operator mask.
