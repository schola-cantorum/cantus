"""EvaluatorOptimizer — generator/evaluator loop until evaluator approves."""

from __future__ import annotations

from typing import Any, Callable

from cantus.core.result import Result


class EvaluatorOptimizer:
    """Generator-then-evaluator loop, capped at `max_iters` iterations.

    On each iteration:
      1. `generator(input)` → candidate
      2. `evaluator(candidate)` → `Result` (or truthy value)
      3. If `Result(ok=True)`, return `result.value` if present, else the candidate.
         If `Result(ok=False)`, retry with the same input.
         If the evaluator returns a non-`Result` truthy value, return the candidate.

    If `max_iters` runs are exhausted without approval, the last candidate is
    returned regardless. Pure Python composition — SHALL NOT touch the registry.

        eo = EvaluatorOptimizer(generator=draft, evaluator=critique, max_iters=3)
        eo.run("Argue for solar over wind")
    """

    def __init__(
        self,
        generator: Callable[[Any], Any],
        evaluator: Callable[[Any], Any],
        max_iters: int = 3,
    ) -> None:
        if max_iters < 1:
            raise ValueError("max_iters must be >= 1")
        self.generator = generator
        self.evaluator = evaluator
        self.max_iters = max_iters

    def run(self, input: Any) -> Any:
        candidate: Any = None
        for _ in range(self.max_iters):
            candidate = self.generator(input)
            verdict = self.evaluator(candidate)
            if isinstance(verdict, Result):
                if verdict.ok:
                    return verdict.value if verdict.value is not None else candidate
            elif verdict:
                return candidate
        return candidate
