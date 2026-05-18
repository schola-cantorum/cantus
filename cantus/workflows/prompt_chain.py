"""PromptChain — run a sequence of Skills, threading output to next input."""

from __future__ import annotations

from typing import Any, Callable, Iterable


class PromptChain:
    """Run Skills in order, where each Skill's output becomes the next one's input.

    Pure Python composition — SHALL NOT touch the runtime registry.

        chain = PromptChain(steps=[outline, draft, polish])
        chain.run("write a haiku about Tainan")
    """

    def __init__(self, steps: Iterable[Callable[..., Any]]) -> None:
        self.steps = list(steps)
        if not self.steps:
            raise ValueError("PromptChain requires at least one step")

    def run(self, input: Any) -> Any:
        out = input
        for step in self.steps:
            out = step(out)
        return out
