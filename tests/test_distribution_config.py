"""Distribution config tests for cantus v0.3.5 quality baseline.

Validates that the pyproject.toml carries the PEP 561 py.typed package-data,
the mypy baseline configuration with optional-extras overrides, the coverage
baseline configuration, the pytest addopts that trigger coverage on every
default run, and the v0.3.5 version bump. Each test corresponds to a single
scenario from the `Cantus ships PEP 561 py.typed marker and baseline tool
configuration` Requirement in cantus-distribution.
"""

from __future__ import annotations

import sys
from importlib.resources import files
from pathlib import Path

import pytest

if sys.version_info < (3, 11):
    pytest.skip("tomllib requires Python 3.11+", allow_module_level=True)

import tomllib

_PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _load_pyproject() -> dict:
    with _PYPROJECT.open("rb") as fh:
        return tomllib.load(fh)


def test_py_typed_marker_exists() -> None:
    marker = files("cantus").joinpath("py.typed")
    assert marker.is_file(), "cantus/py.typed missing — PEP 561 marker not shipped"
    assert marker.read_text() == "", "py.typed must be empty per PEP 561 inline-typed convention"


def test_pyproject_has_setuptools_package_data_for_py_typed() -> None:
    cfg = _load_pyproject()
    package_data = (
        cfg.get("tool", {}).get("setuptools", {}).get("package-data", {})
    )
    assert "cantus" in package_data, (
        "[tool.setuptools.package-data] missing the cantus entry"
    )
    assert "py.typed" in package_data["cantus"], (
        "[tool.setuptools.package-data].cantus must list 'py.typed' so the wheel bundles the marker"
    )


def test_pyproject_has_mypy_baseline() -> None:
    cfg = _load_pyproject()
    mypy = cfg.get("tool", {}).get("mypy")
    assert mypy is not None, "[tool.mypy] section missing"
    assert mypy.get("python_version") == "3.10"
    assert mypy.get("warn_unused_ignores") is True
    assert mypy.get("warn_redundant_casts") is True
    assert mypy.get("check_untyped_defs") is True
    assert mypy.get("disallow_untyped_defs") is False
    overrides = mypy.get("overrides", [])
    assert overrides, "[[tool.mypy.overrides]] must declare at least one entry"
    mcp_override = next(
        (
            o
            for o in overrides
            if "mcp.*" in (o.get("module") or [])
        ),
        None,
    )
    assert mcp_override is not None, (
        "[[tool.mypy.overrides]] must cover 'mcp.*' so a bare cantus[dev] install does not fail on the lazy adapter import"
    )
    assert mcp_override.get("ignore_missing_imports") is True


def test_pyproject_has_coverage_baseline() -> None:
    cfg = _load_pyproject()
    coverage = cfg.get("tool", {}).get("coverage", {})
    run = coverage.get("run")
    report = coverage.get("report")
    assert run is not None, "[tool.coverage.run] section missing"
    assert run.get("source") == ["cantus"]
    assert run.get("branch") is True
    assert report is not None, "[tool.coverage.report] section missing"
    assert report.get("show_missing") is True
    exclude_lines = report.get("exclude_lines", [])
    assert "pragma: no cover" in exclude_lines
    assert "if TYPE_CHECKING:" in exclude_lines


def test_pytest_addopts_triggers_cov() -> None:
    cfg = _load_pyproject()
    addopts = (
        cfg.get("tool", {})
        .get("pytest", {})
        .get("ini_options", {})
        .get("addopts", "")
    )
    assert isinstance(addopts, str), "addopts must be a string"
    assert "--cov=cantus" in addopts, (
        "addopts must trigger coverage against the cantus package by default"
    )
    assert "--cov-report=term-missing" in addopts, (
        "addopts must emit a term-missing coverage report on every default pytest run"
    )


def test_pyproject_version_bumped_to_0_3_5() -> None:
    cfg = _load_pyproject()
    assert cfg["project"]["version"] == "0.3.5"
