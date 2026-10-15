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
| `scripts/test_report_output_loop_layout.py` | `scripts/test_report_output_loop_layout.elisascript` | Active source port, colocated with its Python reference. The candidate resolves the original launch spelling with `path_real(Script::invocation_path())`, matching Python `Path.resolve()` when symlink components and `..` interact. It uses the `read_text_bounded` builtin backed by the shared stable UTF-8 reader, then checks four fixed fragments with a local KMP matcher with a fixed stack table so repeated near-matches stay linear without per-search allocation. The source parity guard pins repository-root derivation, fragments, diagnostics, strict UTF-8, reader limits and stability checks, and the matcher. Current reader source rejects empty/NUL paths and UTF-8 path views of 4,096 bytes or more; all post-open cleanup paths now propagate close failure as a read error. Positive short reads continue through EOF within the byte cap, and consecutive `EINTR` retries remain bounded; Python uses one pre-sized bytearray bounded by the opened-file size, avoiding retention of a separate bytes object for each positive short read. Regressions cover one-byte reads, a full-limit file delivered in 512-byte reads with requests capped at 16,384 bytes, transient and repeated EINTR, same-inode size drift before open, growth during reading, same-size metadata drift at the intermediate fstat, and descriptor closure on errors. The current Python and ElisaScript readers align on opened-size bounds and short-request metadata checks. Runtime parity is still unqualified, so retain Python. |
| `scripts/test_global_mutable_array_owner_identity.py` | queued | No candidate promoted until the active port has parity evidence. |
| `scripts/test_resource_call_storage_confinement_static.py` | queued | No candidate promoted until the active port has parity evidence. |

The shared reader's `Global{Read,Write}` effects are intentional. It returns
permanent string storage through `string_view_copy`, which accesses the small
string cache and records permanent string lengths in the global cache. The
`read_text_bounded` builtin keeps those implementation effects inside the
interpreter and exposes `File.Read` to script callers.

## Qualification record (2026-10-15)

The Python reference exits 0 and prints the expected success line. The installed
runner and retained native binaries identify as version 0.1 and predate this
source. An earlier nested-module draft failed with `UnsupportedDeclaration`.
After relocation under `elisa-proof/scripts` and correction of the
source-root path, the old candidate using `Path.read_text()` caused the rebuilt
runner to exit 138 without diagnostics. An intermediate candidate imported
`EsBoundedText` directly, which retained v0.1 runners rejected during
`--check`. The current candidate uses the `read_text_bounded` builtin described
below. No ElisaScript runtime parity has been established. Keep the Python
reference in place.

An earlier candidate used an unsupported `Path.read_text()` call, which could
read an oversized or changing file before checking its length. An intermediate
candidate used `EsBoundedText::read_utf8` with the reader's 16 MiB maximum; the
current candidate calls the `read_text_bounded` builtin backed by that reader.
The Python reference applies the same bound with a nonblocking descriptor. Both
readers require a regular file, verify device/inode identity when opening, compare
identity, size, modification time, and change time after reading, require strict
UTF-8, and normalize CRLF and CR line endings. ElisaScript retries interrupted
open/stat/fstat/read operations at most four times; Python has the same explicit
retry wrapper, while its runtime may transparently restart a syscall before the
wrapper observes `InterruptedError`. Close remains single-shot to avoid retrying
a potentially reused descriptor. This difference is limited to repeated
interruptions and still needs runtime parity evidence. Python uses substring
membership; the ElisaScript candidate uses a local KMP matcher with a fixed
256-entry stack table for the four short fragments, preserving linear-time
behavior on repeated-prefix near-matches without allocating per search. The
matcher rejects longer needles, and the source parity guard checks that all
required fragments fit the bound.
The source parity guard verifies the exact fragments, diagnostics, reader
selection, reader limits, `same_file` and `stable_file` formulas, overflow
probe, byte-read bounds, retry handling, and stability checks. A fresh review of
ElisaScript HEAD `854fd6d379c3246829261eeb6e10ab04e83b91ae` confirmed the reader
rejects empty or NUL-containing paths and path views with length `>= 4096`,
matching the Python byte-length cutoff for UTF-8 paths. Every post-open cleanup
now passes through `close_descriptor`, which raises `ReadError.ReadFailed` when
close fails. Thus close failure takes precedence over a pending reader error,
matching Python's `finally` behavior at the API level; the script maps both to
the same generic read diagnostic and exit status. The guard checks the close
helper's failure mapping, requires each post-open error to pair with exactly one
checked close (excluding a failed open), and pins final close placement;
per-error close precedence remains source-review evidence. The ElisaScript
path-form fixture compares the `Path` and `sview` entrypoints, but neither that
fixture nor the reader has run under a source-matched launcher. This remains
source evidence, not runtime parity.

