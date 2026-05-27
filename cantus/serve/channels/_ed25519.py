"""cantus.serve.channels._ed25519 — Ed25519 signature verification for Discord.

Thin wrapper around :class:`nacl.signing.VerifyKey` (libsodium via PyNaCl)
used by the Discord interactions HTTP endpoint to authenticate inbound
requests. cantus does not roll its own Ed25519 — every verification call
funnels through :func:`verify_ed25519`, which surfaces a single,
secret-free :class:`DiscordSignatureError` for every failure mode so
callers cannot accidentally distinguish "wrong signature" from "wrong
length" via the exception surface (preserving the v0.4.1 401
indistinguishability discipline).

Cross-platform wheel matrix (B2 cantus[serve] C-extension discipline)
---------------------------------------------------------------------

``pynacl>=1.5,<2`` ships prebuilt binary wheels for every operating
system and CPython version supported by ``cantus[serve]==0.4.6``. No
source build is required when installing into a clean virtualenv on
any of the following targets:

* Linux x86_64 manylinux2014 — CPython 3.10, 3.11, 3.12, 3.13
* macOS arm64 (Apple Silicon) — CPython 3.10, 3.11, 3.12, 3.13
* macOS x86_64 (Intel) — CPython 3.10, 3.11, 3.12, 3.13
* Windows AMD64 — CPython 3.10, 3.11, 3.12, 3.13

Platforms outside this matrix (musllinux/Alpine, Linux aarch64 without
manylinux wheels, FreeBSD, etc.) are explicitly unsupported by the
``cantus-distribution`` spec and may require ``pip install`` to fall
back to a source build.
"""

from __future__ import annotations

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

#: HTTP header that carries the hex-encoded Ed25519 signature on each
#: Discord interactions POST. Constant taken from the Discord developer
#: documentation; case is preserved verbatim because some ASGI servers
#: surface headers case-sensitively when the framework reads them via
#: raw scope.
SIGNATURE_HEADER = "X-Signature-Ed25519"

#: HTTP header that carries the request timestamp (seconds since epoch
#: as ASCII digits) which is prepended to the raw body before
#: verification. See Discord's "Receiving and Responding" docs.
TIMESTAMP_HEADER = "X-Signature-Timestamp"

#: Fixed default message for :class:`DiscordSignatureError`. The string
#: is a module-level constant so callers cannot accidentally override
#: it with a value that leaks signature material via ``str(err)``.
_DEFAULT_MESSAGE = "discord interaction signature verification failed"


class DiscordSignatureError(Exception):
    """Raised when Discord interactions Ed25519 verification fails.

    The constructor accepts exactly one parameter, ``message``, defaulting
    to the fixed string ``"discord interaction signature verification
    failed"``. The exception deliberately refuses to store or echo the
    public key, the bot token, the request body, or the signature value:
    its ``str()`` representation is byte-identical to the default message
    for every instance constructed without an explicit override, so the
    401 surface returned by the interactions endpoint stays
    indistinguishable across every red-path branch (missing header,
    wrong-length signature, wrong-length public key, mathematically
    invalid signature).
    """

    def __init__(self, message: str = _DEFAULT_MESSAGE) -> None:
        super().__init__(message)


def verify_ed25519(
    public_key_bytes: bytes, message: bytes, signature: bytes
) -> None:
    """Verify an Ed25519 signature; raise :class:`DiscordSignatureError` on failure.

    Parameters
    ----------
    public_key_bytes:
        Raw 32-byte Ed25519 public key. Must be ``bytes``, never a hex
        string — accidental hex/base64 confusion is rejected via
        ``ValueError`` / ``TypeError`` from PyNaCl and surfaced as
        :class:`DiscordSignatureError` so callers see one failure mode
        regardless of which input is malformed.
    message:
        Concatenation of the ``X-Signature-Timestamp`` header bytes and
        the raw request body bytes, in that order. Callers are
        responsible for the concatenation; this function does not
        re-parse the headers.
    signature:
        Raw 64-byte Ed25519 signature bytes (already decoded from the
        hex value in the ``X-Signature-Ed25519`` header).

    Returns
    -------
    None
        Returned implicitly on successful verification. ``return`` is
        intentionally absent from the success path so the function reads
        as "raise on failure, fall through on success".

    Raises
    ------
    DiscordSignatureError
        Raised for every failure mode — mathematical signature mismatch
        (:class:`nacl.exceptions.BadSignatureError`), wrong-length
        public key, wrong-length signature, or any ``ValueError`` /
        ``TypeError`` surfaced by PyNaCl when the inputs are not raw
        bytes of the expected shape. The exception message is the
        fixed default; the inputs are never echoed.
    """
    try:
        verify_key = VerifyKey(public_key_bytes)
        verify_key.verify(message, signature)
    except BadSignatureError as exc:
        raise DiscordSignatureError() from exc
    except (ValueError, TypeError) as exc:
        # Wrong-length public key surfaces as ValueError from VerifyKey();
        # wrong-length signature surfaces as ValueError from .verify();
        # non-bytes inputs surface as TypeError. Collapse all of them to
        # the fixed DiscordSignatureError surface so the 401 endpoint
        # cannot leak which input was malformed.
        raise DiscordSignatureError() from exc


__all__ = [
    "DiscordSignatureError",
    "SIGNATURE_HEADER",
    "TIMESTAMP_HEADER",
    "verify_ed25519",
]
