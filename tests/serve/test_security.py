"""Tests for cantus.serve.security (v0.4.1 cantus-serve-security).

Each test corresponds to one scenario from the
`Cantus serve gates Skill endpoints behind opt-in authentication` Requirement
in the cantus-distribution capability (cantus-serve-security release content).

Test matrix:
1. NONE preserves v0.4.0 zero-auth behavior.
2. Bearer mode rejects missing token with 401.
3. Bearer mode rejects wrong token with 401 (byte-identical body to #2).
4. Bearer mode accepts correct token with 200.
5. API-key mode parity (missing / wrong / correct → 401 / 401 / 200).
6. SecretStr token fields do not leak in repr / model_dump_json / OpenAPI / log.

Plus: fail-fast when auth_mode != NONE but corresponding token field is unset,
and the dashboard_requires_auth toggle is covered in test_dashboard.py.
"""

from __future__ import annotations

import importlib
import json
import logging
from collections.abc import Iterator
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def _clear_cantus_serve_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Strip any pre-existing CANTUS_SERVE_* env so each test starts clean."""
    import os

    for key in list(os.environ):
        if key.startswith("CANTUS_SERVE_"):
            monkeypatch.delenv(key, raising=False)
    yield


def _fresh_settings_class() -> type[Any]:
    """Reload cantus.config so env-driven Settings are picked up per-test."""
    module = importlib.import_module("cantus.config")
    importlib.reload(module)
    return module.Settings


def _registry_with_echo() -> Any:
    """Build a Registry with a single `echo` Skill returning the input string."""
    from cantus.core.registry import Registry
    from cantus.protocols.skill import register_skill

    def echo(value: str) -> str:
        """Echo back."""
        return value

    instance = register_skill(echo)
    registry = Registry()
    registry.register("skill", instance)
    return registry


_AUTH_REQUIRED_BODY = {"detail": "Authentication required"}


# --- Case 1: NONE preserves v0.4.0 behavior ------------------------------


def test_none_mode_preserves_v040_behavior() -> None:
    """auth_mode default NONE: anonymous requests succeed exactly as in v0.4.0."""
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    Settings = _fresh_settings_class()
    settings = Settings()
    app = serve(_registry_with_echo(), settings=settings)
    client = TestClient(app)

    resp = client.post("/skills/echo", json={"value": "hi"})
    assert resp.status_code == 200
    assert resp.json() == {"result": "hi"}
    # Dashboard endpoints also accept anonymous requests under NONE.
    assert client.get("/skills").status_code == 200
    assert client.get("/health").status_code == 200
    assert client.get("/events").status_code == 200


# --- Case 2 + 3: bearer 401 indistinguishable ---------------------------


def _bearer_app(monkeypatch: pytest.MonkeyPatch, token: str = "correct-secret") -> Any:
    from cantus.serve import serve

    monkeypatch.setenv("CANTUS_SERVE_AUTH_MODE", "bearer")
    monkeypatch.setenv("CANTUS_SERVE_BEARER_TOKEN", token)
    Settings = _fresh_settings_class()
    settings = Settings()
    return serve(_registry_with_echo(), settings=settings)


def test_bearer_missing_header_401(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    app = _bearer_app(monkeypatch)
    client = TestClient(app)
    resp = client.post("/skills/echo", json={"value": "hi"})
    assert resp.status_code == 401
    assert resp.json() == _AUTH_REQUIRED_BODY


def test_bearer_wrong_token_401(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    app = _bearer_app(monkeypatch)
    client = TestClient(app)
    resp = client.post(
        "/skills/echo",
        json={"value": "hi"},
        headers={"Authorization": "Bearer wrong-secret"},
    )
    assert resp.status_code == 401
    assert resp.json() == _AUTH_REQUIRED_BODY


def test_bearer_401_bodies_byte_identical_between_missing_and_wrong(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The 401 body MUST NOT distinguish missing-credential vs wrong-credential."""
    from fastapi.testclient import TestClient

    app = _bearer_app(monkeypatch)
    client = TestClient(app)
    missing = client.post("/skills/echo", json={"value": "hi"})
    wrong = client.post(
        "/skills/echo",
        json={"value": "hi"},
        headers={"Authorization": "Bearer wrong-secret"},
    )
    assert missing.content == wrong.content


# --- Bearer edge cases: malformed Authorization header ------------------


