"""Validator returns Result(ok, value, feedback)."""

import pytest

from cantus.core.result import Result
from cantus.protocols.validator import Validator, register_validator, validator


def _isbn13_ok(isbn: str) -> bool:
    digits = [int(c) for c in isbn if c.isdigit()]
    if len(digits) != 13:
        return False
    s = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits))
    return s % 10 == 0


def test_decorator_validator_pass_and_fail():
    @validator
    def ensure_isbn(isbn: str) -> Result:
        """Verify ISBN-13 checksum."""
        if _isbn13_ok(isbn):
            return Result.success(isbn)
        return Result.failure(f"checksum invalid for {isbn}")

    good = ensure_isbn("9780553293357")
    assert good.ok and good.value == "9780553293357"

    bad = ensure_isbn("9780000000000")
    assert not bad.ok and "checksum invalid" in bad.feedback


def test_validator_must_return_result():
    @validator
    def bad(_x: str) -> Result:
        """Doesn't return Result."""
        return "wrong"  # type: ignore[return-value]

    with pytest.raises(TypeError):
        bad("anything")


def test_function_pass_validator():
    def v(n: int) -> Result:
        """Even check."""
        return Result.success() if n % 2 == 0 else Result.failure("odd")

    inst = register_validator(v)
    assert inst(2).ok
    assert not inst(3).ok


def test_class_first_validator():
    class EnsurePositive(Validator):
        """Positive int check."""

        name = "ensure_positive"

        def run(self, n: int) -> Result:
            return Result.success(n) if n > 0 else Result.failure("must be positive")

    inst = EnsurePositive()
    assert inst(5).ok
    assert not inst(-1).ok


# --- Hook helper (v0.3.0): no registry side-effect ----------------------


def test_decorator_validator_no_registry_entry():
    """v0.3.0: @validator SHALL NOT mutate the runtime registry."""
    from cantus.core.registry import get_registry

    @validator
    def is_positive(n: int) -> Result:
        """Positive check."""
        return Result.success(n) if n > 0 else Result.failure("not positive")

    reg = get_registry()
    for kind in ("skill", "analyzer", "validator", "workflow"):
        assert "is_positive" not in reg.names_for(kind)


def test_register_validator_no_registry_entry():
    """v0.3.0: register_validator() SHALL NOT mutate the runtime registry."""
    from cantus.core.registry import get_registry

    def v(n: int) -> Result:
        """Even."""
        return Result.success() if n % 2 == 0 else Result.failure("odd")

    register_validator(v)
    reg = get_registry()
    for kind in ("skill", "analyzer", "validator", "workflow"):
        assert "v" not in reg.names_for(kind)


def test_reserved_validator_name_still_guards():
    """v0.3.0: dropping registry side-effect SHALL NOT weaken the reserved-name guard."""
    from cantus.protocols.validator import ReservedValidatorNameError

    with pytest.raises(ReservedValidatorNameError):

        @validator
        def non_empty_final_answer(value: str) -> Result:  # reserved name
            """Should be rejected."""
            return Result.success(value)
