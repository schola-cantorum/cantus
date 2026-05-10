"""Workflow composes other protocols."""

from cantus.core.registry import get_registry
from cantus.protocols.skill import skill
from cantus.protocols.workflow import Workflow, register_workflow, workflow


def test_decorator_workflow_runs_and_composes_skills():
    @skill
    def double(n: int) -> int:
        """Double."""
        return n * 2

    @skill
    def square(n: int) -> int:
        """Square."""
        return n * n

    @workflow
    def chain(n: int) -> int:
        """Chain double then square."""
        return square(double(n))

    out = chain(3)
    assert out == 36  # (3 * 2) ** 2


def test_class_first_workflow():
    class TwoStep(Workflow):
        """Two-step pipeline."""

        name = "two_step"

        def run(self, x: int) -> int:
            return x + 10

    inst = TwoStep()
    assert inst(5) == 15


def test_function_pass_workflow():
    def add_one(x: int) -> int:
        """Add 1."""
        return x + 1

    inst = register_workflow(add_one)
    assert inst(7) == 8
    assert get_registry().lookup("workflow", "add_one") is inst