def test_bearer_no_space_after_scheme_returns_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`Authorization: Bearer<token>` (no space) violates RFC 6750 and must 401."""
    from fastapi.testclient import TestClient

    app = _bearer_app(monkeypatch)
    client = TestClient(app)
    resp = client.post(
        "/skills/echo",
        json={"value": "hi"},
        headers={"Authorization": "Bearercorrect-secret"},
    )
    assert resp.status_code == 401
    assert resp.json() == _AUTH_REQUIRED_BODY


def test_bearer_empty_token_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    """`Authorization: Bearer ` (scheme but no token) must 401."""
    from fastapi.testclient import TestClient

    app = _bearer_app(monkeypatch)
    client = TestClient(app)
    resp = client.post(
        "/skills/echo",
        json={"value": "hi"},
        headers={"Authorization": "Bearer "},
    )
    assert resp.status_code == 401
    assert resp.json() == _AUTH_REQUIRED_BODY


def test_bearer_uppercase_scheme_still_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`Authorization: BEARER <token>` (uppercase scheme) is RFC 6750 compliant
    (auth-scheme is case-insensitive); we accept it."""
    from fastapi.testclient import TestClient

    app = _bearer_app(monkeypatch)
    client = TestClient(app)
    resp = client.post(
        "/skills/echo",
        json={"value": "hi"},
        headers={"Authorization": "BEARER correct-secret"},
    )
    assert resp.status_code == 200


def test_bearer_extra_whitespace_around_token_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Trailing whitespace after the token is stripped (defensive against
    sloppy clients) and the auth still succeeds."""
    from fastapi.testclient import TestClient

    app = _bearer_app(monkeypatch)
    client = TestClient(app)
    resp = client.post(
        "/skills/echo",
        json={"value": "hi"},
        headers={"Authorization": "Bearer correct-secret  "},
    )
    assert resp.status_code == 200


# --- Case 4: bearer 200 ---------------------------------------------------


def test_bearer_correct_token_200(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    app = _bearer_app(monkeypatch)
    client = TestClient(app)
    resp = client.post(
        "/skills/echo",
        json={"value": "hi"},
        headers={"Authorization": "Bearer correct-secret"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"result": "hi"}


# --- Case 5: api-key mode parity -----------------------------------------


def _api_key_app(monkeypatch: pytest.MonkeyPatch, key: str = "correct-key") -> Any:
    from cantus.serve import serve

    monkeypatch.setenv("CANTUS_SERVE_AUTH_MODE", "api-key")
    monkeypatch.setenv("CANTUS_SERVE_API_KEY", key)
    Settings = _fresh_settings_class()
    settings = Settings()
    return serve(_registry_with_echo(), settings=settings)


def test_api_key_mode_missing_header_401(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    app = _api_key_app(monkeypatch)
    client = TestClient(app)
    resp = client.post("/skills/echo", json={"value": "hi"})
    assert resp.status_code == 401
    assert resp.json() == _AUTH_REQUIRED_BODY


def test_api_key_mode_wrong_key_401(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    app = _api_key_app(monkeypatch)
    client = TestClient(app)
    resp = client.post(
        "/skills/echo",
        json={"value": "hi"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401
    assert resp.json() == _AUTH_REQUIRED_BODY


def test_api_key_mode_correct_key_200(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    app = _api_key_app(monkeypatch)
    client = TestClient(app)
    resp = client.post(
        "/skills/echo",
        json={"value": "hi"},
        headers={"X-API-Key": "correct-key"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"result": "hi"}


# --- Case 6: SecretStr does not leak in repr / JSON / OpenAPI / log -----


def test_secretstr_does_not_leak_in_repr_json_openapi_or_log(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from fastapi.testclient import TestClient

    monkeypatch.setenv("CANTUS_SERVE_AUTH_MODE", "bearer")
    monkeypatch.setenv("CANTUS_SERVE_BEARER_TOKEN", "correct-secret")
    monkeypatch.setenv("CANTUS_SERVE_API_KEY", "correct-key")
    Settings = _fresh_settings_class()
    settings = Settings()

    # repr — both tokens are masked.
    assert "correct-secret" not in repr(settings)
    assert "correct-key" not in repr(settings)

    # JSON dump.
    assert "correct-secret" not in settings.model_dump_json()
    assert "correct-key" not in settings.model_dump_json()

    # OpenAPI schema.
    from cantus.serve import serve

    app = serve(_registry_with_echo(), settings=settings)
    client = TestClient(app)
    openapi = client.get("/openapi.json").json()
    openapi_text = json.dumps(openapi)
    assert "correct-secret" not in openapi_text
    assert "correct-key" not in openapi_text

    # Log surface — drive both a 401 and a 200 then scan caplog.
    with caplog.at_level(logging.DEBUG, logger="cantus.serve"):
        client.post("/skills/echo", json={"value": "hi"})  # missing auth → 401
        client.post(
            "/skills/echo",
            json={"value": "hi"},
            headers={"Authorization": "Bearer correct-secret"},
        )  # valid → 200
    assert "correct-secret" not in caplog.text
    assert "correct-key" not in caplog.text


# --- Fail-fast on missing token ------------------------------------------


def test_serve_fails_fast_when_bearer_mode_token_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """auth_mode=bearer with no bearer_token must raise ValueError at serve()."""
    from cantus.serve import serve

    monkeypatch.setenv("CANTUS_SERVE_AUTH_MODE", "bearer")
    # NOTE: bearer_token intentionally unset.
    Settings = _fresh_settings_class()
    settings = Settings()
    with pytest.raises(ValueError, match=r"bearer.*BEARER_TOKEN"):
        serve(_registry_with_echo(), settings=settings)


def test_serve_fails_fast_when_api_key_mode_token_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cantus.serve import serve

    monkeypatch.setenv("CANTUS_SERVE_AUTH_MODE", "api-key")
    Settings = _fresh_settings_class()
    settings = Settings()
    with pytest.raises(ValueError, match=r"api-key.*API_KEY"):
        serve(_registry_with_echo(), settings=settings)


def test_serve_fails_fast_when_bearer_token_is_empty_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`CANTUS_SERVE_BEARER_TOKEN=""` would pass an `is None` check yet make
    every request 401 — that is a foot-gun. validate_auth_config must reject
    empty / whitespace-only tokens at app build time."""
    from cantus.serve import serve

    monkeypatch.setenv("CANTUS_SERVE_AUTH_MODE", "bearer")
    monkeypatch.setenv("CANTUS_SERVE_BEARER_TOKEN", "")
    Settings = _fresh_settings_class()
    settings = Settings()
    with pytest.raises(ValueError, match=r"BEARER_TOKEN.*non-empty"):
        serve(_registry_with_echo(), settings=settings)


