"""cantus CLI entry point.

The `main(argv)` callable is wired into the `cantus` console script via
`pyproject.toml [project.scripts]` and also dispatched from
`cantus.__main__` so that `cantus serve ...` and `python -m cantus serve ...`
behave identically.

The serve subcommand is a thin wrapper around `cantus.serve(...)` —
argparse parses CLI args, the helpers below resolve them into a `Settings`
instance plus a `Registry` (and optional channel list), and finally
`uvicorn.run(app, host=settings.host, port=settings.port)` runs the server.
The wrapper deliberately leaves `KeyboardInterrupt` uncaught so uvicorn's
own SIGINT handler can drive graceful shutdown with exit code 0.
"""

from __future__ import annotations

import argparse
import importlib
import sys

from cantus.config import AuthMode, Settings
from cantus.core.registry import Registry


_AUTH_MODE_BY_CLI_VALUE: dict[str, AuthMode] = {
    "none": AuthMode.NONE,
    "bearer": AuthMode.BEARER,
    "api-key": AuthMode.API_KEY,
}


class RegistryImportError(Exception):
    """Raised when `--registry-import` cannot be resolved to a Registry instance."""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cantus",
        description="cantus — polyphonic LLM agent harness CLI.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    serve_parser = subparsers.add_parser(
        "serve",
        help="Start a FastAPI server exposing a cantus Registry over HTTP.",
        description=(
            "Start a FastAPI server exposing a cantus Registry over HTTP. "
            "Wraps cantus.serve(registry, ...) + uvicorn.run."
        ),
    )
    serve_parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Bind host (default: CANTUS_SERVE_HOST env or 127.0.0.1).",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Bind port (default: CANTUS_SERVE_PORT env or 8765).",
    )
    serve_parser.add_argument(
        "--registry-import",
        type=str,
        required=True,
        metavar="DOTTED_PATH",
        help=(
            "Dotted import path of the Registry instance, "
            "format `module.dotted.path:variable_name`."
        ),
    )
    serve_parser.add_argument(
        "--auth-mode",
        type=str,
        choices=list(_AUTH_MODE_BY_CLI_VALUE.keys()),
        default=None,
        help=(
            "Authentication mode (default: CANTUS_SERVE_AUTH_MODE env or none). "
            "`bearer` requires CANTUS_SERVE_BEARER_TOKEN; "
            "`api-key` requires CANTUS_SERVE_API_KEY."
        ),
    )
    dashboard_group = serve_parser.add_mutually_exclusive_group()
    dashboard_group.add_argument(
        "--dashboard",
        dest="dashboard",
        action="store_const",
        const=True,
        default=None,
        help="Force dashboard endpoints on (overrides CANTUS_SERVE_DASHBOARD).",
    )
    dashboard_group.add_argument(
        "--no-dashboard",
        dest="dashboard",
        action="store_const",
        const=False,
        help="Force dashboard endpoints off (overrides CANTUS_SERVE_DASHBOARD).",
    )
    serve_parser.add_argument(
        "--channels",
        nargs="+",
        default=None,
        metavar="DOTTED_PATH",
        help=(
            "One or more channel dotted import paths "
            "(format `module.dotted.path:variable_name`)."
        ),
    )
    serve_parser.set_defaults(func=_cmd_serve)
    return parser


def _resolve_registry_import(spec: str) -> Registry:
    module_name, _, attr_name = spec.partition(":")
    if not module_name or not attr_name:
        raise RegistryImportError(
            f"expected `module.dotted.path:variable_name`, got {spec!r}"
        )
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise RegistryImportError(str(exc)) from exc
    try:
        obj = getattr(module, attr_name)
    except AttributeError as exc:
        raise RegistryImportError(str(exc)) from exc
    if not isinstance(obj, Registry):
        raise RegistryImportError(
            f"{spec!r} resolved to {type(obj).__name__}, expected Registry"
        )
    return obj


def _resolve_channels_import(specs: list[str]) -> list:
    """Resolve one or more dotted-import channel specs into channel objects.

    Reuses `_resolve_registry_import`'s partition-then-import pattern but
    without the Registry isinstance check (channel kinds vary; the
    cantus.serve.channel.Channel base class would tighten this later).
    """
    channels = []
    for spec in specs:
        module_name, _, attr_name = spec.partition(":")
        if not module_name or not attr_name:
            raise RegistryImportError(
                f"expected `module.dotted.path:variable_name`, got {spec!r}"
            )
        try:
            module = importlib.import_module(module_name)
        except ImportError as exc:
            raise RegistryImportError(
                f"cannot import channel from {spec!r}: {exc}"
            ) from exc
        try:
            channels.append(getattr(module, attr_name))
        except AttributeError as exc:
            raise RegistryImportError(
                f"cannot import channel from {spec!r}: {exc}"
            ) from exc
    return channels


def _apply_override(
    settings: Settings,
    args: argparse.Namespace,
    settings_attr: str,
    cli_attr: str,
) -> None:
    """Apply a CLI override to `settings` only when the user supplied a value.

    argparse defaults are all `None`; this preserves the precedence
    CLI > env > Settings field default (see spec Requirement
    "Settings override precedence is CLI args, then env vars, then Settings
    defaults").
    """
    value = getattr(args, cli_attr)
    if value is not None:
        setattr(settings, settings_attr, value)


def _cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:
        print(
            "cantus serve: error: cantus[serve] not installed. "
            "Run: pip install cantus-agent[serve]",
            file=sys.stderr,
        )
        return 1

    try:
        registry = _resolve_registry_import(args.registry_import)
    except RegistryImportError as exc:
        print(
            f"cantus serve: error: cannot import registry from "
            f"{args.registry_import!r}: {exc}",
            file=sys.stderr,
        )
        return 1

    if args.channels is not None:
        try:
            channels = _resolve_channels_import(args.channels)
        except RegistryImportError as exc:
            print(f"cantus serve: error: {exc}", file=sys.stderr)
            return 1
    else:
        channels = None

    settings = Settings()
    _apply_override(settings, args, "host", "host")
    _apply_override(settings, args, "port", "port")
    _apply_override(settings, args, "dashboard", "dashboard")
    if args.auth_mode is not None:
        settings.auth_mode = _AUTH_MODE_BY_CLI_VALUE[args.auth_mode]

    from cantus.serve import serve as _build_app

    try:
        app = _build_app(registry, channels=channels, settings=settings)
    except ValueError as exc:
        print(f"cantus serve: error: {exc}", file=sys.stderr)
        return 1

    uvicorn.run(app, host=settings.host, port=settings.port)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for the `cantus` console script and `python -m cantus`.

    Returns the int exit code; raises `SystemExit` only when argparse
    decides to (unknown args, missing required, bad enum value → exit 2).
    Internal cantus errors map to exit 1; normal shutdown returns 0.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
