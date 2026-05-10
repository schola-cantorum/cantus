"""Shared reflection helpers for the function-based protocols.

`_first_paragraph`, `_parse_args_block`, `_pascal`, and
`_build_args_model_from_callable` are used by skill / analyzer /
validator / workflow to derive their LLM-facing spec from a plain
Python function.

Memory does not use these — it is class-only.
"""

from __future__ import annotations

import inspect as _inspect
import re
from typing import Any, Callable

from pydantic import create_model


def first_paragraph(text: str) -> str:
    if not text:
        return ""
    blocks = text.strip().split("\n\n")
    return blocks[0].strip()


def parse_args_block(docstring: str) -> dict[str, str]:
    if not docstring:
        return {}
    m = re.search(
        r"^\s*Args:\s*\n(.+?)(?:\n\s*\n|\n\s*(Returns|Raises|Yields):|\Z)",
        docstring,
        re.DOTALL | re.MULTILINE,
    )
    if not m:
        return {}
    body = m.group(1)
    out: dict[str, str] = {}
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        m2 = re.match(r"(\w+)\s*(?:\([^)]*\))?\s*:\s*(.+)", stripped)
        if m2:
            out[m2.group(1)] = m2.group(2).strip()
    return out


def pascal(snake: str) -> str:
    return "".join(part.capitalize() or "_" for part in snake.split("_")) or "Item"


def build_args_model_from_callable(fn: Callable[..., Any], name: str) -> Any:
    sig = _inspect.signature(fn)
    fields: dict[str, Any] = {}
    for pname, param in sig.parameters.items():
        if pname == "self":
            continue
        if param.kind in (
            _inspect.Parameter.VAR_POSITIONAL,
            _inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        annotation = (
            param.annotation if param.annotation is not _inspect.Parameter.empty else Any
        )
        default = param.default if param.default is not _inspect.Parameter.empty else ...
        fields[pname] = (annotation, default)
    model_name = f"{pascal(name)}Args"
    if fields:
        return create_model(model_name, **fields)
    return create_model(model_name)
