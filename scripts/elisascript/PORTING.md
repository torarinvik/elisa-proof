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
| `scripts/test_report_output_loop_layout.py` | `scripts/test_report_output_loop_layout.elisascript` | Active source port, colocated with its Python reference. The candidate uses the shared bounded UTF-8 reader and checks four fixed fragments with `contains`. The source parity guard pins repository-root derivation, fragments, diagnostics, strict UTF-8, byte/path bounds, and file mutation checks. Runtime parity remains unqualified; retain Python. |
| `scripts/test_global_mutable_array_owner_identity.py` | queued | No candidate promoted until the active port has parity evidence. |
| `scripts/test_resource_call_storage_confinement_static.py` | queued | No candidate promoted until the active port has parity evidence. |

## Qualification record (2026-10-15)

The Python reference exits 0 and prints the expected success line. The installed
runner and retained native binaries identify as version 0.1 and predate this
source. An earlier nested-module draft failed with `UnsupportedDeclaration`.
After relocation under `elisa-proof/scripts` and correction of the
source-root path, the old candidate using `Path.read_text()` caused the rebuilt
runner to exit 138 without diagnostics. The current candidate uses the bounded
reader, but retained v0.1 runners reject its included `EsBoundedText` name during
`--check`. No ElisaScript runtime parity has been established. Keep the Python
reference in place.

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

The current candidate is SHA-256
`23069ad02a7fbeeb6edcb4a05924b42169696419cde791b2453493e6eb449380`. The Python reference
passes and its source hash remains
`55fe791691f426fdacba65b18311906c532e0c38c432d9bb74b349bcd95c2475`. A direct installed-runner
`--check` against the current candidate still exits 1 at line 40 with
`undefined identifier "EsBoundedText"`.

An additional bounded Core test fixture was added at
`../elisa-script/test/ir/elisascript_read_text_utf8_test.elisascript` for strict text decoding.
The shared execution facade test attempt exited 1 before test execution (438,112 KiB sampled
peak RSS; no watchdog trip). The pinned Core compiler reports parser incompatibilities in the
current checkout, including `src/ir/interpret.elisa:349`, `src/ir/lower_ast.elisa:9828`, and
vendored runtime/test modules. It reports no diagnostics at the new UTF-8 validator or focused
fixture. The compiler test therefore does not qualify the change.

The interpreter's `read_text` path now validates strict UTF-8 and reports malformed input as
`FileIoError`, matching Python's default text decoder; `read_bytes` remains the binary API. The
source parity guard pins this rule and the existing `EsBoundedText` reader's UTF-8, 16 MiB source,
4 KiB path, stable-file, and bounded-retry contracts. The strict-read change is unqualified until
the current interpreter can be built and the focused fixture runs. Runtime parity for the active
port remains unqualified; keep the Python reference authoritative.
