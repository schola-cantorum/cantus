"""Analyzer — parses unstructured text into a typed value.

Use an analyzer when you need the agent to convert a string the LLM
produced into a Pydantic / dataclass instance. The return type
annotation is the contract.

    @analyzer
    def parse_book_list(text: str) -> list[Book]:
        \"\"\"Parse a numbered list into Book objects.\"\"\"
        ...
"""

from __future__ import annotations

from typing import Any, Callable

from cantus.core.registry import get_registry
from cantus.protocols._common import (
    build_args_model_from_callable,
    first_paragraph,
    pascal,
)


class Analyzer:
    """Base class for class-first analyzer definitions."""

    name: str = ""
    description: str = ""

    def __init__(self) -> None:
        if not self.name:
            self.name = type(self).__name__
        if not self.description:
            self.description = first_paragraph((type(self).__doc__ or "").strip())
        self._args_model = build_args_model_from_callable(self.run, self.name)

    def run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Subclass must implement run()")

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.run(*args, **kwargs)

    def spec_for_llm(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "args_schema": self._args_model.model_json_schema(),
        }


def analyzer(fn: Callable[..., Any]) -> Analyzer:
    """Decorator entry: wrap a function as an `Analyzer` and register it."""
    instance = _from_function(fn)
    get_registry().register("analyzer", instance)
    return instance


def register_analyzer(fn: Callable[..., Any]) -> Analyzer:
    """Function-pass entry."""
    instance = _from_function(fn)
    get_registry().register("analyzer", instance)
    return instance


def _from_function(fn: Callable[..., Any]) -> Analyzer:
    name = fn.__name__

    def _run(self: Analyzer, *args: Any, **kwargs: Any) -> Any:
        return type(self)._fn(*args, **kwargs)

    cls_attrs: dict[str, Any] = {
        "name": name,
        "description": first_paragraph((fn.__doc__ or "").strip()),
        "_fn": staticmethod(fn),
        "__doc__": fn.__doc__,
        "run": _run,
    }
    Synthetic = type(pascal(name), (Analyzer,), cls_attrs)
    instance = Synthetic()
    instance._args_model = build_args_model_from_callable(fn, name)
    return instance
