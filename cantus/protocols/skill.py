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
    # v0.3.2: provenance marker so callers (Inspector, log, adapter audit)
    # can distinguish locally-defined Skills from MCP-imported remote Skills.
    # `cantus.adapters.import_mcp_server` returns Skill subclasses with
    # `is_remote = True`; bare `@skill` / class-first Skills stay False.
    is_remote: bool = False

    def __init__(
        self,
        *,
        pre_hook: Callable[..., Any] | None = None,
        post_hook: Callable[..., Any] | None = None,
    ) -> None:
        if not self.name:
            self.name = type(self).__name__
        if not self.description:
            doc = (type(self).__doc__ or "").strip()
            self.description = first_paragraph(doc)
        self._args_model = build_args_model_from_callable(self.run, self.name)
        self._pre_hook = pre_hook
        self._post_hook = post_hook

    def run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Subclass must implement run()")

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.run(*args, **kwargs)

    def spec_for_llm(self) -> dict[str, Any]:
        schema: dict[str, Any] = self._args_model.model_json_schema()
        return {
            "name": self.name,
            "description": self.description,
            "args_schema": schema,
        }

    def validate_args(self, args: dict[str, Any]) -> dict[str, Any]:
        dumped: dict[str, Any] = self._args_model(**args).model_dump()
        return dumped


def skill(
    fn: Callable[..., Any] | None = None,
    *,
    pre_hook: Callable[..., Any] | None = None,
    post_hook: Callable[..., Any] | None = None,
) -> Skill | Callable[[Callable[..., Any]], Skill]:
    """Decorator entry: wrap a plain function as a `Skill` and register it.

    Supports both bare `@skill` and `@skill(pre_hook=..., post_hook=...)`.
    """
    if fn is None:
        def decorator(actual_fn: Callable[..., Any]) -> Skill:
            return _build_and_register(actual_fn, pre_hook, post_hook)
        return decorator
    return _build_and_register(fn, pre_hook, post_hook)


def register_skill(
    fn: Callable[..., Any],
    *,
    pre_hook: Callable[..., Any] | None = None,
    post_hook: Callable[..., Any] | None = None,
) -> Skill:
    """Function-pass entry: same as `@skill` but called explicitly."""
    return _build_and_register(fn, pre_hook, post_hook)


def _build_and_register(
    fn: Callable[..., Any],
    pre_hook: Callable[..., Any] | None,
    post_hook: Callable[..., Any] | None,
) -> Skill:
    instance = _from_function(fn)
    instance._pre_hook = pre_hook
    instance._post_hook = post_hook
    get_registry().register("skill", instance)
    return instance


def _from_function(fn: Callable[..., Any]) -> Skill:
    name = fn.__name__
    description = first_paragraph((fn.__doc__ or "").strip())
    args_descriptions = parse_args_block(fn.__doc__ or "")

    def _run(self: Skill, *args: Any, **kwargs: Any) -> Any:
        return type(self)._fn(*args, **kwargs)  # type: ignore[attr-defined]

    cls_attrs: dict[str, Any] = {
        "name": name,
        "description": description,
        "_fn": staticmethod(fn),
        "__doc__": fn.__doc__,
        "_args_descriptions": args_descriptions,
        "run": _run,
    }
    SyntheticSkill = type(pascal(name), (Skill,), cls_attrs)
    instance: Skill = SyntheticSkill()
    instance._args_model = build_args_model_from_callable(fn, name)
    return instance
