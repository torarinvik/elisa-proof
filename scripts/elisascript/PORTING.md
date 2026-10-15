# ElisaScript script ports

The Python versions remain authoritative until each ElisaScript counterpart has
been compiled and run against the same input, with matching exit status and
output. Migrate and qualify one script at a time.

Proof-specific ElisaScript ports and their tests stay in this repository, and
each `.elisascript` counterpart lives beside its original Python script. The
sibling `elisa-script` repository is for general-purpose language, runtime, and
tooling work; do not put Elisa-Proof scripts there.

| Python reference | ElisaScript counterpart | Status |
| --- | --- | --- |
| `scripts/test_report_output_loop_layout.py` | `scripts/test_report_output_loop_layout.elisascript` | Active source port, colocated with its Python reference. The candidate uses the `read_text_bounded` builtin backed by the shared stable UTF-8 reader, then checks four fixed fragments with a local KMP matcher so repeated near-matches stay linear. The source parity guard pins repository-root derivation, fragments, diagnostics, strict UTF-8, byte/path bounds, file mutation checks, and the matcher. Runtime parity remains unqualified; retain Python. |
| `scripts/test_global_mutable_array_owner_identity.py` | queued | No candidate promoted until the active port has parity evidence. |
| `scripts/test_resource_call_storage_confinement_static.py` | queued | No candidate promoted until the active port has parity evidence. |

## Qualification record (2026-10-15)

The Python reference exits 0 and prints the expected success line. The installed
runner and retained native binaries identify as version 0.1 and predate this
source. An earlier nested-module draft failed with `UnsupportedDeclaration`.
After relocation under `elisa-proof/scripts` and correction of the
source-root path, the old candidate using `Path.read_text()` caused the rebuilt
runner to exit 138 without diagnostics. The current candidate uses the bounded
reader, but retained v0.1 runners predate the execution-facade export of
`EsBoundedText` and reject its name during `--check`. No ElisaScript runtime
parity has been established. Keep the Python reference in place.

The candidate previously used an unsupported `Path.read_text()` call, which
could read an oversized or changing file before checking its length. It now
uses `EsBoundedText::read_utf8` with the reader's 16 MiB maximum; the Python
reference applies the same bound with a nonblocking descriptor. Both readers
require a regular file, verify device/inode identity when opening, compare
identity, size, modification time, and change time after reading, retry
interrupted open/stat/fstat/read operations up to four times, require strict
UTF-8, and normalize CRLF and CR line endings. Close remains single-shot to
avoid retrying a potentially reused descriptor. Python uses substring
membership; the ElisaScript candidate uses `contains` for four fixed fragments.
The source parity guard verifies the exact fragments, diagnostics, reader
selection, and the reader's byte/path bounds and mutation checks. This is source
review evidence only, not runtime parity.

The launcher execution facade now includes the shared bounded reader, so the
candidate uses that runtime module without a sibling-repository include. The
installed v0.1 launcher predates this facade change; a runner built from the
current facade is still required before parity can be claimed.

An earlier candidate source hash
(`cad4ffe7bd5baab2f1086ac59d74ed3578e94abd60e8a1280dfbda54051e5304`) lowered
with compiler revision `5241b2aed51641a217ca44ac4ee116ee66ac96e6` and binary
hash `8623ee8dabd773976e370f553cd91457703c4098d135a3d1648cc72609b1b915`; this
evidence does not apply to the current candidate. The installed v0.1 runner
rejects the current `EsBoundedText` import during `--check`. The available
`run_bounded_test.sh` is the Core `-emit test` path for `@test` fixtures and
does not provide script APIs such as `Script::source_path`, `Path`, `print`, or
`write_stderr`. No current-source compile/run parity is established. Python
remains authoritative until a matching script runner demonstrates equal exit
status and output.

A bounded public-launcher attempt on 2026-10-15 used the local launcher pinned by SHA-256
`80fe9f28cd0d36434e0bae68267b8652c833447c1b6bd01c0e4eaf7a8eca94bf`. It exited 1 before running
the script body with `undefined identifier "EsBoundedText"`; the watchdog observed no RSS samples.
The keyed log is retained at
`../elisa-script/.validation/559321b6196f71e963c0b223fe1a396e2ccf184c7a758ee8ba9a29ab09f0ed37/logs/test.i2M2MY`.
This confirms the import incompatibility on the pinned public launcher, not runtime parity. Keep
the Python reference authoritative.

The current candidate uses `read_text_bounded(path, maximum_bytes)`, a typed
global builtin already present in the current source tree. The interpreter
delegates this opcode to `EsBoundedText::read_utf8`, which enforces the strict
UTF-8, 16 MiB and 4 KiB caps, regular-file and stable-metadata checks, bounded
EINTR retries, and owned result storage. This avoids requiring user scripts to
import an internal runtime module. The source parity guard verifies this
registry-to-interpreter path and the candidate call.

Fragment matching uses the candidate's KMP helper. This keeps each search
linear in source plus needle length on repeated-prefix near-matches while using
scratch space proportional to the fixed needle. The generic interpreter
`sview.contains` implementation uses a nested scan, so it is not suitable for
this 16 MiB adversarial-input check.

