"""cantus — Polyphonic LLM agent framework with a dual-tier teaching API."""

# ruff: noqa: E402  (_install_default_filter() must run before any other import below it)

from __future__ import annotations

from cantus._deprecation import install_default_filter as _install_default_filter

_install_default_filter()

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cantus.model.loader import ModelHandle
    from cantus.protocols.tool import Tool as Skill  # noqa: F401  # legacy-alias

__version__ = "0.6.0"

from cantus._deprecation import CantusDeprecationWarning
from cantus._deprecation import warn_legacy as _warn_legacy
from cantus.core.action import (
    Action,
    CallSkillAction,
    FinalAnswerAction,
)
from cantus.core.agent import Agent, AgentState
from cantus.core.event_stream import EventStream
from cantus.core.event_stream_persistence import JsonLinesPersistence
from cantus.core.observation import (
    MaxIterationsObservation,
    Observation,
    SkillObservation,
    ToolErrorObservation,
    ValidationErrorObservation,
)
from cantus.core.registry import Registry, get_registry  # legacy-alias
from cantus.core.result import Result
from cantus.env import CloudOnlyEnvironment, ColabEnvironment, LocalEnvironment
from cantus.identity import Soul, SoulParseError
from cantus.inspect import Inspector
from cantus.model.bridge import ChatModelAsHandle
from cantus.model.chat import ChatModel, ChatResponse, Message, ToolCall
from cantus.model.factory import load_chat_model
from cantus.protocols.debug import debug
from cantus.protocols.memory import (
    AutoMemory,
    BM25Memory,
    EmbeddingMemory,
    MarkdownMemory,
    Memory,
    ShortTermMemory,
)
from cantus.protocols.skill import register_skill, skill  # legacy-alias
from cantus.protocols.tool import Tool, register_tool, tool

__all__ = [
    # Decorator entries (tool + debug only at top level;
    # analyzer/validator are now imported from cantus.hooks)
    "tool",
    "skill",  # legacy-alias
    "debug",
    # Function-pass entries
    "register_tool",
    "register_skill",  # legacy-alias
    # Class-first base classes (top level: Tool + Memory only;
    # Analyzer/Validator are imported from cantus.hooks)
    "Tool",
    "Memory",
    # Memory implementations (v0.3.1: MarkdownMemory + AutoMemory join)
    "ShortTermMemory",
    "BM25Memory",
    "EmbeddingMemory",
    "MarkdownMemory",
    "AutoMemory",
    # Identity (v0.3.1)
    "Soul",
    "SoulParseError",
    # EventStream persistence plug (v0.3.1)
    "JsonLinesPersistence",
    # Runtime
    "Action",
    "CallSkillAction",
    "FinalAnswerAction",
    "Observation",
    "SkillObservation",
    "ToolErrorObservation",
    "ValidationErrorObservation",
    "MaxIterationsObservation",
    "EventStream",
    "Agent",
    "AgentState",
    "Inspector",
    # Registry
    "Registry",
    "get_registry",  # legacy-alias
    # Deprecation warnings (v0.7.0)
    "CantusDeprecationWarning",
    # Result type
    "Result",
    # Tier 2 ChatModel
    "ChatModel",
    "Message",
    "ToolCall",
    "ChatResponse",
    "ChatModelAsHandle",
    "load_chat_model",
    # Environment profiles
    "ColabEnvironment",
    "LocalEnvironment",
    "CloudOnlyEnvironment",
    # Serve layer (v0.4.0, lazy-loaded; require `pip install cantus[serve]`)
    "serve",
    "config",
]


def __getattr__(name: str) -> Any:
    """PEP 562 lazy loader for the v0.4.0 serve layer.

    `cantus.serve` and `cantus.config` are exposed at the top level but
    imported on first attribute access so that a base ``import cantus``
    does not require ``fastapi`` / ``uvicorn`` / ``pydantic-settings``.
    Missing extras still surface as ``ImportError`` with the literal
    substring ``"pip install cantus[serve]"`` from the gate inside the
    target module. It also serves the legacy class name as `Tool`, with a
    deprecation warning.
    """
    if name == "Skill":  # legacy-alias
        _warn_legacy("W1")
        return Tool
    if name in {"serve", "config"}:
        import importlib

        module = importlib.import_module(f"cantus.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module 'cantus' has no attribute {name!r}")


def mount_drive_and_load(*args: object, **kwargs: object) -> ModelHandle:
    """Mount Google Drive and load Gemma 4 weights — see model.loader."""
    from cantus.model.loader import mount_drive_and_load as _impl

    return _impl(*args, **kwargs)  # type: ignore[arg-type]


def load_gemma(*args: object, **kwargs: object) -> ModelHandle:
    """Alias of mount_drive_and_load for direct hub loading scenarios."""
    return mount_drive_and_load(*args, **kwargs)
