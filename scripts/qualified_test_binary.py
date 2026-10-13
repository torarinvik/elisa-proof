"""Select the proof product only after current source/toolchain qualification."""

import json
import os
from pathlib import Path
import subprocess


def _same_path(left: str, right: str) -> bool:
    try:
        return Path(left).resolve() == Path(right).resolve()
    except (OSError, RuntimeError) as error:
        raise SystemExit(f"cannot resolve proof product path: {error}") from error


def proof_test_binary(root: Path) -> str:
    configured = os.environ.get("ELISA_PROOF_BIN")
    matrix_qualified = os.environ.get("ELISA_PROOF_QUALIFIED_BIN")
    if matrix_qualified:
        if not configured or not _same_path(matrix_qualified, configured):
            raise SystemExit("test-matrix qualification path does not match ELISA_PROOF_BIN")
        return configured

    qualified = subprocess.run(
        ["bash", str(root / "scripts/qualify_prebuilt_test.sh"), "--json"],
        cwd=root, capture_output=True, text=True, timeout=120,
    )
    if qualified.returncode:
        raise SystemExit(
            "proof regression refused an unqualified binary; current product qualification "
            f"failed:\n{qualified.stdout}{qualified.stderr}"
        )
    try:
        product = json.loads(qualified.stdout)
        exact_binary = product["proof_binary"] if isinstance(product, dict) else None
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise SystemExit(f"proof product qualification returned malformed JSON: {error}") from error
    if not isinstance(exact_binary, str) or not exact_binary:
        raise SystemExit("proof product qualification did not return a proof binary path")
    if configured and not _same_path(configured, exact_binary):
        raise SystemExit(
            f"ELISA_PROOF_BIN is not the current qualified product: {configured} != {exact_binary}"
        )
    return exact_binary
