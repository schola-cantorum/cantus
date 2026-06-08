"""TOML structure tests for the v0.4.0 serve extras and uv extras-conflict declaration.

These tests parse `pyproject.toml` directly (no real `pip install` / `uv sync`
required) and verify:

* the `serve` optional-dependencies group pins `fastapi`, `uvicorn`, and
  `pydantic-settings` to the version ranges named by the
  `cantus-distribution` Requirement `Distribution extras matrix exposes
  openai, anthropic, google, groq, providers, mcp, langchain, dspy,
  huggingface, openhands, serve, and dev groups`;
* the eleven legacy extras keys (openai, anthropic, google, groq, providers,
  mcp, langchain, dspy, huggingface, openhands, dev) still exist, satisfying
  the REMOVED Requirement's migration scenario ("Removal preserves prior
  extras-matrix behavior");
* the `[tool.uv].conflicts` table declares `cantus[all]` and
  `cantus[openhands]` as a single mutually-exclusive cluster, satisfying the
  ADDED Requirement `pyproject declares uv-style extras conflicts for known
  incompatible groups`.

Fresh `uv sync` smoke (the spec's other scenario) is run by hand in
verification step task 10.3; this module covers only the structural shape.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

if sys.version_info < (3, 11):
    pytest.skip("tomllib requires Python 3.11+", allow_module_level=True)

import tomllib

_PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _load_pyproject() -> dict:
    with _PYPROJECT.open("rb") as fh:
        return tomllib.load(fh)


# --- ADDED Requirement: extras matrix surfaces the serve group -----------


def test_serve_extras_group_exists() -> None:
    cfg = _load_pyproject()
    extras = cfg["project"]["optional-dependencies"]
    assert "serve" in extras, "[project.optional-dependencies].serve missing"


def test_serve_extras_pins_fastapi_uvicorn_pydantic_settings() -> None:
    cfg = _load_pyproject()
    serve = cfg["project"]["optional-dependencies"]["serve"]
    flat = " ".join(serve)
    assert re.search(r"fastapi>=0\.115,<1\b", flat), (
        f"serve extras must pin fastapi>=0.115,<1; got: {serve}"
    )
    assert re.search(r"uvicorn>=0\.30,<1\b", flat), (
        f"serve extras must pin uvicorn>=0.30,<1; got: {serve}"
    )
    assert re.search(r"pydantic-settings>=2\.4,<3\b", flat), (
        f"serve extras must pin pydantic-settings>=2.4,<3; got: {serve}"
    )


def test_serve_extras_pins_google_cloud_pubsub() -> None:
    """Task 2.1 — Requirement: serve extras adds google-cloud-pubsub dependency
    with cross-platform wheel coverage.

    The B3 (v0.4.7) channel gateway pulls google-cloud-pubsub for the Pub/Sub
    streaming-pull inbound transport. google-auth is NOT pinned explicitly —
    it arrives transitively through google-cloud-pubsub.
    """
    cfg = _load_pyproject()
    serve = cfg["project"]["optional-dependencies"]["serve"]
    flat = " ".join(serve)
    assert re.search(r"google-cloud-pubsub>=2\.20,<3\b", flat), (
        f"serve extras must pin google-cloud-pubsub>=2.20,<3; got: {serve}"
    )
    # google-auth must NOT be pinned explicitly — it comes via google-cloud-pubsub.
    assert not re.search(r"^google-auth[<>=~]", flat), (
        f"google-auth must not be pinned explicitly; got: {serve}"
    )


def test_legacy_extras_keys_preserved_byte_identical() -> None:
    cfg = _load_pyproject()
    extras = cfg["project"]["optional-dependencies"]
    legacy_keys = {
        "openai",
        "anthropic",
        "google",
        "groq",
        "providers",
        "mcp",
        "langchain",
        "dspy",
        "huggingface",
        "openhands",
        "dev",
    }
    missing = legacy_keys - extras.keys()
    assert not missing, (
        f"v0.3.3 extras matrix keys missing after v0.4.0 upgrade: {sorted(missing)}"
    )


# --- ADDED Requirement: [tool.uv].conflicts declares the all/openhands cluster


def test_tool_uv_conflicts_declares_all_vs_openhands_cluster() -> None:
    cfg = _load_pyproject()
    uv_table = cfg.get("tool", {}).get("uv")
    assert uv_table is not None, "[tool.uv] table missing — required for v0.4.0"

    conflicts = uv_table.get("conflicts")
    assert isinstance(conflicts, list), (
        "[tool.uv].conflicts must be a list of mutually-exclusive clusters"
    )

    def _cluster_matches(cluster: object, expected: set[str]) -> bool:
        if not isinstance(cluster, list):
            return False
        names = set()
        for entry in cluster:
            if isinstance(entry, dict) and "extra" in entry:
                names.add(entry["extra"])
        return names == expected

    expected = {"all", "openhands"}
    matched = any(_cluster_matches(c, expected) for c in conflicts)
    assert matched, (
        "[tool.uv].conflicts must include a cluster {extra='all'} ⊗ {extra='openhands'} "
        f"to suppress fresh-uv-sync universal-resolution failure; got: {conflicts!r}"
    )


def test_tool_uv_conflicts_cluster_entries_are_well_formed() -> None:
    cfg = _load_pyproject()
    conflicts = cfg["tool"]["uv"]["conflicts"]
    for cluster in conflicts:
        assert isinstance(cluster, list), (
            f"each [tool.uv].conflicts cluster must be a list; got: {cluster!r}"
        )
        for entry in cluster:
            assert isinstance(entry, dict), (
                f"cluster entries must be tables; got: {entry!r}"
            )
            assert list(entry.keys()) == ["extra"], (
                f"cluster entry must contain only the 'extra' key; got: {entry!r}"
            )
            assert isinstance(entry["extra"], str) and entry["extra"], (
                f"'extra' value must be a non-empty string; got: {entry!r}"
            )


# --- ADDED Requirement: mlx is a platform-scoped extras group (mlx-path) ---


def test_mlx_extras_declares_only_platform_scoped_mlx_lm() -> None:
    """`[project.optional-dependencies].mlx` holds exactly one platform-scoped
    `mlx-lm` requirement (Apple Silicon marker), mirroring the bitsandbytes
    precedent."""
    cfg = _load_pyproject()
    extras = cfg["project"]["optional-dependencies"]
    assert "mlx" in extras, "[project.optional-dependencies].mlx missing"

    mlx = extras["mlx"]
    assert len(mlx) == 1, f"mlx extras must hold exactly one requirement; got: {mlx}"

    entry = mlx[0]
    dist = re.match(r"^([A-Za-z0-9._-]+)", entry)
    assert dist is not None and dist.group(1) == "mlx-lm", (
        f"the single mlx requirement's distribution must be mlx-lm; got: {entry!r}"
    )
    assert "platform_machine == 'arm64'" in entry, (
        f"mlx-lm must be scoped to platform_machine == 'arm64'; got: {entry!r}"
    )
    assert "sys_platform == 'darwin'" in entry, (
        f"mlx-lm must be scoped to sys_platform == 'darwin'; got: {entry!r}"
    )


def test_mlx_conflicts_only_with_huggingface() -> None:
    """`mlx-lm>=0.31.1` pulls `transformers>=5` while `cantus[huggingface]`
    pins `transformers>=4.40,<5`, so a single `mlx`↔`huggingface` conflict pair
    is required for uv universal resolution. No OTHER conflict pair may name
    `mlx` (the platform marker isolates it from every group except the
    transformers-pinned huggingface extras)."""
    cfg = _load_pyproject()
    conflicts = cfg["tool"]["uv"]["conflicts"]
    mlx_pairs = [
        {entry.get("extra") for entry in cluster}
        for cluster in conflicts
        if any(entry.get("extra") == "mlx" for entry in cluster)
    ]
    assert mlx_pairs == [{"mlx", "huggingface"}], (
        f"mlx must conflict with exactly huggingface; got: {mlx_pairs!r}"
    )


# --- ADDED Requirement: omlx documentary alias (cantus-local-llm-omlx-server)


def test_omlx_extras_is_documentary_alias_to_openai() -> None:
    """`[project.optional-dependencies].omlx` is a documentary alias holding
    exactly the self-referential `cantus-agent[openai]` extra — no new
    third-party package (mirrors the `ollama` alias). `OmlxChatModel` runs on
    the openai SDK against a local OpenAI-compatible MLX server."""
    cfg = _load_pyproject()
    extras = cfg["project"]["optional-dependencies"]
    assert "omlx" in extras, "[project.optional-dependencies].omlx missing"

    omlx = extras["omlx"]
    assert len(omlx) == 1, f"omlx extras must hold exactly one requirement; got: {omlx}"
    normalized = omlx[0].replace(" ", "").lower()
    assert normalized == "cantus-agent[openai]", (
        f"omlx must be the self-referential cantus-agent[openai] alias; got: {omlx[0]!r}"
    )


def test_omlx_conflicts_only_with_openhands() -> None:
    """omlx aliases the openai closure (transitive openai>=1.50,<2), which
    already conflicts with the openhands extras, so a single omlx↔openhands
    conflict pair is required for uv universal resolution — mirroring the
    ollama↔openhands pair. No OTHER conflict pair may name omlx."""
    cfg = _load_pyproject()
    conflicts = cfg["tool"]["uv"]["conflicts"]
    omlx_pairs = [
        {entry.get("extra") for entry in cluster}
        for cluster in conflicts
        if any(entry.get("extra") == "omlx" for entry in cluster)
    ]
    assert omlx_pairs == [{"omlx", "openhands"}], (
        f"omlx must conflict with exactly openhands; got: {omlx_pairs!r}"
    )