The launcher execution facade includes the shared bounded reader, which backs
the current builtin without requiring a script-level runtime import. The
installed v0.1 launcher predates this facade change; a runner built from the
current facade is still required before parity can be claimed.

An earlier candidate source hash
(`cad4ffe7bd5baab2f1086ac59d74ed3578e94abd60e8a1280dfbda54051e5304`) lowered
with compiler revision `5241b2aed51641a217ca44ac4ee116ee66ac96e6` and binary
hash `8623ee8dabd773976e370f553cd91457703c4098d135a3d1648cc72609b1b915`; this
evidence does not apply to the current candidate. At that time, the installed
v0.1 runner rejected the intermediate candidate's `EsBoundedText` import during
`--check`. The available `run_bounded_test.sh` is the Core `-emit test` path
for `@test` fixtures and
does not provide script APIs such as `Script::source_path`, `Path`, `print`, or
`write_stderr`. No current-source compile/run parity is established. Python
remains authoritative until a matching script runner demonstrates equal exit
status and output.

A bounded public-launcher attempt on 2026-10-15 used the local launcher pinned by SHA-256
`80fe9f28cd0d36434e0bae68267b8652c833447c1b6bd01c0e4eaf7a8eca94bf`. It exited 1 before running
the script body with `undefined identifier "EsBoundedText"`; the watchdog observed no RSS samples.
The keyed log is retained at
`../elisa-script/.validation/559321b6196f71e963c0b223fe1a396e2ccf184c7a758ee8ba9a29ab09f0ed37/logs/test.i2M2MY`.
This confirms the import incompatibility on the pinned public launcher for the
intermediate candidate, not runtime parity. Keep the Python reference authoritative.


A fresh check of the current candidate with that same v0.1 launcher (SHA-256
`80fe9f28cd0d36434e0bae68267b8652c833447c1b6bd01c0e4eaf7a8eca94bf`) exited
1 before execution with `undefined identifier "read_text_bounded" at 40`. This
confirms the installed launcher predates the builtin required by the current
candidate; it provides no runtime parity evidence.

The current candidate uses `read_text_bounded(path, maximum_bytes)`, a typed
global builtin already present in the current source tree. The interpreter
delegates this opcode to `EsBoundedText::read_utf8`, which enforces the strict
UTF-8, 16 MiB and 4 KiB caps, regular-file and stable-metadata checks, bounded
EINTR retries, and owned result storage. This avoids requiring user scripts to
import an internal runtime module. The source parity guard verifies this
registry-to-interpreter path and the candidate call.

Fragment matching uses the candidate's KMP helper. A 256-entry fixed stack
table avoids allocation failure during the four bounded searches; the helper
rejects longer needles. The source parity guard checks that every required
fragment fits this bound. Each check stays linear in source plus needle length
on repeated-prefix near-matches. The generic interpreter `sview.contains`
implementation uses a nested scan, so it is not suitable for this 16 MiB
adversarial-input check.

The current candidate is SHA-256
`fb5a0e8b665bf21e7b5666fc39112f3362fd14fc4310cd44907f2e38732ad013`. The Python reference
passes and its source hash remains
`395cca39647956d1c51f42394187ac02b9d24f11ba6c2a525e79dde8166b7926`. A direct installed-runner
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

A bounded source build with `goal-compiler-latest-b11e` reached type checking
and rejected the temporary `zeroed` initializer because generic `T` may be
non-null. Restored direct `atomic[T]{value: value}` initialization; the same
build reported no parse error at this syntax. It also reported `unknown type
"Path"` in `bounded_text_posix.elisa` and Global/protocol capability diagnostics
across the vendored Core runtime. A subsequent update made the reader entry
generic over `Str`, removing its script-only `Path` type from the self-hosted
compiler source; the latest bounded build no longer reports that error. The
historical compiler log is
`../elisa-engine/build/script-validation/elisascript-port-runner-b11e-v5-20261015.log`.

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

A later bounded current-source attempt used `goal-compiler-latest-b11e` with the same `-O0 -emit
exe` launcher command. It completed in 60.78 seconds with status 1 and peak RSS 563,952 KiB, below
the 1.5 GiB cap; no launcher was produced. The log contains 65 diagnostics, including a parser
module helper missing an explicit `Global.Read` grant and widespread vendored `Str.__cast__` and
`Store.store_get` protocol capability mismatches. These failures are outside the port's candidate
body, and the log does not record a compiler source identity. Do not retry this unchanged build;
Python remains authoritative and runtime parity remains unqualified.

