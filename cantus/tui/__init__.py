"""cantus.tui — a standalone terminal dashboard client for ``cantus serve``.

The TUI is a *client*: it connects over HTTP to an already-running
``cantus serve`` instance and polls its read-only ``/introspection`` +
``/health`` endpoints, rendering a four-pane Textual dashboard (sessions /
events / queue / health). It never shares a process with the server and
issues only GET requests.

``run_tui`` is the package entry point invoked by the ``cantus tui`` CLI
subcommand. Textual is imported lazily inside the function body so that
``import cantus.tui`` does not require the ``cantus[tui]`` optional
dependencies to be installed — the CLI surfaces an actionable install hint
when they are missing.
"""

from __future__ import annotations


def run_tui(
    url: str,
    *,
    auth_mode: str = "none",
    poll_interval: float = 2.0,
) -> None:
    """Launch the cantus terminal dashboard against a running serve URL.

    Parameters:
        url: Base URL of the running ``cantus serve`` instance, e.g.
            ``http://127.0.0.1:8765``.
        auth_mode: One of ``"none"``, ``"bearer"``, or ``"api-key"``. When not
            ``"none"`` the client reads the token from the matching
            ``CANTUS_SERVE_*`` environment variable and sends it as a header.
        poll_interval: Seconds between automatic refresh ticks.
    """
    from cantus.tui.app import CantusTUI

    app = CantusTUI(url=url, auth_mode=auth_mode, poll_interval=poll_interval)
    app.run()


__all__ = ["run_tui"]
