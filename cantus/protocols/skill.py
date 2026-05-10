"""Skill — a callable capability the LLM agent can invoke (tool-style).

Three entry styles all converge to a `Skill` instance registered in the
registry under `kind="skill"`:

    @skill                                  # decorator entry (most common)
    def search_book(title: str) -> str:
        \"\"\"Search the library catalog.\"\"\"
        ...

    register_skill(search_book)             # function-pass entry

    class SearchBook(Skill):                # class-first canonical
        description = "Search the library catalog."
        def run(self, title: str) -> str: ...

The Pydantic schema for the skill's `args` is derived from the function
signature (or `run` for class-first). The description comes from the
docstring (or the `description` class attribute for class-first).
"""

from __future__ import annotations

from typing import Any, Callable

from cantus.core.registry import get_registry
from cantus.protocols._common import (
    build_args_model_from_callable,
    first_paragraph,
    parse_args_block,
    pascal,
)


class Skill:
    """Base class for class-first skill definitions."""

    name: str = ""
    description: str = ""

    def __init__(self) -> None:
        if not self.name:
            self.name = type(self).__name__
        if not self.description:
            doc = (type(self).__doc__ or "").strip()
            self.description = first_paragraph(doc)
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

    def validate_args(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._args_model(**args).model_dump()


def skill(fn: Callable[..., Any]) -> Skill:
    """Decorator entry: wrap a plain function as a `Skill` and register it."""
    instance = _from_function(fn)
    get_registry().register("skill", instance)
    return instance


def register_skill(fn: Callable[..., Any]) -> Skill:
    """Function-pass entry: same as `@skill` but called explicitly."""
    instance = _from_function(fn)
    get_registry().register("skill", instance)
    return instance


def _from_function(fn: Callable[..., Any]) -> Skill:
    name = fn.__name__
    description = first_paragraph((fn.__doc__ or "").strip())
    args_descriptions = parse_args_block(fn.__doc__ or "")

    def _run(self: Skill, *args: Any, **kwargs: Any) -> Any:
        return type(self)._fn(*args, **kwargs)

    cls_attrs: dict[str, Any] = {
        "name": name,
        "description": description,
        "_fn": staticmethod(fn),
        "__doc__": fn.__doc__,
        "_args_descriptions": args_descriptions,
        "run": _run,
    }
    SyntheticSkill = type(pascal(name), (Skill,), cls_attrs)
    instance = SyntheticSkill()
    instance._args_model = build_args_model_from_callable(fn, name)
    return instance