A final bounded current-source build after the reader and atomic-initializer updates used
`goal-compiler-latest-b11e -O0 -emit exe` with a 150-second and 1.5-GiB cap. It exited 1 in
63.76 seconds at 485,440 KiB and produced no launcher. The former `Path` error is gone, and the
bounded-reader module has no diagnostics; the remaining log consists of broad Global/protocol
capability diagnostics in the self-hosted compiler and vendored runtime. The exact report is
`../elisa-script/.validation/elisascript-port-bounded-current2-20261015.log.json`. Python remains
authoritative and runtime parity remains unqualified.

A later bounded runner build completed against `goal-compiler-latest-b11e` on
2026-10-15. The watchdog recorded status 1 after 79.89 seconds, peak RSS
441,200 KiB under the 1.5 GiB limit, and no launcher artifact. Its log contains
64 Global/protocol capability diagnostics in the vendored compiler runtime; the
active script source itself is not implicated. The exact command, exit reason,
resource measurements, and diagnostics are retained in
`../elisa-engine/build/script-validation/elisascript-port-runner-b11e-v6-20261015.log.json`
and the adjacent `.log`. This binary does not record compiler source identity,
so the result is diagnostic only. Do not repeat the unchanged build; keep the
Python reference authoritative until the source-matched runner and parity
controls pass.

A subsequent v7 bounded runner attempt also completed with status 1 and no
artifact. The watchdog report records 89.47 seconds and 428,896 KiB peak RSS
under the same 1.5 GiB limit. Its 1,234-line log is dominated by Global and
protocol capability errors in the vendored compiler runtime and includes
several launcher-level `Global` grant diagnostics. The report is
`../elisa-engine/build/script-validation/elisascript-port-runner-b11e-v7-20261015.log.json`;
the adjacent `.log` contains the diagnostics. As with v6, the b11e binary does
not identify compiler source, so this is diagnostic evidence only. Do not claim
runtime parity or advance to another Python script based on this build.

### Immutable post-edit launcher probes — 2026-10-15

The bounded-reader and path-form fixture edits in the shared `elisa-script`
checkout postdate the v7 report. At capture time, I copied the working tree to
`/tmp/elisascript-port-snapshot.BCCA6p/source`, excluding `.git` and
`.validation`, and verified all 1,837 copied files against the checkout. The
snapshot remains available. Its reproducible manifest SHA-256 is
`18caac11b3dd97687ce8402e5005dbd33cfdac1abc6075302373cc0802838026`. To
recompute it, sort the snapshot's regular files by relative POSIX path, excluding
`.git` and `.validation`; for each file, append `relative-path`, a NUL byte, its
lowercase SHA-256 hex digest, and a newline to the outer SHA-256 input. A later
comparison found the current checkout retains the same 1,837 paths but has six
changed files: `vendor/elisa-compiler/elisacore_std/collections.elisa`,
`debug_referee.elisa`, `elisacore_runtime_prelude.elisa`,
`elisacore_runtime_strings.elisa`, `elisacore_runtime_system_bridge.elisa`, and
`runtime.elisa`. Thus the snapshot is historical build input, not a copy of the
current tree.

Two immutable-snapshot launcher builds used the same `-O0 -emit exe` command.
`goal-compiler-latest-b11e` (SHA-256
`5888942e08da166185c76a8e6a13d774c3aa57cf290f093f1c9ce03dd60a887e`)
exited 1 in 84.58 seconds at 425,008 KiB peak RSS. The newer `perf-stage1-f7b6`
(SHA-256 `26aa2625f28cc2f0adabe9a6f6255376f3198313fb55480e1ea49f8261b3e946`)
exited 1 in 47.70 seconds at 624,848 KiB peak RSS. Each emitted the same 1,298
diagnostics across 48 files, including 330 in `src/ir/interpret.elisa` and none
in `src/runtime/bounded_text_posix.elisa`; no launcher artifact was produced.
The logs are retained at `/tmp/elisascript-port-snapshot.BCCA6p/build.log` and
`/tmp/elisascript-port-snapshot.BCCA6p/perf-build.log`; both have SHA-256
`a1ca8c7a3f8101be5e7a41f471a3b8ac0221d9c965feac3528e138e7fa71c2ab`.


A later bounded launcher build of the shared `elisa-script` checkout used the
provenance-pinned `goal-compiler-latest-b11e` binary (compiler source revision
`b11e9121c64d94bbc8881db58ae850bf4933ceb9`, product SHA-256
`5888942e08da166185c76a8e6a13d774c3aa57cf290f093f1c9ce03dd60a887e`). It
exited 1 after 64.44 seconds at 430,528 KiB peak RSS and produced no launcher.
Its 974 diagnostics span 42 files, including 330 in `src/ir/interpret.elisa`
and none in `src/runtime/bounded_text_posix.elisa`. The report is
`../elisa-engine/build/script-validation/elisascript-port-runner-b11e-v13-20261015.log.json`;
the log SHA-256 is
`2aa970a7975fa626584a9cba49bc61c1de97914a6f585aa429d3e39546ec044d`. The
compiler is from b11e, not current Elisa-compiler HEAD, and this build did not
retain a content manifest of the changing ElisaScript checkout. Treat it as
diagnostic evidence only.

