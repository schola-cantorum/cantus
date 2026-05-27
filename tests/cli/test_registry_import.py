"""`--registry-import` dotted-path resolution tests.

Covers Requirement「--registry-import resolves a Registry instance from a
dotted module path」 — four scenarios:

1. Valid dotted path resolves to a `Registry` instance.
2. Missing module → `RegistryImportError`.
3. Missing attribute → `RegistryImportError`.
4. Attribute exists but is not a `Registry` instance → `RegistryImportError`.
"""

from __future__ import annotations

import subprocess
import sys
import types

import pytest

from cantus.cli import (
    RegistryImportError,
    _format_attribute_error,
    _resolve_channels_import,
    _resolve_registry_import,
)
from cantus.core.registry import Registry


def test_valid_import_resolves_registry():
    """Valid `module:attr` returns the bound `Registry` instance.

    Scenario: valid import path resolves to Registry.
    """
    result = _resolve_registry_import("tests.cli.fixture_registry:registry")
    assert isinstance(result, Registry)


def test_missing_module_raises_registry_import_error():
    """Importing a non-existent module raises `RegistryImportError`.

    Scenario: import error surfaces with cantus serve error prefix.
    """
    with pytest.raises(RegistryImportError) as excinfo:
        _resolve_registry_import("definitely.not.a.real.module:registry")
    assert "definitely.not.a.real.module" in str(excinfo.value) or "No module" in str(excinfo.value)


def test_missing_attribute_raises_registry_import_error():
    """Importable module but missing attribute → `RegistryImportError`.

    Scenario: missing attribute surfaces with cantus serve error prefix.
    """
    with pytest.raises(RegistryImportError):
        _resolve_registry_import("tests.cli.fixture_registry:does_not_exist")


def test_non_registry_attribute_raises_registry_import_error():
    """Attribute exists but is not a `Registry` → `RegistryImportError`."""
    with pytest.raises(RegistryImportError) as excinfo:
        _resolve_registry_import("tests.cli.fixture_registry:not_a_registry")
    assert "expected Registry" in str(excinfo.value)


def test_malformed_spec_raises_registry_import_error():
    """Spec without `:` separator raises early before any import."""
    with pytest.raises(RegistryImportError):
        _resolve_registry_import("no_colon_here")


# ---------- H2 (gate-a-audit-hardening): identifier validation + candidate hint


def _module_with(attrs: dict[str, object], name: str = "tests_cli_fake_mod") -> types.ModuleType:
    """Build an in-memory module with the given top-level bindings and register it."""
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


def test_format_attribute_error_caps_at_ten_with_truncated_suffix():
    """`_format_attribute_error` lists at most 10 public attrs + `(truncated)`.

    Task 4.1 contract: helper is a pure function, deterministic on input,
    and degrades long candidate lists with the literal substring
    `(truncated)`.
    """
    attrs = {f"public_{i:02d}": i for i in range(15)}
    attrs["_private"] = "hidden"
    mod = _module_with(attrs, name="tests_cli_fake_many_attrs")
    try:
        msg = _format_attribute_error(mod, "nonexistent", "tests_cli_fake_many_attrs:nonexistent")
        assert "; available:" in msg
        assert "(truncated)" in msg
        assert "_private" not in msg
        # First ten sorted public names (public_00..public_09) MUST be present;
        # the eleventh (public_10) MUST NOT be in the message.
        for i in range(10):
            assert f"public_{i:02d}" in msg, f"missing public_{i:02d} in {msg!r}"
        assert "public_10" not in msg
    finally:
        sys.modules.pop("tests_cli_fake_many_attrs", None)


def test_format_attribute_error_reports_none_when_only_private_attrs():
    """`_format_attribute_error` emits `; available: (none)` for private-only modules.

    Task 4.1 / 4.4 contract: when the module has zero public attributes,
    the helper SHALL surface `(none)` instead of an empty list.
    """
    mod = _module_with({"_a": 1, "_b": 2, "__c": 3}, name="tests_cli_fake_empty_mod")
    try:
        msg = _format_attribute_error(mod, "anything", "tests_cli_fake_empty_mod:anything")
        assert "; available: (none)" in msg
    finally:
        sys.modules.pop("tests_cli_fake_empty_mod", None)


