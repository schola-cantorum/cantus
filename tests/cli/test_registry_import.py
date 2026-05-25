"""`--registry-import` dotted-path resolution tests.

Covers Requirement「--registry-import resolves a Registry instance from a
dotted module path」 — four scenarios:

1. Valid dotted path resolves to a `Registry` instance.
2. Missing module → `RegistryImportError`.
3. Missing attribute → `RegistryImportError`.
4. Attribute exists but is not a `Registry` instance → `RegistryImportError`.
"""

from __future__ import annotations

import pytest

from cantus.cli import RegistryImportError, _resolve_registry_import
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