These source-identified probes show that the updated bounded-reader module is
not the reported failure site, while the compiler/runtime source as a whole
still cannot produce a launcher. They do not compile or run the proof candidate,
so runtime parity remains unqualified and Python remains authoritative.

A separate fresh-compiler bootstrap probe used isolated Elisa-compiler HEAD
`be83d91458d42b2d5e603dd73139cf9ffa9294f4` with the provenance-valid current
Stage0 binary (SHA-256
`4bb24ef6ca2a6860dcb4f081c3f362801c5f200ed4339446ceb3169f5a78b442`). Stage0
source checks passed, but `bash scripts/elisac_stage1.sh --seed` exited 1 after
207.43 seconds at 3,017,104 KiB peak process-group RSS and produced no Stage1
compiler executable. The isolated snapshot contains a 1,792-byte
`stage1_out.o` side effect, but no `bin/elisac-stage1` or published Stage1
artifact. The retained log is
`/tmp/elisa-compiler-be83d9145.HaPAnH/seed.log` (SHA-256
`8b9c901e44e576c894e6ff50e68926edbb66b440e6dfd83bd56a23fc4f913389`). It
contains compiler-wide region-parameter inference and borrowed-local escape
diagnostics. The provenance-matched `perf-stage1-f7b6` binary is not a valid
bootstrap for HEAD: that revision is 503 commits and 2,257 files behind, and
there is no verified matching runtime object. Thus no source-matched launcher
is available for this candidate; do not advance the queue or claim runtime
parity.

A second seed attempt used a clean clone at the same compiler HEAD, the same
Stage0 binary, and byte-identical seed scripts. Its 1.5 GiB process-group guard
stopped Stage0 at 1,575,744 KiB (limit 1,572,864 KiB), before diagnostics
completed or an object was emitted. No Stage1 compiler or new seed object was
produced. The retained log is
`/private/tmp/elisa-compiler-be83-port-qual/build/seed-be83-stage0-gomemlimit-20261015.log`
(SHA-256
`ced8dd15d4acbbde2bd729fefb37041e0f37156c3a485e81ba154756a798ee19`). The
earlier 3 GiB attempt with these same inputs reached compiler diagnostics and
reported 81 region-parameter inference errors and 9 borrowed-local escape
errors. Raising the cap alone would repeat that source failure; a source fix or
new compiler revision is needed before another seed attempt is useful.

A v14 bounded current-worktree runner attempt used the same b11e command. It
exited 1 after 64.75 seconds at 471,952 KiB peak RSS and emitted 973 diagnostics;
no launcher was produced. Its report is
`../elisa-engine/build/script-validation/elisascript-port-runner-b11e-v14-20261015.log.json`;
the log SHA-256 is
`fafa3aa1a83b0b6360ddee59c8dd4da7c204e76bdb4696304b40fde8e40d58cb`. The
worktree was mutable and the compiler binary is still pinned to b11e rather than
the current compiler source, so this remains diagnostic evidence only. Do not
advance the port queue or rerun the same command; Python remains authoritative.

A subsequent v15 attempt exited 1 after 70.86 seconds at 477,872 KiB peak RSS,
with 970 Global capability diagnostics across 40 files and no launcher. The
watchdog report is
`../elisa-engine/build/script-validation/elisascript-port-runner-b11e-v15-20261015.log.json`;
the log SHA-256 is
`2334a76853b580b35b799fc325d5d8d08c90bca23f7f91f72a494aab19488bc1`. This
used the mutable shared source tree and an older b11e compiler binary, so the
three fewer diagnostics than v14 are a triage delta, not a qualified source
result. Do not advance the script queue until an immutable current-source
compiler produces a launcher and parity passes.

A v18 bounded runner build used the same b11e compiler binary against the
shared ElisaScript checkout. It exited 1 after 60.58 seconds at 581,104 KiB
peak RSS and produced no launcher. Its log contains 969 diagnostics across 40
files, including 330 in `src/ir/interpret.elisa` and none in
`src/runtime/bounded_text_posix.elisa`. The report is
`../elisa-engine/build/script-validation/elisascript-port-runner-b11e-v18-20261015.log.json`;
the log SHA-256 is
`252017e62c268a6157313a4bcb4041381c484457a36a9131df132c304bd2144e`. Its
diagnostic log is byte-identical to v17, so another build of the same b11e
binary against this changing checkout would not qualify the active candidate.
An earlier availability audit recorded ElisaScript HEAD
`e6ab4ecb679ba1edd1c72b2f2204da546703afb8`; it has since advanced to
`854fd6d379c3246829261eeb6e10ab04e83b91ae`. A subsequent local change to the
bounded reader is currently uncommitted. Elisa-compiler remains at HEAD
`be83d91458d42b2d5e603dd73139cf9ffa9294f4`, with local changes in the shared
checkout. Available Stage1 binaries are pinned to older revisions `f7b6c4a2`
and `b11e9121`, and no launcher report newer than v18 was found. The v19 check
log is empty, with no JSON result or executable, so it is inconclusive. No
source-matched runner is available for parity.

