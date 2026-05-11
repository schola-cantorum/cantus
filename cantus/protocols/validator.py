"""Validator — predicate that returns Result(ok, value, feedback).

A validator is how you tell the agent "this output is wrong, here's
why, please retry". Validators run *between* skill calls and the agent
loop turns ValidationError into an Observation that gets fed back.

    @validator
    def ensure_isbn_valid(book: Book) -> Result:
        \"\"\"Verify the ISBN-13 checksum.\"\"\"
        if checksum_ok(book.isbn):
            return Result.success(book)
        return Result.failure("ISBN checksum mismatch — re-check digits.")
"""

from __future__ import annotations

from typing import Any, Callable

from cantus.core.registry import get_registry
from cantus.core.result import Result
from cantus.protocols._common import (
    build_args_model_from_callable,
    first_paragraph,
    pascal,
)

RESERVED_VALIDATOR_NAMES: frozenset[str] = frozenset(
    {"non_empty_final_answer", "action_parse"}
)
"""Validator names reserved by the cantus framework for its built-in
failure-handling pipeline. User-defined validators MUST NOT use these
names; collision raises ValueError at registration time, case-sensitive.
"""


class ReservedValidatorNameError(ValueError):
    """Raised when a user-defined validator collides with a reserved name."""


def _guard_reserved_name(name: str) -> None:
    if name in RESERVED_VALIDATOR_NAMES:
        raise ReservedValidatorNameError(
            f"Validator name {name!r} collides with framework-reserved "
            f"validator vocabulary {sorted(RESERVED_VALIDATOR_NAMES)}; "
            f"choose a different name."
        )


class Validator:
    """Base class for class-first validator definitions."""

    name: str = ""
    description: str = ""

    def __init__(self) -> None:
        if not self.name:
            self.name = type(self).__name__
        if not self.description:
            self.description = first_paragraph((type(self).__doc__ or "").strip())
        self._args_model = build_args_model_from_callable(self.run, self.name)

    def run(self, *args: Any, **kwargs: Any) -> Result:
        raise NotImplementedError("Subclass must implement run()")

    def __call__(self, *args: Any, **kwargs: Any) -> Result:
        out = self.run(*args, **kwargs)
        if not isinstance(out, Result):
            raise TypeError(
                f"Validator {self.name} must return Result, got {type(out).__name__}"
            )
        return out

    def spec_for_llm(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "args_schema": self._args_model.model_json_schema(),
        }


def validator(fn: Callable[..., Result]) -> Validator:
    """Decorator entry: wrap a function as a `Validator` and register it."""
    _guard_reserved_name(fn.__name__)
    instance = _from_function(fn)
    get_registry().register("validator", instance)
    return instance


def register_validator(fn: Callable[..., Result]) -> Validator:
    """Function-pass entry."""
    _guard_reserved_name(fn.__name__)
    instance = _from_function(fn)
    get_registry().register("validator", instance)
    return instance


def _from_function(fn: Callable[..., Result]) -> Validator:
    name = fn.__name__

    def _run(self: Validator, *args: Any, **kwargs: Any) -> Result:
        return type(self)._fn(*args, **kwargs)

    cls_attrs: dict[str, Any] = {
        "name": name,
        "description": first_paragraph((fn.__doc__ or "").strip()),
        "_fn": staticmethod(fn),
        "__doc__": fn.__doc__,
        "run": _run,
    }
    Synthetic = type(pascal(name), (Validator,), cls_attrs)
    instance = Synthetic()
    instance._args_model = build_args_model_from_callable(fn, name)
    return instance
