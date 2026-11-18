"""Shared helpers for tests that drive an Agent with a scripted model.

`call_json` builds a model output with the `tool_name` action key.
"""

import json

from cantus import Agent
from cantus.core.observation import (
    ToolErrorObservation,
    ToolObservation,
    ValidationErrorObservation,
)


class ScriptedModel:
    """Model stub: returns the scripted outputs in order, records prompts."""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.prompts = []

    def generate(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return self.outputs.pop(0)


def call_json(name, **args):
    action = {"tool_name": name, "args": args}
    return json.dumps({"thought": "t", "action": action})


def final_json():
    return json.dumps({"thought": "d", "action": {"final_answer": "ok"}})


def run_agent(tools, outputs):
    """Run an agent built with ``tools=`` against the scripted outputs; return (stream, model)."""
    model = ScriptedModel(outputs)
    stream = Agent(model, tools=tools).run("q").stream
    return stream, model


def observations(stream):
    return [
        e
        for e in stream
        if isinstance(e, (ToolObservation, ValidationErrorObservation))
    ]


def tool_results(stream):
    """(name, result) for every successful tool observation."""
    return [
        (e.tool_name, e.result)
        for e in stream
        if isinstance(e, ToolObservation)
    ]


def tool_errors(stream):
    return [e for e in stream if isinstance(e, ToolErrorObservation)]


def parse_errors(stream):
    return [
        e
        for e in stream
        if isinstance(e, ValidationErrorObservation) and e.validator_name == "action_parse"
    ]


def prompt_tool_names(model, index=0):
    """The tool names listed in the catalog of the ``index``-th prompt the model saw."""
    return [t["name"] for t in json.loads(model.prompts[index])["tools"]["tool"]]
