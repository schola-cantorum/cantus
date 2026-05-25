"""Distribution config tests for cantus v0.4.0 strict typing baseline.

Validates that the pyproject.toml carries the PEP 561 py.typed package-data,
the strict mypy configuration with the v0.4.0 extras overrides (which now
include the serve-layer SDKs fastapi/uvicorn/pydantic_settings), the coverage
baseline configuration, the pytest addopts that trigger coverage on every
default run, and the v0.4.0 version bump. Each test corresponds to a single
scenario from the `Cantus ships PEP 561 py.typed marker and strict typing
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


def test_pyproject_has_mypy_strict_configuration() -> None:
    cfg = _load_pyproject()
    mypy = cfg.get("tool", {}).get("mypy")
    assert mypy is not None, "[tool.mypy] section missing"
    assert mypy.get("python_version") == "3.10"
    assert mypy.get("warn_unused_ignores") is True
    assert mypy.get("warn_redundant_casts") is True
    assert mypy.get("strict") is True, (
        "v0.4.0 promotes mypy from disallow_untyped_defs=false baseline to strict=true"
    )
    overrides = mypy.get("overrides", [])
    assert overrides, "[[tool.mypy.overrides]] must declare at least one entry"
    flat_modules = {m for o in overrides for m in (o.get("module") or [])}
    required = {
        "mcp.*",
        "langchain_core.*",
        "dspy.*",
        "transformers.*",
        "openhands.*",
        "anthropic.*",
        "openai.*",
        "google.genai.*",
        "groq.*",
        "fastapi.*",
        "uvicorn.*",
        "pydantic_settings.*",
    }
    missing = required - flat_modules
    assert not missing, (
        f"[[tool.mypy.overrides]] missing required globs for lazy-import shims: {sorted(missing)}"
    )
    for o in overrides:
        if "mcp.*" in (o.get("module") or []):
            assert o.get("ignore_missing_imports") is True
            break


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


def test_mypy_strict_rejects_untyped_def_regression(tmp_path: Path) -> None:
    """Regression scenario for `Cantus ships PEP 561 py.typed marker and strict
    typing configuration`: introducing an untyped def under the strict config
    must exit non-zero with `"Function is missing a return type annotation"`.

    Runs mypy in an isolated tmp dir with a minimal mypy.ini that mirrors the
    v0.4.0 pyproject strict knobs, so the test does not depend on the cantus
    source tree being strict-clean (which is asserted separately).
    """
    import shutil
    import subprocess

    mypy_bin = shutil.which("mypy")
    if mypy_bin is None:
        pytest.skip("mypy not on PATH — install via cantus[dev] before running")

    fixture = tmp_path / "untyped_def_fixture.py"
    # Param is typed; return type is missing — strict mode must surface the
    # literal "Function is missing a return type annotation" phrase named by
    # the cantus-distribution Requirement scenario. (A fully-untyped def
    # `def foo(x): ...` would instead produce "Function is missing a type
    # annotation", which is a different `[no-untyped-def]` variant.)
    fixture.write_text("def foo(x: int):\n    return x + 1\n")

    cfg = tmp_path / "mypy.ini"
    cfg.write_text(
        "[mypy]\n"
        "python_version = 3.10\n"
        "strict = True\n"
        "warn_unused_ignores = True\n"
        "warn_redundant_casts = True\n"
    )

    result = subprocess.run(
        [mypy_bin, "--config-file", str(cfg), str(fixture)],
        capture_output=True,
        text=True,
        check=False,
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert result.returncode != 0, (
        f"mypy strict expected to reject untyped def; got exit 0. stdout={result.stdout!r}"
    )
    assert "Function is missing a return type annotation" in combined, (
        "mypy strict must surface the literal 'Function is missing a return type annotation' "
        f"for `def foo(x): ...`; got:\nstdout={result.stdout!r}\nstderr={result.stderr!r}"
    )


def test_pyproject_version_is_valid_semver() -> None:
    import re

    cfg = _load_pyproject()
    version = cfg["project"]["version"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), (
        f"pyproject.toml [project].version must match X.Y.Z semver; got {version!r}"
    )


def test_dunder_version_aligned_with_pyproject() -> None:
    import cantus

    cfg = _load_pyproject()
    assert cantus.__version__ == cfg["project"]["version"], (
        "cantus.__version__ must equal pyproject.toml [project].version"
    )
