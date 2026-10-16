# Proof source-length checker parity

The reference is the proof repository's own
[`scripts/check_source_length.py`](../../../../scripts/check_source_length.py).
`reference.py` is an unchanged fixture snapshot with SHA-256
`8a5142e1c3c82db4f21668e9e9dcdc3dd8acae2452fcba73cb3f3278a7f18996`.
The gated launcher checks that the live Python file and snapshot retain this
identity before and after a parity matrix.

The adjacent port is [`scripts/check_source_length.elisascript`](../../../../scripts/check_source_length.elisascript),
currently SHA-256 `ad5526a1d577b9490fb9ed8eb28fc343111b8a6804a8b78c17524ad5e0288a09`.
It uses the shared streaming UTF-8 and universal-newline reader from the
neighboring `elisa-script` checkout. The port resolves its project root from
its own real script path, like `Path(__file__).resolve().parents[1]`.

## Ordinary-tree behavior

The Python checker scans these groups in order, sorting paths within each
group:

1. `src/**/*.elisa`
2. `scripts/**/*.sh`
3. `scripts/**/*.py`
4. `test/**/*.py`
5. `examples/**/*.elisa`

For each path, Python text iteration with UTF-8 decoding counts universal
newlines. CRLF is one newline; LF and bare CR are newlines; an unterminated
nonempty final segment is one line; an empty file is zero lines. Invalid UTF-8
raises. Files over 600 lines produce status 1, empty stdout, and one stderr
line per file in grouped order:

```text
file exceeds 600 lines: <project-relative-path> (<line-count>)
```

Otherwise the checker exits 0 without output. Extra command-line arguments are
ignored. Suffix matching is case-sensitive, hidden paths are included, file
symlinks are opened, and descendant directory symlinks are not traversed.
`Path.rglob`/`Path.glob` error behavior is not claimed as exact parity by the
port: its filesystem and UTF-8 failures return status 2 with a concise
candidate diagnostic instead of Python's traceback and status 1. Such host and
invalid-input cases are excluded from ordinary parity acceptance and need a
separate policy decision. The shared reader uses the current Darwin POSIX
adapter; cross-platform execution has not been qualified.

## Authored parity fixture

`test/script_parity/source_length_launcher_test.elisascript` stages isolated
`elisa-proof` and `elisa-script` sibling trees, then compares Python and the
public ElisaScript launcher from `/`. It checks empty/missing/non-directory
`src`, a symlinked `src`, line-count boundaries and newline forms, hidden and
Unicode source names, component-wise path order, file symlinks, a descendant
directory-symlink cycle, traversal deeper than 64 directories, and the four
additional glob groups including within-group sorting and cross-group order.
Literal expected output is independent fixture data in
`test/script_parity/source_length_cases.elisa` and the launcher matrix. A pure
ordering assertion lives in `test/script_parity/source_length_order_test.elisascript`.

The launcher requires explicit reauthorization, the bounded test RSS marker,
and pinned compiler, Python, launcher, source, and dependency identities before
starting a child process. It is dormant; no runtime parity matrix was run, per
the lower-only validation choice. Authored assertions and source review do not
establish runtime parity.

The candidate source passed bounded lowering on 2026-10-15 with compiler
revision `f7219491633164caeac2a909ae04309e01b38a19` (binary SHA-256
`faa6cd9f55223b18c12908c52d5937d929015291c7607f2ae135b25f54d06c31`), exit 0,
and sampled peak RSS 33,712 KiB. Its retained log is
`elisa-script/.validation/22f5d214aac8b6b06506024d4d38856d6b10795f29175584aa97bcae85c45dd8/logs/lowering.o9PqSY`.
The literal case data also lowered with exit 0; its process ended before the
RSS sampler recorded a sample. Its log is
`.../logs/lowering.5U1g9l`. The component-order fixture lowered with exit 0
and sampled peak RSS 35,536 KiB; its log is `.../logs/lowering.EkK69r` in the
same validation directory. These lowerings check parsing, include resolution,
and compiler lowering only; they do not run the checker or assertions. The
retargeted public launcher matrix has not been lowered or run.
