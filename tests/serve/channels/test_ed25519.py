"""Tests for cantus.serve.channels._ed25519 (B2 Phase 3).

Covers the PyNaCl Ed25519 verification wrapper used by the Discord
interactions HTTP endpoint:

* ``verify_ed25519(public_key_bytes, message, signature)`` — green path
  (valid signature) and red paths (tampered body, tampered timestamp,
  wrong-length signature, wrong-length public key).
* ``DiscordSignatureError`` — fixed default message, single-parameter
  constructor signature, and the discipline that ``str(err)`` never
  echoes the public key, signature, or request body even when the
  exception is raised by a verification failure.
* Module-level constants ``SIGNATURE_HEADER`` and ``TIMESTAMP_HEADER``
  exist and carry the Discord-defined HTTP header names.
"""

from __future__ import annotations

import inspect

import pytest


def _generate_keypair() -> tuple[bytes, "object"]:
    """Return (public_key_bytes, signing_key) from a fresh Ed25519 keypair.

    The signing key is returned as ``nacl.signing.SigningKey`` so callers
    can produce signatures over arbitrary messages.
    """
    from nacl.signing import SigningKey

    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key
    return bytes(verify_key), signing_key


# --- 3.3 verify_ed25519 — green path ------------------------------------


def test_verify_ed25519_accepts_valid_signature() -> None:
    from cantus.serve.channels._ed25519 import verify_ed25519

    public_key_bytes, signing_key = _generate_keypair()
    timestamp = b"1700000000"
    body = b'{"type":1}'
    message = timestamp + body
    signature = signing_key.sign(message).signature

    # Returns None on success; must not raise.
    result = verify_ed25519(public_key_bytes, message, signature)
    assert result is None


# --- 3.3 verify_ed25519 — red paths -------------------------------------


def test_verify_ed25519_tampered_body_raises() -> None:
    from cantus.serve.channels._ed25519 import (
        DiscordSignatureError,
        verify_ed25519,
    )

    public_key_bytes, signing_key = _generate_keypair()
    timestamp = b"1700000000"
    original_body = b'{"type":1}'
    signature = signing_key.sign(timestamp + original_body).signature

    tampered_body = b'{"type":2}'
    with pytest.raises(DiscordSignatureError):
        verify_ed25519(public_key_bytes, timestamp + tampered_body, signature)


def test_verify_ed25519_tampered_timestamp_raises() -> None:
    from cantus.serve.channels._ed25519 import (
        DiscordSignatureError,
        verify_ed25519,
    )

    public_key_bytes, signing_key = _generate_keypair()
    original_timestamp = b"1700000000"
    body = b'{"type":1}'
    signature = signing_key.sign(original_timestamp + body).signature

    tampered_timestamp = b"1700000999"
    with pytest.raises(DiscordSignatureError):
        verify_ed25519(public_key_bytes, tampered_timestamp + body, signature)


def test_verify_ed25519_wrong_length_signature_raises() -> None:
    from cantus.serve.channels._ed25519 import (
        DiscordSignatureError,
        verify_ed25519,
    )

    public_key_bytes, _ = _generate_keypair()
    message = b"1700000000" + b'{"type":1}'

    short_signature = b"\x00" * 32  # Ed25519 sigs are 64 bytes; 32 is wrong.
    with pytest.raises(DiscordSignatureError):
        verify_ed25519(public_key_bytes, message, short_signature)


def test_verify_ed25519_wrong_length_public_key_raises() -> None:
    from cantus.serve.channels._ed25519 import (
        DiscordSignatureError,
        verify_ed25519,
    )

    _, signing_key = _generate_keypair()
    message = b"1700000000" + b'{"type":1}'
    signature = signing_key.sign(message).signature

    short_public_key = b"\x00" * 31  # Ed25519 public keys are 32 bytes.
    with pytest.raises(DiscordSignatureError):
        verify_ed25519(short_public_key, message, signature)


# --- 3.2 DiscordSignatureError shape ------------------------------------


def test_signature_error_fixed_message() -> None:
    from cantus.serve.channels._ed25519 import DiscordSignatureError

    err = DiscordSignatureError()
    assert str(err) == "discord interaction signature verification failed"


def test_signature_error_constructor_has_single_message_param() -> None:
    from cantus.serve.channels._ed25519 import DiscordSignatureError

    sig = inspect.signature(DiscordSignatureError.__init__)
    params = [name for name in sig.parameters if name != "self"]
    assert params == ["message"]

    message_param = sig.parameters["message"]
    # `from __future__ import annotations` stringifies annotations, so the
    # check tolerates both the string form and the resolved class.
    assert message_param.annotation in (str, "str")


def test_signature_error_str_does_not_leak_inputs() -> None:
    """Verification failure MUST NOT echo public key, signature, or body in str(err)."""
    from cantus.serve.channels._ed25519 import (
        DiscordSignatureError,
        verify_ed25519,
    )

    # Use obviously-fake byte patterns so we can grep for them later.
    fake_public_key = b"\xab" * 32  # 32 * 0xab
    fake_signature = b"\xcd" * 64
    fake_body = b"FAKE-BODY-DO-NOT-LEAK"
    fake_timestamp = b"FAKE-TIMESTAMP-DO-NOT-LEAK"

    with pytest.raises(DiscordSignatureError) as exc_info:
        verify_ed25519(
            fake_public_key, fake_timestamp + fake_body, fake_signature
        )
    rendered = str(exc_info.value)

    # No hex echo of inputs.
    assert fake_public_key.hex() not in rendered
    assert fake_signature.hex() not in rendered
    # No raw byte echo of body or timestamp.
    assert fake_body.decode() not in rendered
    assert fake_timestamp.decode() not in rendered


# --- 3.1 module-level constants -----------------------------------------


def test_signature_header_constants_present() -> None:
    from cantus.serve.channels import _ed25519

    assert _ed25519.SIGNATURE_HEADER == "X-Signature-Ed25519"
    assert _ed25519.TIMESTAMP_HEADER == "X-Signature-Timestamp"


# --- 8.1 cross-platform wheel matrix docstring --------------------------


def test_ed25519_module_docstring_lists_python_versions() -> None:
    """Task 8.1 requires the docstring to advertise the wheel matrix."""
    from cantus.serve.channels import _ed25519

    doc = _ed25519.__doc__ or ""
    assert "CPython 3.10" in doc
