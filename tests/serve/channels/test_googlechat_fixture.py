"""Sanity tests for the ``fake_service_account`` fixture helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.serve.channels.fixtures.fake_service_account import (
    FAKE_CLIENT_EMAIL,
    FAKE_PROJECT_ID,
    build_fake_sa_dict,
    write_fake_sa_file,
)


def test_build_fake_sa_dict_has_required_fields() -> None:
    sa = build_fake_sa_dict()
    # Google-auth requires these fields at minimum.
    for required in (
        "type",
        "project_id",
        "private_key",
        "client_email",
        "token_uri",
    ):
        assert required in sa, f"fake SA dict missing required field {required!r}"
    assert sa["type"] == "service_account"
    assert sa["project_id"] == FAKE_PROJECT_ID
    assert sa["client_email"] == FAKE_CLIENT_EMAIL
    # PEM-encoded private key must start with the BEGIN PRIVATE KEY header.
    assert sa["private_key"].startswith("-----BEGIN PRIVATE KEY-----")


def test_fake_service_account_produces_loadable_credentials(
    tmp_path: Path,
) -> None:
    """Task 9.1 — the generated SA JSON loads cleanly via google-auth.

    Asserts that ``Credentials.from_service_account_file`` does not raise
    on our fixture. This protects the test fixtures from drift — if
    google-auth ever tightens its schema, this test fails before the
    downstream channel tests do."""
    path = write_fake_sa_file(tmp_path)
    assert path.exists()
    sa_content = json.loads(path.read_text())
    assert sa_content["type"] == "service_account"

    from google.oauth2.service_account import Credentials

    creds = Credentials.from_service_account_file(  # type: ignore[no-untyped-call]
        str(path),
        scopes=["https://www.googleapis.com/auth/chat.bot"],
    )
    assert creds.service_account_email == FAKE_CLIENT_EMAIL


def test_token_endpoint_mockable_via_jwt_grant_patch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task 9.2 — the token-exchange POST is testable without a live
    Google endpoint by patching ``google.oauth2._client.jwt_grant``.

    Why this and not respx: google-auth uses the ``requests`` library
    (not ``httpx``) internally, so respx — which intercepts httpx — does
    NOT capture the token endpoint call. The actual test mechanism we
    rely on for ``send()`` tests is direct patching of
    ``_token_cache.get_token`` (see ``test_googlechat_send.py``); this
    test documents the deeper jwt_grant patch as the supported escape
    hatch for tests that want to exercise the full ``Credentials.refresh``
    code path.
    """
    import datetime as dt

    from google.auth.transport.requests import Request
    from google.oauth2.service_account import Credentials

    path = write_fake_sa_file(tmp_path)
    creds = Credentials.from_service_account_file(  # type: ignore[no-untyped-call]
        str(path),
        scopes=["https://www.googleapis.com/auth/chat.bot"],
    )

    # google-auth stores expiry as a naive UTC datetime; build one the
    # same way it does internally (without tripping the utcnow deprecation
    # warning).
    fake_expiry = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) + dt.timedelta(hours=1)
    monkeypatch.setattr(
        "google.oauth2._client.jwt_grant",
        lambda request, token_uri, assertion: (
            "ya29.test-token-marker",
            fake_expiry,
            {"access_token": "ya29.test-token-marker"},
        ),
    )

    creds.refresh(Request())
    assert creds.token == "ya29.test-token-marker"
