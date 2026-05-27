"""Throwaway service-account JSON fixture for Google Chat channel tests.

google-auth's ``Credentials.from_service_account_file`` parses a JSON file
with a fixed shape (``type`` = ``"service_account"``, plus
``project_id`` / ``private_key_id`` / ``private_key`` / ``client_email``
/ ``client_id`` / ``token_uri``). The ``private_key`` field must be a
PEM-encoded RSA private key — google-auth refuses to load anything else.

This module generates a fresh 2048-bit RSA key at runtime via
``cryptography`` (transitively available via the ``dev`` extras) and
wraps it into a syntactically valid SA JSON. The key never leaves the
test process; we discard it as soon as the test function returns. This
lets tests that exercise the OAuth2 token flow run end-to-end without
shipping a baked-in fixture key file (which would be tedious to rotate
and easy to leak).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Iterator

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

FAKE_CLIENT_EMAIL = "cantus-tests@fake-project.iam.gserviceaccount.com"
FAKE_PROJECT_ID = "fake-project"
FAKE_PRIVATE_KEY_ID = "fake-key-id-0000000000000000000000000000"
FAKE_CLIENT_ID = "000000000000000000000"


def _generate_private_key_pem() -> bytes:
    """Generate a fresh 2048-bit RSA private key encoded as PEM bytes."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def build_fake_sa_dict() -> dict[str, str]:
    """Return a syntactically valid service-account JSON as a dict."""
    private_key_pem = _generate_private_key_pem().decode("ascii")
    return {
        "type": "service_account",
        "project_id": FAKE_PROJECT_ID,
        "private_key_id": FAKE_PRIVATE_KEY_ID,
        "private_key": private_key_pem,
        "client_email": FAKE_CLIENT_EMAIL,
        "client_id": FAKE_CLIENT_ID,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": (
            "https://www.googleapis.com/robot/v1/metadata/x509/"
            f"{FAKE_CLIENT_EMAIL.replace('@', '%40')}"
        ),
    }


def write_fake_sa_file(directory: Path) -> Path:
    """Write a fresh fake SA JSON into ``directory`` and return the path."""
    sa = build_fake_sa_dict()
    path = directory / "fake-service-account.json"
    path.write_text(json.dumps(sa))
    return path


def make_fake_sa_tempfile() -> Iterator[Path]:
    """Yield a temporary fake SA JSON path; cleans up on iterator exhaustion."""
    with tempfile.TemporaryDirectory() as td:
        path = write_fake_sa_file(Path(td))
        yield path
