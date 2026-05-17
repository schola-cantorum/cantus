"""Self-test that the providers conftest applies the secret-scrubbing config."""

from __future__ import annotations


def test_vcr_config_strips_known_auth_headers(vcr_config):
    headers = set(vcr_config["filter_headers"])
    # OpenAI / Groq / NVIDIA NIM use Authorization: Bearer ...
    assert "authorization" in headers
    # Anthropic uses x-api-key
    assert "x-api-key" in headers
    # Some proxies/internal APIs use api-key
    assert "api-key" in headers
    # Google AI Studio uses x-goog-api-key (forward-looking for v0.2.1)
    assert "x-goog-api-key" in headers


def test_vcr_record_mode_is_none_by_default(vcr_config):
    """CI must never silently record new cassettes."""
    assert vcr_config["record_mode"] == "none"
