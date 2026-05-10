"""Result dataclass."""

from cantus.core.result import Result


def test_result_success():
    r = Result(ok=True, value=42)
    assert r.ok is True
    assert r.value == 42
    assert r.feedback is None


def test_result_failure():
    r = Result(ok=False, feedback="ISBN bad")
    assert r.ok is False
    assert r.value is None
    assert r.feedback == "ISBN bad"


def test_result_defaults():
    r = Result(ok=True)
    assert r.ok is True
    assert r.value is None
    assert r.feedback is None


def test_result_helpers():
    s = Result.success(value="abc")
    assert s.ok and s.value == "abc"
    f = Result.failure("oops")
    assert (not f.ok) and f.feedback == "oops"
