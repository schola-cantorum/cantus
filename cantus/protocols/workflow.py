"""Workflow — multi-step orchestration that composes other protocols.

A workflow is just a Python function (or class with `run`) that calls
registered skills, analyzers, and validators. The framework records
those calls into the EventStream automatically when the workflow runs
inside `agent.run()`.

    @workflow
    def recommend_books(query: str) -> list[Book]:
        candidates = search_book(query)
        parsed = parse_book_list(candidates)
        return [b for b in parsed if ensure_isbn_valid(b).ok]
"""

from __future__ import annotations

from typing import Any, Callable

from cantus.core.registry import get_registry
from cantus.protocols._common import (
    build_args_model_from_callable,
    first_paragraph,
    pascal,
)


class Workflow:
    """Base class for class-first workflow definitions."""

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


def workflow(fn: Callable[..., Any]) -> Workflow:
    """Decorator entry: wrap a function as a `Workflow` and register it."""
    instance = _from_function(fn)
    get_registry().register("workflow", instance)
    return instance


def register_workflow(fn: Callable[..., Any]) -> Workflow:
    """Function-pass entry."""
    instance = _from_function(fn)
    get_registry().register("workflow", instance)
    return instance


def _from_function(fn: Callable[..., Any]) -> Workflow:
    name = fn.__name__

    def _run(self: Workflow, *args: Any, **kwargs: Any) -> Any:
        return type(self)._fn(*args, **kwargs)

    cls_attrs: dict[str, Any] = {
        "name": name,
        "description": first_paragraph((fn.__doc__ or "").strip()),
        "_fn": staticmethod(fn),
        "__doc__": fn.__doc__,
        "run": _run,
    }
    Synthetic = type(pascal(name), (Workflow,), cls_attrs)
    instance = Synthetic()
    instance._args_model = build_args_model_from_callable(fn, name)
    return instance