I also tried a direct Stage0 object-emission fallback from an isolated snapshot
of the current ElisaScript working tree. The snapshot contains 1,838 files and
has manifest SHA-256
`7da209e967555c7bc1ad9963a24746f033293e844d3a5760a0dfce921bf6c782`. The
current Core Stage0 binary (SHA-256
`4bb24ef6ca2a6860dcb4f081c3f362801c5f200ed4339446ceb3169f5a78b442`) ran
`elisac -O0 -emit obj -o /tmp/elisascript-stage0-object-20261015.o src/driver/elisascript.elisa`.
Its embedded Core revision is `5bc4b62d2e57a135ca2c57a78b4058e0ad2c8896`
with `vcs.modified=false`, matching the current Core HEAD; its source tree is
clean and `assert_stage0_fresh.sh` passes.
It exited 1 after 1.07 seconds at 456,144 KiB peak RSS and emitted no object;
the parser rejected the lowercase generic-brace `atomic[T]{value: value}` form
in `vendor/elisa-compiler/elisacore_std/elisacore_runtime_concurrency.elisa:1123`.
The captured log is `/tmp/elisascript-stage0-object-20261015.log` (SHA-256
`211ec4df3073eb6fa76930451663d799e679f4b57751aed79cbb4bae270f636a`). This
Stage0 path cannot produce the runner either. A separate Stage1 bootstrap from
current Elisa-compiler HEAD `be83d91458d42b2d5e603dd73139cf9ffa9294f4` also
failed as recorded above. Therefore runtime parity is still unqualified and
Python remains authoritative; do not advance to the next Python script.

A follow-up seed run on the same clean Elisa-compiler HEAD, Stage0 binary, and
byte-identical seed scripts ended at the same 1,572,864 KiB memory guard. It
sampled 1,581,168 KiB and produced no Stage1 compiler or new seed object; the
old 1,792-byte `stage1_out.o` predates the run. The retained log is
`/private/tmp/elisa-compiler-be83-port-qual/build/seed-be83-stage0-gomemlimit-1250-20261015.log`
(SHA-256
`426299fb332add3ec95fa29f78c92a34f6aa3576394c57bc6b8efe6b6d5e1183`). It
differs from the prior same-input memory-guard run only in the final sampled
RSS. These repeated results leave no useful unchanged bootstrap retry; the
compiler source or available memory strategy must change before another seed
attempt can qualify a launcher.

A third clean-HEAD seed used `GOMEMLIMIT=1000` with the same compiler snapshot,
Stage0 binary, and seed scripts. It still crossed the 1,572,864 KiB process
guard, sampling 1,581,248 KiB, and produced no Stage1. The preexisting
`stage1_out.o` in that snapshot was not used; the attempted object path
`build/elisac_stage1.o.tmp.71989` is absent. The retained log is
`/private/tmp/elisa-compiler-be83-port-qual/build/seed-be83-stage0-gomemlimit-1000-20261015.log`
(SHA-256
`7e765a2c61e7cb45ae6b5a1d8f44e5d26819f02735a9c82d21d65f656951b235`). Lowering
the Go heap goal did not keep process RSS under the guard. This run also did
not include the later uncommitted compiler edits in the shared checkout, so a
useful source retry requires a coherent immutable snapshot containing fixes
for the known diagnostics as well as a viable memory envelope.

A read-only comparison of the current dirty compiler checkout with the earlier
3-GiB seed diagnostics found that its `@callbacks` annotation may fix one
specific borrowed-return error, while the parser edit only adds catch-token
source metadata. The recorded 81 region-inference errors across 22 files, nine
borrowed-local escapes in assignment code generation, and other hard diagnostic
groups remain untouched. The current edits therefore do not yet form a useful
seed snapshot; changing only the memory limit will not qualify a launcher.

### Source-loader effect propagation — 2026-10-15

The sibling `elisa-script` source loader now declares and propagates the
`Global{Read,Write}` effect required by its bounded diagnostic-text allocations
through `src/ir/source.elisa`, `src/ir/source_file.elisa`, the direct runner API
callers, and the launcher's `run_test_mode`/`run`/`main` chain. This is source
progress only: no build or runtime parity check was run, and the Python
reference remains authoritative.

