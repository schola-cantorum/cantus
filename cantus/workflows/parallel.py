"""Parallel — apply every branch Skill to the same input, collect outputs."""

from __future__ import annotations

from typing import Any, Callable, Iterable


class Parallel:
    """Fan out the same input to multiple Skills and gather their results in order.

    Pure Python composition — SHALL NOT touch the runtime registry. Execution is
    sequential under v0.3.0; concurrency (asyncio / threads) is a host concern.

        fanout = Parallel(branches=[summarize_en, summarize_zh])
        fanout.run("Long article...")  # → [en_summary, zh_summary]
    """

    def __init__(self, branches: Iterable[Callable[..., Any]]) -> None:
        self.branches = list(branches)
        if not self.branches:
            raise ValueError("Parallel requires at least one branch")

    def run(self, input: Any) -> list[Any]:
        return [branch(input) for branch in self.branches]