def test_invalid_identifier_attr_name_rejected():
    """`--registry-import "x:bad attr"` is rejected early as invalid identifier.

    Task 4.2 / Scenario: invalid identifier attribute name is rejected early.
    """
    with pytest.raises(RegistryImportError) as excinfo:
        _resolve_registry_import("tests.cli.fixture_registry:bad attr")
    assert "not a valid Python identifier" in str(excinfo.value)


def test_missing_attr_error_lists_candidates():
    """Missing attribute error message includes `; available:` and candidates.

    Task 4.2 / Scenario: missing attribute error lists module candidates.
    """
    with pytest.raises(RegistryImportError) as excinfo:
        _resolve_registry_import("tests.cli.fixture_registry:registr")
    msg = str(excinfo.value)
    assert "; available:" in msg
    assert "registry" in msg
    assert "dashboard_registry" in msg


def test_channels_invalid_identifier_attr_name_rejected():
    """`--channels "x:bad attr"` is rejected as invalid identifier.

    Task 4.3 contract: `_resolve_channels_import` mirrors the helper from
    `_resolve_registry_import`.
    """
    with pytest.raises(RegistryImportError) as excinfo:
        _resolve_channels_import(["tests.cli.fixture_registry:bad attr"])
    assert "not a valid Python identifier" in str(excinfo.value)


def test_missing_attr_reports_none_when_no_public_attrs():
    """Missing-attr message for private-only module ends with `; available: (none)`.

    Task 4.4 / Scenario: missing attribute error reports (none) when module
    has no public attributes.
    """
    _module_with({"_private": "x"}, name="tests_cli_fake_only_private")
    try:
        with pytest.raises(RegistryImportError) as excinfo:
            _resolve_registry_import("tests_cli_fake_only_private:registry")
        assert "; available: (none)" in str(excinfo.value)
    finally:
        sys.modules.pop("tests_cli_fake_only_private", None)


# ---------- M4 (gate-a-audit-hardening): Channel Protocol runtime check ------


def test_channels_non_channel_object_rejected():
    """A non-Channel object in `--channels` is rejected at startup.

    Task 5.1 / Scenario: non-Channel object is rejected at startup.
    """
    with pytest.raises(RegistryImportError) as excinfo:
        _resolve_channels_import(["tests.cli.fixture_registry:not_a_channel"])
    msg = str(excinfo.value)
    assert "expected cantus.serve.channel.Channel-compatible object" in msg
    assert "str" in msg


def test_channels_local_mock_receiver_passes_runtime_check():
    """`LocalMockReceiver()` satisfies the Channel Protocol runtime check.

    Task 5.2 / Scenario: Channel-compatible object passes the runtime check.
    """
    from cantus.serve.channel import LocalMockReceiver

    channels = _resolve_channels_import(["tests.cli.fixture_registry:mock_channel"])
    assert len(channels) == 1
    assert isinstance(channels[0], LocalMockReceiver)


def test_cli_import_does_not_transitively_load_channel_module(tmp_path):
    """`import cantus.cli` MUST NOT pull `cantus.serve.channel` into sys.modules.

    Task 5.3 / Scenario: importing cantus.cli does not transitively load
    cantus.serve.channel. Runs in a fresh subprocess so prior imports in
    this pytest process do not pollute the assertion.
    """
    script = (
        "import sys\n"
        "import cantus.cli  # noqa: F401\n"
        "assert 'cantus.serve.channel' not in sys.modules, "
        "f'cantus.serve.channel leaked into sys.modules via cantus.cli import'\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, (
        f"subprocess failed: stdout={completed.stdout!r} stderr={completed.stderr!r}"
    )