The source and file loaders now use local `can Global.Read, Global.Write`
scopes at their allocation, parser, and diagnostic-helper call boundaries. The
effect also reaches the two differential runner adapters and the affected
loader/runner test call scopes. This remains source-only progress; runtime
parity is unqualified.

### Active candidate semantic review — 2026-10-15

An independent source-level comparison of `scripts/test_report_output_loop_layout.py`
and its colocated `.elisascript` found no ordinary-input behavior mismatch. Both
resolve the same project root and target file, normalize CRLF and CR identically,
check the same four fragments, and use matching success/failure output and exit
codes. The ElisaScript KMP matcher is equivalent to Python substring membership
for these ASCII fragments in UTF-8 input. Its prefix table now has fixed stack
storage, removing the per-search allocation edge case.

This remains source review only. The candidate has not run under a matched
current ElisaScript launcher, so process output and exit parity are unqualified.
The installed v0.1 runner does not support the `read_text_bounded` builtin. The
IR bounded-reader test routes through the interpreter because direct bytecode
has no implementation for `ReadBoundedText`; that fallback is present in source,
but was not executed here. Review also found that the test's over-limit
`rejected` flag starts as true and is left true on both success and error paths,
so its assertion did not prove that the error branch ran. The flag now starts
false and is mutable, so only the caught-error branch sets it true. This source
fix has not been run: the bounded test wrapper still rejects the dirty pinned
compiler checkout and requires explicit validation reauthorization.

Source tracing now covers the raw path bytes as well. The file-backed runner
scans the NUL-terminated `u8&` filename into a bounded `sview` without UTF-8
validation; `Path` normalization copies and compares bytes, `path_real` passes
the NUL-terminated bytes to `realpath` and copies the returned bytes, and
`read_text_bounded` forwards its runtime text bytes to the bounded reader, which
copies them unchanged into the POSIX path buffer. These source paths reject
empty, NUL-containing, and over-limit values but do not reject invalid UTF-8.
This supports parity with Python's `os.fsencode` path handling at the source
level. No source-matched launcher has exercised an invalid-UTF-8 filename, so
runtime parity remains unqualified.

### Reauthorized validation identity recheck — 2026-10-15

After direct user reauthorization, `./scripts/validation_identity.sh` was run
from `elisa-script`. It exited 125 before invoking a compiler with
`validation_identity: compiler checkout is dirty; refusing to bind an
executable to an ambiguous source tree`. The pinned compiler checkout is at
`5241b2aed51641a217ca44ac4ee116ee66ac96e6` and has modifications in
`src/parser/parser_ergonomics_test.go` and
`src/parser/parser_expr_parsepostfix_to_expectnewlineaftervalueexpr.go`. Its
existing `bin/elisac` SHA-256 is
`8623ee8dabd773976e370f553cd91457703c4098d135a3d1648cc72609b1b915`. The
bounded wrapper uses that canonical path and will refuse at the same identity
gate, so no build or runtime evidence was produced. Keep Python authoritative,
leave this candidate `active_unqualified`, and do not advance to the queued
Python script.

### Bounded-reader API caller reconciliation — 2026-10-15

A fresh source-only audit of the shared `elisa-script` tree found no remaining
live-code calls to `EsBoundedText::read_utf8(...)`; Path-valued callers now use
`read_utf8_path_text(f"{path}", limit)`. The generic `read_utf8[T: Str]` entry
point remains available, but no live call sites currently use it. This includes
the IR `read_text_bounded` dispatch and its differential fixture.
`git diff --check` passes in the shared tree. These edits are not
compiler-checked: the canonical compiler checkout remains dirty and the bounded
validation identity gate still refuses before compilation. Source API
consistency is improved, but the active Python/ElisaScript port stays
`active_unqualified` until a source-matched runtime check succeeds.

### Current2 bounded-runner source trace — 2026-10-15

A read-only inspection of `.validation/native/port-build-current2-20261015`
found `logs/build.log.json` status `1` (`reason: completed`, peak RSS 385,600
KiB, elapsed 1.48 s; JSON SHA-256
`1987a3d98e51658401eba9092db7da7729ddf38c076bd84dda5c0500428c89bc`). Its
paired `logs/build.log` (SHA-256
`3c7645467eb79578d368abb1d1baab68041b785cfe2a04eaa313975b49c2925d`) contains
2,647 warnings and zero error/note diagnostics. The only `runtime.elisa`
reference is a style warning at line 321. Therefore this retained log does not
show the reported `Str` capability errors, and it does not explain the nonzero
build status.

