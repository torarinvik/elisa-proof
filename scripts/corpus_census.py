"""Corpus census (BACKLOG A-05): run the checker over read-only real Elisa code (stage1 compiler
modules and Elisa-core sources) and write per-module proved/total counts to docs/census/corpus.md.
Sources are only read. Orchestration only; meant for a nightly run, not the test suite."""
import json
import os
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refusal_census import ROOT, run  # noqa: E402

PROJECTS = ROOT.parent
CORE = PROJECTS.parent / "Go projects/Elisa-core"
DEFAULT_ROOTS = [PROJECTS / "elisa-compiler-worktrees/proofbase/src", CORE / "compiler/runtime/elisacore_std",
                 *sorted(CORE.glob("Code/*/src"))]
OUT = ROOT / "docs/census"


def module_of(path):
    for root in DEFAULT_ROOTS:
        if root in path.parents:
            relative = path.relative_to(root)
            prefix = f"{root.relative_to(PROJECTS.parent)}"
            return f"{prefix}/{relative.parts[0]}" if len(relative.parts) > 1 else prefix
    return str(path.parent)


def main():
    roots = [Path(arg).resolve() for arg in sys.argv[1:]] or [root for root in DEFAULT_ROOTS if root.is_dir()]
    files = sorted(path for root in roots for path in root.rglob("*.elisa"))
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        results = list(pool.map(lambda path: (path, run(path, 60)[1]), files))
    modules = defaultdict(lambda: {"files": 0, "unreadable": 0, "proven": 0, "obligations": 0})
    for path, data in results:
        entry = modules[module_of(path)]
        entry["files"] += 1
        if data is None:
            entry["unreadable"] += 1
            continue
        summary = data.get("summary", {})
        entry["proven"] += summary.get("proven", 0)
        entry["obligations"] += summary.get("obligations", 0)
    proven = sum(entry["proven"] for entry in modules.values())
    total = sum(entry["obligations"] for entry in modules.values())
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "corpus.json").write_text(json.dumps(dict(sorted(modules.items())), indent=1) + "\n")
    lines = ["# Corpus census", "", f"{len(files)} real source files, {proven}/{total} obligations proven.",
             "Unreadable files produced no JSON report within 60 s (parse or import failure, or timeout).", "",
             "| Module | Files | Unreadable | Proven | Obligations |", "| --- | ---: | ---: | ---: | ---: |"]
    lines += [f"| {name} | {e['files']} | {e['unreadable']} | {e['proven']} | {e['obligations']} |"
              for name, e in sorted(modules.items())]
    (OUT / "corpus.md").write_text("\n".join(lines) + "\n")
    print(f"corpus: {proven}/{total} proven across {len(files)} files in {len(modules)} modules")


if __name__ == "__main__":
    main()
