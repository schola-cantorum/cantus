"""Cassette-based contract test infrastructure for provider adapters.

Two safety properties matter here:

1.  **No secret ever lands in a cassette.** `filter_headers` strips every
    known auth header before vcrpy serialises a recorded request. We list
    Google's `x-goog-api-key` even though v0.2.0 ships no Google adapter
    so that v0.2.1 adapter work cannot bypass this gate by reusing the
    same conftest.
2.  **CI never records.** `record_mode='none'` means a missing or out-of-date
    cassette raises an error instead of silently going to the network.
    Re-recording is an explicit human action: pass `--record-mode=once`
    locally with real credentials.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": [
            "authorization",
            "x-api-key",
            "api-key",
            "x-goog-api-key",
        ],
        "record_mode": "none",
        "decode_compressed_response": True,
    }
