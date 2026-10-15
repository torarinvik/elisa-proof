# ElisaScript script ports

The Python versions remain authoritative until each ElisaScript counterpart has
been compiled and run against the same input, with matching exit status and
output. Migrate and qualify one script at a time.

| Python reference | ElisaScript counterpart | Status |
| --- | --- | --- |
| `scripts/test_report_output_loop_layout.py` | `scripts/elisascript/test_report_output_loop_layout.elisascript` | Active source port. It reads the same source file through the shared UTF-8 reader with a 16 KiB limit, normalizes universal newlines with `sview.replace`, and checks the same four fragments with `sview.index`. The installed ElisaScript runner cannot currently qualify it; retain Python. |
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

The candidate also used an unsupported `Path.read_text()` call. It now uses the
shared `EsBoundedText::read_utf8` API with a 16 KB cap for the 4.5 KB target file.
The retained v0.1 runners reject the imported `EsBoundedText` name, so this
candidate remains unqualified; the Python reference remains authoritative.
The source comparison uses `.index()` as used by the shared ElisaScript source
helpers. The 16 KiB cap differs from Python's unbounded `read_text()`, and
missing-file or missing-fragment diagnostics differ: Python emits a traceback,
while the candidate writes a concise message. These cases need an explicit parity
decision and runtime qualification before replacing Python.
