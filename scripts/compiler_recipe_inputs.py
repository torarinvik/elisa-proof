"""Read Stage1's recipe inventory from pinned source without executing it."""
import ast
from pathlib import PurePosixPath
import subprocess


def committed_recipe_paths(repository: str, revision: str) -> tuple[str, ...]:
    source = subprocess.run(["git", "-C", repository, "show",
        f"{revision}:scripts/stage1_provenance.py"], check=True,
        capture_output=True, text=True).stdout
    assignments = [node for node in ast.parse(source).body if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "BUILD_RECIPES" for target in node.targets)]
    if len(assignments) != 1:
        raise ValueError("pinned compiler must declare one literal BUILD_RECIPES inventory")
    try:
        paths = ast.literal_eval(assignments[0].value)
    except (ValueError, TypeError) as error:
        raise ValueError("pinned compiler BUILD_RECIPES must be literal") from error
    if not isinstance(paths, tuple) or not 1 <= len(paths) <= 64:
        raise ValueError("pinned compiler BUILD_RECIPES must be a bounded tuple")
    if any(not isinstance(path, str) or not path.startswith("scripts/") or
            ".." in PurePosixPath(path).parts or str(PurePosixPath(path)) != path for path in paths):
        raise ValueError("pinned compiler recipe paths must be canonical script paths")
    if len(set(paths)) != len(paths):
        raise ValueError("pinned compiler recipe paths must be distinct")
    return paths
