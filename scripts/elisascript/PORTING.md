# ElisaScript script ports

The Python versions remain authoritative until each ElisaScript counterpart has
been compiled and run against the same input, with matching exit status and
output. Migrate and qualify one script at a time.

Proof-specific ElisaScript ports and their tests stay in this repository. The
sibling `elisa-script` repository is for general-purpose language, runtime, and
tooling work; do not put Elisa-Proof scripts there.

| Python reference | ElisaScript counterpart | Status |
| --- | --- | --- |
| `scripts/test_report_output_loop_layout.py` | `scripts/elisascript/test_report_output_loop_layout.elisascript` | Active source port. `scripts/test_elisascript_report_output_port_parity.py` pins their repository-root path derivation, fragments, diagnostics, strict UTF-8, byte/path bounds, full-precision file mutation checks, file-size-aware reader and content-buffer sizing, and universal newline normalization. Runtime parity remains unqualified; retain Python. |
| `scripts/test_global_mutable_array_owner_identity.py` | queued | No candidate promoted until the active port has parity evidence. |
| `scripts/test_resource_call_storage_confinement_static.py` | queued | No candidate promoted until the active port has parity evidence. |

## Qualification record (2026-10-15)

The Python reference exits 0 and prints the expected success line. The installed
runner and retained native binaries identify as version 0.1 and predate this
source. An earlier nested-module draft failed with `UnsupportedDeclaration`.
After relocation under `elisa-proof/scripts/elisascript` and correction of the
source-root path, the old candidate using `Path.read_text()` caused the rebuilt
runner to exit 138 without diagnostics. The current candidate uses the bounded
reader, but retained v0.1 runners reject its included `EsBoundedText` name during
`--check`. No ElisaScript runtime parity has been established. Keep the Python
reference in place.

The candidate previously used an unsupported `Path.read_text()` call. It now
uses the shared `EsBoundedText::read_utf8` API with the reader's 16 MiB maximum;
the Python reference now applies the same bound with a nonblocking descriptor.
Both readers require a regular file, verify device/inode identity when opening,
and compare identity, size, modification time, and change time after reading.
Both require strict UTF-8 and normalize CRLF and CR line endings. Python checks
fragments with `in`; ElisaScript uses caught `sview.index`, which raises when a
fragment is missing. Both enforce the same 16 MiB source and 4096-byte path caps,
route missing fragments and read failures through the same diagnostics, and print
the same success line. These behaviors match by source review, including the
bounded file checks. Runtime parity remains unqualified:
the retained v0.1 runners reject the imported `EsBoundedText` name, and the
sibling ElisaScript repository's `docs/development.md` suspends compiler and
test-wrapper launches until validation is explicitly reauthorized in the active
task. A source review also found that the shared reader returned a view into its
local byte array; it now copies validated text into permanent backing storage
before returning. Python remains authoritative until compile/run parity is
established.
