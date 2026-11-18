"""Router: classifier picks one route; unselected routes are NOT called."""

from __future__ import annotations

import pytest

from cantus import tool
from cantus.core.registry import _get_global_registry
from cantus.workflows import Router


def test_router_calls_only_selected_route():
    calls: list[str] = []

    @tool
    def get_weather(query: str) -> str:
        """Weather."""
        calls.append("weather")
        return f"weather:{query}"

    @tool
    def fetch_news(query: str) -> str:
        """News."""
        calls.append("news")
        return f"news:{query}"

    def classify(query: str) -> str:
        return "weather" if "typhoon" in query else "news"

    router = Router(
        routes={"weather": get_weather, "news": fetch_news},
        classifier=classify,
    )
    result = router.run("typhoon update")

    assert result == "weather:typhoon update"
    assert calls == ["weather"]
    assert "news" not in calls


def test_router_unknown_route_key_raises():
    @tool
    def only(x: str) -> str:
        """Single."""
        return x

    router = Router(routes={"a": only}, classifier=lambda _: "b")
    with pytest.raises(KeyError):
        router.run("anything")


def test_router_does_not_pollute_registry():
    @tool
    def route_a(x: str) -> str:
        """A."""
        return x

    router = Router(routes={"a": route_a}, classifier=lambda _: "a")
    router.run("input")

    assert _get_global_registry().names_for("tool") == []


def test_router_empty_routes_raises():
    with pytest.raises(ValueError):
        Router(routes={}, classifier=lambda _: "x")