The current candidate is SHA-256
`b0e5117a25f920d21699a168c7b5cc92f264a3be7c80769c3abbb3b3d3aed24a`. The Python reference
passes and its source hash remains
`55fe791691f426fdacba65b18311906c532e0c38c432d9bb74b349bcd95c2475`. A direct installed-runner
`--check` against the current candidate exits 1 at line 16 with
`undefined identifier "read_text_bounded"`; the installed v0.1 binary predates
this builtin and the corresponding `ReadBoundedText` opcode.

An additional bounded Core test fixture was added at
`../elisa-script/test/ir/elisascript_read_text_utf8_test.elisascript` for strict text decoding.
The shared execution facade test attempt exited 1 before test execution (438,112 KiB sampled
peak RSS; no watchdog trip). The pinned Core compiler reports parser incompatibilities in the
then-current checkout, including an invalid function nested inside `const module ProcessWait`, a
set-dispatch guard in `src/ir/lower_ast.elisa`, and vendored runtime/test modules. The `ProcessWait`
helper has since been moved to the enclosing private scope, and the set-dispatch guard now uses the
current return-guard syntax. These source changes have not been compiled. The earlier attempt
reported no diagnostics at the UTF-8 validator or focused fixture and does not qualify the change.

The focused fixture now checks that `read_text_bounded` rejects malformed UTF-8,
accepts a valid multibyte sequence at the exact bound, and rejects input beyond
the requested limit. A bounded Core test attempt against the updated fixture is
still required; the pinned compiler previously failed on parser incompatibilities
elsewhere in the current checkout, before test execution. Runtime parity remains
unqualified; keep the Python reference authoritative.

### Current bounded launcher build — 2026-10-15

I refreshed a private snapshot of the current ElisaScript `src/` and `vendor/`
trees after moving `process_wait_poll_limit` out of `const module ProcessWait`,
then rebuilt the native launcher with the pinned compiler from
`scripts/validation_identity.sh` (revision
`5241b2aed51641a217ca44ac4ee116ee66ac96e6`, binary SHA-256
`8623ee8dabd773976e370f553cd91457703c4098d135a3d1648cc72609b1b915`). The
first bounded build completed with exit 1 after 2.04 seconds and 372,080 KiB
peak RSS under a 1.5 GiB / 180-second limit; no watchdog limit was reached and
no launcher artifact was produced. It confirmed the old `ProcessWait`
nested-function diagnostic was gone, but found one remaining `false return` at
`src/ir/lower_ast.elisa:9849`. I changed that statement to `return false` and
rebuilt from a second fresh snapshot. That build also completed with exit 1
(1.48 seconds, 385,600 KiB peak RSS; no watchdog limit reached), with the
lowerer diagnostic gone. Its remaining parser incompatibility is at
`vendor/elisa-compiler/elisacore_std/elisacore_runtime_concurrency.elisa:1123`
(`expected }, got :`) for `atomic[T]{value: value}`. The vendored declaration is
`struct atomic[T]`. The vendored parser source in
`vendor/elisa-compiler/src/parser/parser_expr_ops.elisa` parses brace construction
as a postfix on any active expression, including lowercase generic names. This
differs from the pinned compiler's matched StructPy source: its
`compiler/src/parser/parser_expr_parsepostfix_to_expectnewlineaftervalueexpr.go`
only recognizes brace constructors for capitalized names. The build diagnostic
therefore reflects a real compatibility gap between the pinned parser and the
older adapted parser snapshot used by Elisascript. Neither build produced a
launcher, so runtime parity remains unqualified; keep the Python reference
authoritative until the syntax is reconciled and parity checks pass.

To address this Core parse failure, the pinned StructPy parser source now has a
narrow brace-literal path for the existing lowercase builtin `atomic[T]`. It
preserves the capitalized-name rule for user structs and does not change
lowercase indexed-value record updates. The source edit is formatted and passes
`git diff --check`; the pinned compiler has not been rebuilt, and validation
remains disabled pending explicit reauthorization.

The vendored Core initializer now also avoids the lowercase generic-brace form:
`atomic_cell` starts from `zeroed`, assigns `slot.value`, then wraps the slot.
This source workaround has not been compiled. The port remains unqualified and
Python remains authoritative.

A subsequent current-source launcher build used
`../Elisa-compiler/build/self_host_gen2/elisac-stage1-gen2 -O0 -emit exe` against
`src/driver/elisascript.elisa`. The bounded wrapper terminated it at 180.09 seconds with status
`-15` (timeout), peak RSS 718,144 KiB under the 1.5 GiB cap, no diagnostics, and no executable
artifact. Its report is `.validation/current-launcher-build.log.json`; it records no compiler
source identity, so this attempt is not provenance-qualified. Do not claim script parity or retry
this unchanged build until the compiler/toolchain or build strategy changes.

On 2026-10-15, a separately launched bounded retry against the current dirty ElisaScript source
also failed to produce a launcher. The wrapper ended it at 360.12 seconds with status `-15`
(`reason=timeout`), peak RSS 680,512 KiB under its 1.5 GiB cap, no diagnostics, and no artifact.
The exact command and measured outcome are retained in
`../elisa-script/.validation/current-launcher-build-retry.log.json`. This was a bounded observation
of a second attempt, not evidence of a compiler error or proof of compiler-source identity; do not
repeat the unchanged build. Python remains authoritative and runtime parity remains unqualified.
