"""@debug — stack on top of any protocol decorator to print a structured trace.

    @debug
    @skill
    def search_book(title: str) -> str: ...

When stacked, every invocation prints `[debug] <name> args=... result=...`
to stdout. The decorator works with any of `Skill`, `Analyzer`,
`Validator`, `Workflow` (and their function-derived synthetic
subclasses). Memory is class-only and not wrapped here; if you want to
trace memory access, override `recall` in your subclass.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from cantus.protocols.analyzer import Analyzer
from cantus.protocols.skill import Skill
from cantus.protocols.validator import Validator
from cantus.protocols.workflow import Workflow

_TRACEABLE = (Skill, Analyzer, Validator, Workflow)


def debug(target: Any) -> Any:
    """Decorator: wrap a registered protocol instance to print a trace on each call.

    Stack on top of `@skill`, `@analyzer`, `@validator`, or `@workflow`:

        @debug
        @skill
        def f(x): ...

    `target` will be the protocol instance returned by the inner
    decorator. We rebind `__call__` to a tracing wrapper.
    """
    if not isinstance(target, _TRACEABLE):
        raise TypeError(
            f"@debug can only wrap a registered protocol "
            f"(Skill, Analyzer, Validator, Workflow); got {type(target).__name__}. "
            f"Make sure @debug is on top: `@debug` then `@skill`."
        )

    original_run = target.run
    spec = target.spec_for_llm() if hasattr(target, "spec_for_llm") else {}
    sys.stdout.write(f"[debug] registered {type(target).__name__} '{target.name}'\n")
    sys.stdout.write(f"[debug] spec={_safe_json(spec)}\n")

    def traced(*args: Any, **kwargs: Any) -> Any:
        thought = kwargs.pop("_debug_thought", "")
        try:
            result = original_run(*args, **kwargs)
        except Exception as exc:
            sys.stdout.write(
                f"[debug] {target.name} thought={thought!r} args={_safe_json(args)}/{_safe_json(kwargs)} "
                f"raised {type(exc).__name__}: {exc}\n"
            )
            raise
        sys.stdout.write(
            f"[debug] {target.name} thought={thought!r} args={_safe_json(args)}/{_safe_json(kwargs)} "
            f"result={_safe_json(result)}\n"
        )
        return result

    # Replace `run` on the instance — __call__ delegates to run().
    target.run = traced  # type: ignore[method-assign]
    target._debug_enabled = True  # type: ignore[attr-defined]
    return target


def _safe_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return repr(obj)