The source snapshot itself predates the current bounded-reader change:
`source/src/runtime/bounded_text_posix.elisa` (SHA-256
`2b8482e7a779594cbbb70ac2f54593779d278c2eb0a3b456d16505f1946591c3`) declares
`read_utf8(input_path: Path, ...)`; it has no generic `read_utf8[T: Str]`. The
snapshot's `vendor/elisa-compiler/elisacore_std/runtime.elisa` (SHA-256
`91fd412f216e720df22d04664644c9085f164dc8058169ef146d29fb6c2858f0`) matches
the older `e6ab4ecb` version, whose `Str.__cast__` protocol omitted the global
and unsafe effects used by string-view conversions. Current HEAD `854fd6d3`
widened that protocol to include `Global{Read,Write}` and
`Unsafe{PointerCast,PointerArithmetic}` while adding the generic reader wrapper.
This rules out the generic wrapper as the cause of an error in the retained
current2 source snapshot; the snapshot is stale relative to HEAD.

The generic `read_utf8[T: Str]` wrapper formats `T`, so its effect row now
includes `Console.Format` and `Unsafe.PointerArithmetic`, matching the current
`Str.__cast__` protocol alongside the existing global, allocation, and pointer
cast effects. This is source alignment only; no source-matched compiler has
checked the signature. Runtime parity remains unqualified.

The Python reference and shared ElisaScript reader accept positive short reads
until EOF, bounded by the input byte limit and file-stability checks. Repeated
consecutive `EINTR` retries still fail closed after four retries. A Python
regression exercises a stable full-limit file delivered in 512-byte reads and
repeated-interruption failure. This establishes source-level contract
alignment only; runtime parity remains unqualified. The Python reference SHA-256 is now
`395cca39647956d1c51f42394187ac02b9d24f11ba6c2a525e79dde8166b7926`; the
inventory records this source identity. Retain Python as authoritative.

### Latest bounded identity and source-parity checks — 2026-10-15

The canonical `elisa-script/scripts/validation_identity.sh` now succeeds against
the clean Elisa-core checkout at revision
`5bc4b62d2e57a135ca2c57a78b4058e0ad2c8896`, with embedded binary revision
matching and `vcs.modified=false`. The earlier dirty-checkout refusal above is
historical and no longer describes the current identity gate. The proof-side
`scripts/test_elisascript_report_output_port_parity.py` source guard passes for
the active `test_report_output_loop_layout` candidate. No candidate runtime
execution was performed in this check, so its inventory status remains
`active_unqualified` and Python remains authoritative until runtime parity is
qualified.

### Bounded lowering of the active candidate — 2026-10-15

Rechecked the canonical compiler identity and lowered the current
`scripts/test_report_output_loop_layout.elisascript` source with
`elisa-script/scripts/run_bounded_lowering.sh`. It exited 0 under Elisa-core
revision `5bc4b62d2e57a135ca2c57a78b4058e0ad2c8896`, binary SHA-256
`4bb24ef6ca2a6860dcb4f081c3f362801c5f200ed4339446ceb3169f5a78b442`; the
captured source was 3,130 bytes with SHA-256
`fb5a0e8b665bf21e7b5666fc39112f3362fd14fc4310cd44907f2e38732ad013`. The
bounded wrapper observed 160 KiB RSS and reported no timeout, RSS, or output
guard event. The retained log SHA-256 is
`d0ab17afee4c69027f1d584f4e8a994edefa04c79140b2fcf05bbf1d31e0ca82`. This
confirms current-toolchain lowering only: the candidate has not executed, so
Python remains authoritative and the port stays `active_unqualified`.

### Bounded launcher-entrypoint lowering — 2026-10-15

Extended `elisa-script/scripts/run_bounded_lowering.sh` to admit both `.elisa`
and `.elisascript` sources; it still snapshots a bounded source and uses the
same compiler identity, process-tree RSS, time, and output guards. Lowering
`src/driver/elisascript.elisa` with the canonical compiler did not complete:
the wrapper stopped it at the 512 MiB RSS cap (observed 534,752 KiB, exit 137)
after 2,647 warnings across 321 files. The partial log contains no compiler
errors; its SHA-256 is
`24be19609768810d0b0d64b3552fecad0bdc611e368b55bb7ed86d26cd15971d`. The
captured 32,415-byte driver source SHA-256 is
`2b103f943a72ead050e5118a1ff8159061a527f1bd5633ac46710159169688ea`. The
emergency-stop latch was not set. This leaves launcher compilation and runtime
parity unresolved; keep Python authoritative and do not advance the port queue.

### Bounded-reader descriptor cleanup review — 2026-10-15

