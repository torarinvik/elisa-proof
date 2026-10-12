"""JSON readers for provenance and build metadata with duplicate-key rejection."""

from __future__ import annotations

import json
from typing import TextIO


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise ValueError(f"non-standard JSON numeric constant: {value}")


def loads(raw: str | bytes) -> object:
    return json.loads(
        raw,
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )


def load(stream: TextIO) -> object:
    return json.load(
        stream,
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )
