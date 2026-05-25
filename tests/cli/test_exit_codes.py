"""Exit-code contract for cantus-internal errors → exit 1.

Covers Requirement「CLI exit codes follow argparse error / cantus error /
signal convention」 — three error paths from the spec map to exit code 1:

1. `--registry-import` resolution failure (ImportError / AttributeError /
   non-Registry result).
2. `validate_auth_config` raising `ValueError` (auth_mode != NONE with the
   matching token field unset).
3. `import uvicorn` failure (missing `[serve]` extras).

argparse-driven errors (exit 2) and signal-driven shutdown (exit 0 / ≥130)
are covered by `test_serve_args.py` and `test_signal_handling.py`
respectively.
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stderr

from cantus.cli import main


def _no_op_uvicorn_run(*args, **kwargs):
    return None


def test_registry_import_failure_exits_1(monkeypatch):
    """Bad `--registry-import` → stderr with cantus-serve prefix + exit 1."""
    monkeypatch.delenv("CANTUS_SERVE_BEARER_TOKEN", raising=False)
    import uvicorn

    monkeypatch.setattr(uvicorn, "run", _no_op_uvicorn_run)

    err = io.StringIO()
    with redirect_stderr(err):
        rc = main(
            [
                "serve",
                "--registry-import",
                "definitely.not.a.module:registry",
            ]
        )
    assert rc == 1
    err_text = err.getvalue()
    assert err_text.startswith(
        "cantus serve: error: cannot import registry from "
        "'definitely.not.a.module:registry'"
    )


def test_bearer_without_env_token_exits_1(monkeypatch):
    """`--auth-mode bearer` without `CANTUS_SERVE_BEARER_TOKEN` → exit 1.

    Scenario: --auth-mode bearer without env token exits 1.
    """
    monkeypatch.delenv("CANTUS_SERVE_BEARER_TOKEN", raising=False)
    import uvicorn

    monkeypatch.setattr(uvicorn, "run", _no_op_uvicorn_run)

    err = io.StringIO()
    with redirect_stderr(err):
        rc = main(
            [
                "serve",
                "--registry-import",
                "tests.cli.fixture_registry:registry",
                "--auth-mode",
                "bearer",
            ]
        )
    assert rc == 1
    assert "bearer requires CANTUS_SERVE_BEARER_TOKEN" in err.getvalue()


def test_api_key_without_env_key_exits_1(monkeypatch):
    """`--auth-mode api-key` without `CANTUS_SERVE_API_KEY` → exit 1.

    Scenario: --auth-mode api-key without env key exits 1.
    """
    monkeypatch.delenv("CANTUS_SERVE_API_KEY", raising=False)
    import uvicorn

    monkeypatch.setattr(uvicorn, "run", _no_op_uvicorn_run)

    err = io.StringIO()
    with redirect_stderr(err):
        rc = main(
            [
                "serve",
                "--registry-import",
                "tests.cli.fixture_registry:registry",
                "--auth-mode",
                "api-key",
            ]
        )
    assert rc == 1
    assert "api-key requires CANTUS_SERVE_API_KEY" in err.getvalue()


def test_missing_uvicorn_exits_1(monkeypatch):
    """If `import uvicorn` fails inside _cmd_serve → exit 1 + install hint.

    Scenario: missing serve extras exits 1.

    Hides `uvicorn` from the import system for the duration of the test so
    that `_cmd_serve`'s lazy import raises ImportError exactly as in a
    truly missing-extras environment.
    """
    # Force the lazy `import uvicorn` inside `_cmd_serve` to fail.
    monkeypatch.setitem(sys.modules, "uvicorn", None)

    err = io.StringIO()
    with redirect_stderr(err):
        rc = main(
            [
                "serve",
                "--registry-import",
                "tests.cli.fixture_registry:registry",
            ]
        )
    assert rc == 1
    assert "cantus[serve] not installed" in err.getvalue()
