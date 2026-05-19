"""Lazy-import gate tests for cantus.serve and cantus.config.

Each test corresponds to one scenario from the
`cantus.serve module is gated behind cantus[serve] extras` Requirement.

The strategy: temporarily mark one of the serve SDKs (`fastapi`,
`uvicorn`, or `pydantic_settings`) as missing via ``sys.modules`` patching,
then drop the relevant cantus modules from cache and re-import. The
ImportError raised by the gate must contain the literal substring
``"pip install cantus[serve]"``.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator

import pytest


_GATED_CANTUS_MODULES = ["cantus.config", "cantus.serve", "cantus.serve.app",
                         "cantus.serve.channel", "cantus.serve.dashboard"]


@pytest.fixture
def _purge_serve_modules(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Drop cantus.serve / cantus.config and the serve SDKs from sys.modules.

    Ensures the next import re-executes the gate body. Using monkeypatch so
    sys.modules is restored after the test (important — other tests still
    need cantus.serve importable).
    """
    for mod in _GATED_CANTUS_MODULES:
        monkeypatch.delitem(sys.modules, mod, raising=False)
    yield


def _block_module(monkeypatch: pytest.MonkeyPatch, mod_name: str) -> None:
    """Mark ``mod_name`` as missing for subsequent imports.

    Setting the value to ``None`` is the documented way to make
    ``import <mod_name>`` raise ``ModuleNotFoundError`` (see CPython
    docs / PEP 328).
    """
    monkeypatch.setitem(sys.modules, mod_name, None)  # type: ignore[arg-type]


# --- import cantus still works when serve SDKs are missing ----------------


def test_import_cantus_succeeds_without_serve_sdks(
    monkeypatch: pytest.MonkeyPatch,
    _purge_serve_modules: None,
) -> None:
    _block_module(monkeypatch, "fastapi")
    _block_module(monkeypatch, "uvicorn")
    _block_module(monkeypatch, "pydantic_settings")
    monkeypatch.delitem(sys.modules, "cantus", raising=False)

    cantus = importlib.import_module("cantus")
    assert cantus.__version__ == "0.4.0"


# --- cantus.serve gate ---------------------------------------------------


def test_import_cantus_serve_fails_without_fastapi(
    monkeypatch: pytest.MonkeyPatch,
    _purge_serve_modules: None,
) -> None:
    _block_module(monkeypatch, "fastapi")
    with pytest.raises(ImportError, match=r"pip install cantus\[serve\]"):
        importlib.import_module("cantus.serve")


def test_import_cantus_serve_fails_without_uvicorn(
    monkeypatch: pytest.MonkeyPatch,
    _purge_serve_modules: None,
) -> None:
    _block_module(monkeypatch, "uvicorn")
    with pytest.raises(ImportError, match=r"pip install cantus\[serve\]"):
        importlib.import_module("cantus.serve")


def test_import_cantus_serve_fails_without_pydantic_settings(
    monkeypatch: pytest.MonkeyPatch,
    _purge_serve_modules: None,
) -> None:
    _block_module(monkeypatch, "pydantic_settings")
    with pytest.raises(ImportError, match=r"pip install cantus\[serve\]"):
        importlib.import_module("cantus.serve")


# --- cantus.config gate --------------------------------------------------


def test_import_cantus_config_fails_without_pydantic_settings(
    monkeypatch: pytest.MonkeyPatch,
    _purge_serve_modules: None,
) -> None:
    _block_module(monkeypatch, "pydantic_settings")
    with pytest.raises(ImportError, match=r"pip install cantus\[serve\]"):
        importlib.import_module("cantus.config")


# --- happy path (control) ------------------------------------------------


def test_import_cantus_serve_succeeds_when_all_sdks_present() -> None:
    """Control test — when fastapi/uvicorn/pydantic_settings are installed
    in the cantus[dev,serve] virtualenv, the imports succeed and the public
    surface is reachable."""
    from cantus.config import Settings  # noqa: F401
    from cantus.serve import serve  # noqa: F401
