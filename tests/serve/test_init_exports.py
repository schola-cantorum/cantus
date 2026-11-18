"""Tests for cantus.serve public API surface (v0.4.5 webhook additions)."""

from __future__ import annotations


def test_webhook_symbols_exported() -> None:
    """All four v0.4.5 names must be importable from cantus.serve."""
    from cantus.serve import (
        ChannelSendError,
        LineWebhookChannel,
        TelegramWebhookChannel,
        WebhookChannel,
    )

    # WebhookChannel is a runtime-checkable Protocol.
    from typing import Protocol  # noqa: F401  (sanity import)

    assert WebhookChannel.__name__ == "WebhookChannel"
    assert LineWebhookChannel.__name__ == "LineWebhookChannel"
    assert TelegramWebhookChannel.__name__ == "TelegramWebhookChannel"
    assert issubclass(ChannelSendError, Exception)


def test_webhook_symbols_in_all() -> None:
    import cantus.serve as serve_pkg

    assert "WebhookChannel" in serve_pkg.__all__
    assert "LineWebhookChannel" in serve_pkg.__all__
    assert "TelegramWebhookChannel" in serve_pkg.__all__
    assert "ChannelSendError" in serve_pkg.__all__


def test_realtime_channel_exported() -> None:
    """Task 2.3 — Requirement: RealtimeChannel Protocol extends Channel with
    connect/disconnect lifecycle. The Protocol is reachable from cantus.serve
    and appears in __all__ alongside the v0.4.5 channel symbols.
    """
    from cantus.serve import RealtimeChannel

    assert RealtimeChannel.__name__ == "RealtimeChannel"

    import cantus.serve as serve_pkg

    assert "RealtimeChannel" in serve_pkg.__all__


def test_existing_v040_symbols_still_exported() -> None:
    """ADDITIVE: v0.4.0+v0.4.1 names remain importable."""
    from cantus.serve import (
        AuthMode,
        Channel,
        LocalMockReceiver,
        require_auth,
        serve,
    )

    assert AuthMode is not None
    assert Channel is not None
    assert LocalMockReceiver is not None
    assert callable(require_auth)
    assert callable(serve)


def test_introspection_symbols_exported() -> None:
    """C2.0 — register_introspection_routes, SessionTracker, the read-models,
    and the QueueIntrospectable capability are importable from cantus.serve."""
    from cantus.serve import (  # noqa: F401
        IntrospectionSnapshot,
        PermissionsSnapshot,
        QueueIntrospectable,
        SessionTracker,
        ToolEntry,
        register_introspection_routes,
    )

    assert callable(register_introspection_routes)
    assert SessionTracker is not None


def test_introspection_symbols_in_all() -> None:
    import cantus.serve as serve_pkg

    for name in (
        "register_introspection_routes",
        "SessionTracker",
        "IntrospectionSnapshot",
        "ToolEntry",
        "SessionEntry",
        "PermissionsSnapshot",
        "QueueEntry",
        "WorkflowTrace",
        "DataflowGraph",
        "QueueIntrospectable",
    ):
        assert name in serve_pkg.__all__


def test_tool_entry_is_exported_from_serve_and_introspection() -> None:
    import cantus.serve as serve_pkg
    import cantus.serve.introspection as introspection

    assert "ToolEntry" in serve_pkg.__all__
    assert "ToolEntry" in introspection.__all__
    assert "collect_tools" in introspection.__all__
    assert serve_pkg.ToolEntry is introspection.ToolEntry


def test_collect_tools_returns_tool_entries_with_literal_fields() -> None:
    from cantus import Registry, tool
    from cantus.serve.introspection import ToolEntry, collect_tools

    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    entries = collect_tools(Registry(tools=[tool(add)]))

    assert len(entries) == 1
    assert isinstance(entries[0], ToolEntry)
    assert entries[0].name == "add"
    assert entries[0].description == "Add two numbers."
    assert entries[0].args_schema == {
        "properties": {
            "a": {"title": "A", "type": "integer"},
            "b": {"title": "B", "type": "integer"},
        },
        "required": ["a", "b"],
        "title": "AddArgs",
        "type": "object",
    }


def test_the_tool_names_and_routes_are_silent_with_bearer_auth_and_log_nothing(caplog) -> None:
    import logging
    import warnings

    from fastapi.testclient import TestClient

    import cantus
    from cantus import Registry, tool
    from cantus.config import Settings

    def echo(value: str) -> str:
        """Echo back."""
        return value

    caplog.set_level(logging.DEBUG)
    with warnings.catch_warnings():
        warnings.simplefilter("error", cantus.CantusDeprecationWarning)
        import cantus.serve  # noqa: F401
        from cantus.serve import ToolEntry, serve  # noqa: F401
        from cantus.serve.introspection import collect_tools  # noqa: F401

        settings = Settings(auth_mode="bearer", bearer_token="t0k")
        client = TestClient(serve(Registry(tools=[tool(echo)]), settings=settings))
        headers = {"Authorization": "Bearer t0k"}

        assert client.post("/tools/echo", json={"value": "hi"}, headers=headers).status_code == 200
        assert client.get("/tools", headers=headers).status_code == 200
        assert client.get("/introspection/tools", headers=headers).status_code == 200

    assert [r for r in caplog.records if r.name == "cantus.serve"] == []