The source-only parity review found that the shared ElisaScript reader could
panic during buffer reservation or growth after opening its descriptor, while
the Python reference closes the descriptor in a `finally` path. The current
reader moves scratch and input-buffer reservation before `open`, sizes retained
storage to the pre-open file size, and rejects a size change or growth beyond
that snapshot before appending. Handled post-open errors close through the
checked `close_descriptor` helper. This removes the identified allocation-panic
leak path at source level. `git diff --check` passes for the reader change; no
compiler or runtime check was performed. Runtime parity remains unqualified,
the candidate remains `active_unqualified`, and Python remains authoritative.

The Python reference now also compares the opened descriptor size with the
pre-open path snapshot. Both implementations reject a same-inode size change
between the initial `stat` and `open`, while retaining later metadata checks
for changes during reading. This closes a narrow source-level parity gap;
runtime parity remains unqualified.

The Python reference now reads into one bytearray sized from the opened file,
limits each read to the runtime reader's 16 KiB scratch capacity, rejects data
beyond the opened-size snapshot, and performs the same descriptor-stability
check when the requested read is smaller than that capacity. A deterministic
regression appends to the opened file during reading and verifies failure plus
descriptor closure. The Python behavior and source-contract checks pass;
ElisaScript runtime parity remains unqualified.

### Bounded-read builtin dispatch review — 2026-10-15

Source inspection traced the active candidate's `read_text_bounded` call through
`Opcode.ReadBoundedText`: the lowerer requires positional `Path` and `usize`
arguments. The shared global-call boundary records the registry effect and
error contract; the IR verifier checks operand count/types, `sview` result,
`File.Read`, and `FileIoError`. The interpreter rejects runtime kind mismatch,
negative or non-round-trippable limits, then delegates to
`EsBoundedText::read_utf8_path_text` and maps reader errors to `FileIo`.
This confirms the source-level dispatch contract for the active port. The
candidate has not executed through this path; runtime parity remains
unqualified and Python remains authoritative.

### Invocation path resolution correction — 2026-10-15

A source review found a launch-path edge mismatch: `Script::source_path()` is
lexically normalized before symlink resolution, while Python's
`Path(__file__).resolve()` resolves symlinks before processing `..`. The
candidate now calls `path_real(Script::invocation_path())`, so the original
launch spelling reaches filesystem resolution first. The source audit also
traced arbitrary pathname bytes through invocation capture, byte-based path
normalization/join, `realpath`, and the bounded reader; pathname bytes are not
UTF-8-decoded by these layers. This is source evidence only.

Python regressions and the reader and source-parity guards pass after the
change. Guarded lowering of the exact 3,134-byte candidate passed with source
SHA-256
`94e6820769936d1065ae973919c5a4dac7f3ba7abf903bb271f225cff553f88d`, using
Elisa-core revision `5bc4b62d2e57a135ca2c57a78b4058e0ad2c8896` and binary
SHA-256 `4bb24ef6ca2a6860dcb4f081c3f362801c5f200ed4339446ceb3169f5a78b442`.
The retained lowering log SHA-256 is
`b8e77606bc21d1b1be14841b5bcbc614bb9fced1bd1b851667a86c098f54fd7e`.
The Python reference was tightened to reject a same-inode size change between
the pre-open stat and opened-file fstat, matching the shared reader's snapshot
check. This narrows the prior Python behavior for that race window; a deterministic
regression now mutates the file in place between stat and open and verifies that
the reader reports failure and closes the descriptor. Read-time regressions
also verify that growth is rejected before the extra byte is retained and that a
same-size metadata change is rejected at the intermediate `fstat` checkpoint.
The current source-level contract aligns, but runtime execution and process-output
parity remain unverified. The candidate remains `active_unqualified` and Python remains
authoritative.

## 2026-10-15: refreshed immutable source-runner audit

The latest snapshot is
`../elisa-script/.validation/native/port-build-current3-20261015`, with source
HEAD `854fd6d379c3246829261eeb6e10ab04e83b91ae`, tree SHA-256
`f6b0727b624d562ffd0134f17a6e16274f75ccf90460d5202f03f3c6c5b0710f`, and
manifest SHA-256
`69abed9744112b8a4461eef215c9e3f7c682136b83faa1f2a9dbecc3d4ab5491`. Its
`bin` directory contains no executable. The build stdout is empty; stderr
SHA-256 `f4067b60e1ae126c17f253ba8d20f470882ebb2be519abb2f82c7b9fb9ee213d`
contains 895 compiler diagnostics, including 865 missing `can[Global]` grants
in the runner. Existing executable artifacts are from September or earlier and
are not source-matched. The active candidate still has SHA-256
`94e6820769936d1065ae973919c5a4dac7f3ba7abf903bb271f225cff553f88d`.

The four candidate Python/source checks pass, and an independent source audit
found no concrete mismatch. No candidate-specific runtime execution is
available, so leave this candidate `active_unqualified`, keep Python
authoritative, and do not advance the queue.