def test_serve_fails_fast_when_api_key_is_whitespace_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cantus.serve import serve

    monkeypatch.setenv("CANTUS_SERVE_AUTH_MODE", "api-key")
    monkeypatch.setenv("CANTUS_SERVE_API_KEY", "   ")
    Settings = _fresh_settings_class()
    settings = Settings()
    with pytest.raises(ValueError, match=r"API_KEY.*non-empty"):
        serve(_registry_with_echo(), settings=settings)


# --- require_auth dependency uses constant-time compare -----------------


def test_require_auth_uses_constant_time_compare() -> None:
    """The token comparison must go through hmac.compare_digest."""
    import inspect

    from cantus.serve import security as security_module

    src = inspect.getsource(security_module)
    assert "hmac.compare_digest" in src or "compare_digest" in src, (
        "require_auth implementation must use hmac.compare_digest "
        "for constant-time token comparison to prevent timing-oracle attacks"
    )


# --- Defensive branches: NONE short-circuit + unknown mode fail-closed --


def _mock_request_with_settings(settings: Any) -> Any:
    """Build a minimal Request-shaped object exposing app.state.settings."""

    class _State:
        pass

    class _App:
        state: _State

    class _Request:
        app: _App
        headers: dict[str, str] = {}

    app = _App()
    app.state = _State()
    app.state.settings = settings
    req = _Request()
    req.app = app
    req.headers = {}
    return req


def test_require_auth_short_circuits_under_auth_mode_none() -> None:
    """Defensive path: when require_auth is called with auth_mode=NONE it
    must return None without consulting any header. Normal serve() never
    attaches the dependency in NONE mode, but the short-circuit is the
    correctness guarantee."""
    from cantus.config import AuthMode, Settings
    from cantus.serve.security import require_auth

    settings = Settings()
    assert settings.auth_mode == AuthMode.NONE
    req = _mock_request_with_settings(settings)
    assert require_auth(req) is None  # type: ignore[arg-type]


def test_require_auth_fails_closed_on_unknown_mode() -> None:
    """Defensive path: if auth_mode somehow holds an unknown value (e.g. via
    direct attribute injection bypassing the enum), require_auth must raise
    401 rather than silently allow the request through."""
    from fastapi import HTTPException

    from cantus.config import Settings
    from cantus.serve.security import require_auth

    settings = Settings()
    # Bypass the enum to simulate a degenerate state — never happens via env
    # variables (pydantic-settings would reject), but require_auth must not
    # silently allow a request through if it ever does.
    object.__setattr__(settings, "auth_mode", "unknown-mode")
    req = _mock_request_with_settings(settings)
    with pytest.raises(HTTPException) as excinfo:
        require_auth(req)  # type: ignore[arg-type]
    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Authentication required"
