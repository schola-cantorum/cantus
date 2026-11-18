"""v0.2 -> v0.3 migration smoke whose subject is the legacy form `@skill(pre_hook=...)`.

Moved out of tests/test_integration_smoke.py by T-0010: the script binds a hook with the
legacy decorator and runs an Agent without tools=, so it belongs with the legacy tests.
The subprocess isolation matches the rest of that file's pattern.
"""

from __future__ import annotations

import subprocess
import sys


def _run_in_fresh_subprocess(script: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_v0_1_example_runs_after_migration():
    """v0.2 → v0.3 migration smoke: hook-bound skill + PromptChain reach FinalAnswerAction.

    Extends ARCH-2 integration smoke audit row to cover the protocol-reorg surface:
    `cantus.hooks` import, `@skill(pre_hook=...)` binding, and `cantus.workflows`
    building blocks must coexist with the existing Agent loop. Subprocess isolation
    matches the rest of this file's pattern.
    """
    script = """
import json
from dataclasses import dataclass

from cantus import Agent, skill
from cantus.hooks import analyzer
from cantus.workflows import PromptChain
from cantus.core.action import FinalAnswerAction


@analyzer
def parse_query(text: str) -> dict:
    return {"value": text}


@skill(pre_hook=parse_query)
def echo(value: str) -> str:
    "Echo the input back to the caller."
    return value


# Pure-Python building block — does not register itself into the runtime registry.
chain = PromptChain(steps=[echo])
assert chain.run("hello") == "hello"


@dataclass
class _ImmediateFinalizer:
    answer: str = "v0.3 migration ok"

    def generate(self, prompt, **kwargs):
        return json.dumps({"thought": "done", "action": {"final_answer": self.answer}})


agent = Agent(model=_ImmediateFinalizer())
state = agent.run("smoke", max_iterations=3)
final = state.stream[-1]
assert isinstance(final, FinalAnswerAction), type(final).__name__
print("FinalAnswerAction emitted:", final.answer)
"""
    code, out, err = _run_in_fresh_subprocess(script)
    assert code == 0, f"subprocess failed: stdout={out!r} stderr={err!r}"
    assert "FinalAnswerAction" in out, f"FinalAnswerAction not in stdout: {out!r}"
    assert "ImportError" not in err, f"ImportError leaked into stderr: {err!r}"
