"""Tool — a callable capability the LLM agent can invoke.

Three entry styles all converge to a `Tool` instance:

    @tool                                   # decorator entry (does not register)
    def search_book(title: str) -> str:
        \"\"\"Search the library catalog.\"\"\"
        ...

    register_tool(search_book, registry=reg)    # function-pass entry (registers)

    class SearchBook(Tool):                 # class-first canonical
        description = "Search the library catalog."
        def run(self, title: str) -> str: ...

`@tool` and `tool(fn)` build a Tool and return it; they never register it.
Registration is an explicit step: `register_tool(fn, registry=reg)`.

The Pydantic schema for the tool's `args` is derived from the function
signature (or `run` for class-first). The description comes from the
docstring (or the `description` class attribute for class-first).
"""

from __future__ import annotations

from typing import Any, Callable

from cantus.core.registry import Registry
from cantus.protocols._common import (
    build_args_model_from_callable,
    first_paragraph,
    parse_args_block,
    pascal,
)


class Tool:
    """A callable the model can ask the agent to invoke.

    Subclass it for the class-first style: set ``description`` (or write a
    class docstring) and implement ``run``. ``@tool`` builds an instance from
    a plain function instead.

    Attributes:
        name: The name the model uses to call the tool. Defaults to the class
            name.
        description: What the tool does, shown to the model. Defaults to the
            first paragraph of the class docstring.
        is_remote: True for tools imported from another framework or an MCP
            server.

    Args:
        pre_hook: Called with the validated arguments before ``run`` when an
            ``Agent`` dispatches the tool.
        post_hook: Called with the result of ``run`` when an ``Agent``
            dispatches the tool.
    """

    name: str = ""
    description: str = ""
    # v0.3.2: provenance marker so callers (Inspector, log, adapter audit)
    # can distinguish locally-defined Tools from MCP-imported remote Tools.
    # `cantus.adapters.import_mcp_server` returns Tool subclasses with
    # `is_remote = True`; bare `@tool` / class-first Tools stay False.
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
        """Do the tool's work. Subclasses implement this; hooks do not run here."""
        raise NotImplementedError("Subclass must implement run()")

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.run(*args, **kwargs)

    def spec_for_llm(self) -> dict[str, Any]:
        """Describe the tool for the model.

        Returns:
            A dict with exactly ``name``, ``description`` and ``args_schema``
            (the JSON schema of the arguments).
        """
        schema: dict[str, Any] = self._args_model.model_json_schema()
        return {
            "name": self.name,
            "description": self.description,
            "args_schema": schema,
        }

    def validate_args(self, args: dict[str, Any]) -> dict[str, Any]:
        """Validate and coerce arguments against the tool's schema.

        Args:
            args: The arguments the model supplied.

        Returns:
            The arguments after validation and type coercion.
        """
        dumped: dict[str, Any] = self._args_model(**args).model_dump()
        return dumped


def _from_function(
    fn: Callable[..., Any],
    pre_hook: Callable[..., Any] | None = None,
    post_hook: Callable[..., Any] | None = None,
) -> Tool:
    """Wrap a plain function as a new Tool with the given hooks.

    The one wrapping routine behind ``tool`` and ``register_tool``; the legacy
    entry points build on it too.
    """
    name = fn.__name__
    description = first_paragraph((fn.__doc__ or "").strip())
    args_descriptions = parse_args_block(fn.__doc__ or "")

    def _run(self: Tool, *args: Any, **kwargs: Any) -> Any:
        return type(self)._fn(*args, **kwargs)  # type: ignore[attr-defined]

    cls_attrs: dict[str, Any] = {
        "name": name,
        "description": description,
        "_fn": staticmethod(fn),
        "__doc__": fn.__doc__,
        "_args_descriptions": args_descriptions,
        "run": _run,
    }
    SyntheticTool = type(pascal(name), (Tool,), cls_attrs)
    instance: Tool = SyntheticTool()
    instance._args_model = build_args_model_from_callable(fn, name)
    instance._pre_hook = pre_hook
    instance._post_hook = post_hook
    return instance


def tool(
    fn: Callable[..., Any] | None = None,
    *,
    pre_hook: Callable[..., Any] | None = None,
    post_hook: Callable[..., Any] | None = None,
) -> Tool | Callable[[Callable[..., Any]], Tool]:
    """Turn a function into a `Tool`. Does not register it anywhere.

    Use it bare (``@tool``), with hooks (``@tool(pre_hook=...)``) or as a call
    (``tool(fn)``), then pass the result to an agent or a ``Registry``.

    Args:
        fn: The function to wrap. Its name, docstring and signature become the
            tool's name, description and argument schema. An existing `Tool`
            is returned as it is. Omit it to get a decorator.
        pre_hook: Called with the validated arguments before the function when
            an ``Agent`` dispatches the tool.
        post_hook: Called with the function's result when an ``Agent``
            dispatches the tool.

    Returns:
        The `Tool`, or a decorator that builds one when ``fn`` is omitted.

    Raises:
        TypeError: If ``fn`` is not callable, is a `Tool` subclass instead of
            an instance, or is an existing `Tool` and a hook is also given.
    """
    if fn is None:

        def decorator(actual_fn: Callable[..., Any]) -> Tool:
            return _to_tool(actual_fn, pre_hook, post_hook)

        return decorator
    return _to_tool(fn, pre_hook, post_hook)


def _to_tool(
    fn: Any,
    pre_hook: Callable[..., Any] | None,
    post_hook: Callable[..., Any] | None,
) -> Tool:
    """Shared by `tool` and `register_tool`: validate, then wrap or pass through."""
    if isinstance(fn, Tool):
        if pre_hook is not None or post_hook is not None:
            raise TypeError(
                "got a Tool together with pre_hook/post_hook; hooks are set "
                "when the Tool is created, so pass them there"
            )
        return fn
    if isinstance(fn, type) and issubclass(fn, Tool):
        raise TypeError(
            f"got the class {fn.__name__}; pass an instance: {fn.__name__}()"
        )
    if not callable(fn):
        raise TypeError(
            f"expected a function or a Tool, got {type(fn).__name__}"
        )
    return _from_function(fn, pre_hook, post_hook)


def register_tool(
    fn: Any,
    *,
    registry: Registry,
    pre_hook: Callable[..., Any] | None = None,
    post_hook: Callable[..., Any] | None = None,
) -> Tool:
    """Build a `Tool` from a function, or take an existing one, and add it to ``registry``.

    A tool already in ``registry`` under the same name is replaced.

    Args:
        fn: The function to wrap, or an existing `Tool`.
        registry: The ``Registry`` to add the tool to. Required, keyword-only.
        pre_hook: Called with the validated arguments before the function when
            an ``Agent`` dispatches the tool.
        post_hook: Called with the function's result when an ``Agent``
            dispatches the tool.

    Returns:
        The `Tool` that was added.

    Raises:
        TypeError: If ``registry`` is not a ``Registry``, or for the same
            inputs `tool` rejects. Nothing is added in that case.
    """
    if not isinstance(registry, Registry):
        raise TypeError(
            f"register_tool() needs registry=<Registry>, got {type(registry).__name__}"
        )
    the_tool = _to_tool(fn, pre_hook, post_hook)
    registry.register(Registry.KINDS[0], the_tool)
    return the_tool


__all__ = ["Tool", "tool", "register_tool"]
