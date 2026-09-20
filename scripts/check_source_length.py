"""Enforce the proof assistant's source-file size boundary."""

from pathlib import Path
import sys


MAX_LINES = 600


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    oversized = []
    for path in sorted((root / "src").rglob("*.elisa")):
        lines = sum(1 for _ in path.open(encoding="utf-8"))
        if lines > MAX_LINES:
            oversized.append((lines, path.relative_to(root)))
    if oversized:
        for lines, path in oversized:
            print(f"source file exceeds {MAX_LINES} lines: {path} ({lines})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
