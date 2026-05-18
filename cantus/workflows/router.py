"""Router — classifier-driven dispatch to one of several Skills."""

from __future__ import annotations

from typing import Any, Callable, Mapping


class Router:
    """Classify input, then call exactly one of the registered routes.

    Pure Python composition — SHALL NOT touch the runtime registry.

        router = Router(
            routes={"weather": get_weather, "news": fetch_news},
            classifier=classify_intent,
        )
        router.run("typhoon update")
    """

    def __init__(
        self,
        routes: Mapping[str, Callable[..., Any]],
        classifier: Callable[[Any], str],
    ) -> None:
        if not routes:
            raise ValueError("Router requires at least one route")
        self.routes = dict(routes)
        self.classifier = classifier

    def run(self, input: Any) -> Any:
        key = self.classifier(input)
        if key not in self.routes:
            raise KeyError(
                f"classifier returned {key!r}, not in routes {sorted(self.routes)}"
            )
        return self.routes[key](input)
