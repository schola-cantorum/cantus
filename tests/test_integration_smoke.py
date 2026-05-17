"""ARCH-2 integration smoke tests — adapter / Tier 2 isolation guarantees.

These tests fork fresh Python subprocesses so that modules already imported
by the test runner (openai, anthropic — pulled in by the adapter tests) do
not pollute the `sys.modules` snapshot we are inspecting.
"""

from __future__ import annotations

import subprocess
import sys

import pytest


def _run_in_fresh_subprocess(script: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_core_import_does_not_transitively_load_provider_sdks():
    """`import cantus` must leave `openai` and `anthropic` out of sys.modules.

    Protects the dual-tier API boundary: a Tier 1 student using only Gemma
    must not pay the import cost (or supply-chain exposure) of cloud SDKs.
    """
    script = """
import sys
assert 'openai' not in sys.modules, 'openai leaked before import cantus'
assert 'anthropic' not in sys.modules, 'anthropic leaked before import cantus'
import cantus
assert 'openai' not in sys.modules, f'openai leaked after import cantus: {sorted(m for m in sys.modules if m.startswith("openai"))}'
assert 'anthropic' not in sys.modules, f'anthropic leaked after import cantus: {sorted(m for m in sys.modules if m.startswith("anthropic"))}'
print('OK')
"""
    code, out, err = _run_in_fresh_subprocess(script)
    assert code == 0, f"subprocess failed: stdout={out!r} stderr={err!r}"
    assert "OK" in out


def test_using_adapter_loads_its_sdk_on_first_client_construction():
    """The provider SDK must load on first chat()/stream() call (lazy client)."""
    script = """
import os
import sys
os.environ['OPENAI_API_KEY'] = 'sk-test'
from cantus.model.providers.openai import OpenAIChatModel
# Importing the class alone is cheap — SDK not yet loaded.
assert 'openai' not in sys.modules, f'openai loaded too eagerly: {sorted(m for m in sys.modules if m.startswith("openai"))}'
m = OpenAIChatModel(model_id='gpt-4o-mini')
# Constructor still does not pull the SDK.
assert 'openai' not in sys.modules
# Touching _get_client() triggers the SDK import.
m._get_client()
assert 'openai' in sys.modules
print('OK')
"""
    code, out, err = _run_in_fresh_subprocess(script)
    assert code == 0, f"subprocess failed: stdout={out!r} stderr={err!r}"
    assert "OK" in out


def test_load_chat_model_factory_does_not_eagerly_load_other_provider_sdks():
    """Calling load_chat_model('openai/...') must NOT import anthropic."""
    script = """
import os
import sys
os.environ['OPENAI_API_KEY'] = 'sk-test'
import cantus
assert 'openai' not in sys.modules
assert 'anthropic' not in sys.modules
m = cantus.load_chat_model('openai/gpt-4o-mini')
# Factory dispatched to the openai adapter module (which imports cantus internals
# only); the openai SDK itself loads on first _get_client() call.
assert 'anthropic' not in sys.modules, 'anthropic was eagerly imported by openai dispatch'
m._get_client()
assert 'openai' in sys.modules
assert 'anthropic' not in sys.modules
print('OK')
"""
    code, out, err = _run_in_fresh_subprocess(script)
    assert code == 0, f"subprocess failed: stdout={out!r} stderr={err!r}"
    assert "OK" in out


def test_core_import_does_not_leak_google_or_groq_sdks_to_sys_modules():
    """`import cantus` must not transitively load google.genai / groq either.

    Extends the v0.2.0 openai/anthropic guarantee to the v0.2.1 batch.
    NVIDIA is intentionally not listed because its runtime SDK is `openai`
    (the dedicated `import cantus` openai-isolation test above already
    covers the NVIDIA path transitively).
    """
    script = """
import sys
for name in ('google.genai', 'groq'):
    assert name not in sys.modules, f'{name!r} leaked before import cantus'
import cantus
leaked = [m for m in sys.modules if m.startswith(('google.genai', 'groq'))]
assert not leaked, f'provider SDK leaked after import cantus: {leaked}'
print('OK')
"""
    code, out, err = _run_in_fresh_subprocess(script)
    assert code == 0, f"subprocess failed: stdout={out!r} stderr={err!r}"
    assert "OK" in out


def _is_module_importable(name: str) -> bool:
    import importlib.util

    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


@pytest.mark.skipif(
    not _is_module_importable("google.genai"),
    reason="google-genai SDK not installed; positive-case smoke needs it",
)
def test_explicit_google_adapter_import_loads_google_genai():
    script = """
import os
import sys
os.environ['GOOGLE_API_KEY'] = 'ai-test'
assert 'google.genai' not in sys.modules
from cantus.model.providers.google import GoogleChatModel
# Class import is cheap — SDK still not loaded.
assert 'google.genai' not in sys.modules
m = GoogleChatModel(model_id='gemini-2.0-flash')
assert 'google.genai' not in sys.modules
m._get_client()
assert 'google.genai' in sys.modules
print('OK')
"""
    code, out, err = _run_in_fresh_subprocess(script)
    assert code == 0, f"subprocess failed: stdout={out!r} stderr={err!r}"
    assert "OK" in out


@pytest.mark.skipif(
    not _is_module_importable("groq"),
    reason="groq SDK not installed; positive-case smoke needs it",
)
def test_explicit_groq_adapter_import_loads_groq():
    script = """
import os
import sys
os.environ['GROQ_API_KEY'] = 'gsk-test'
assert 'groq' not in sys.modules
from cantus.model.providers.groq import GroqChatModel
assert 'groq' not in sys.modules
m = GroqChatModel(model_id='llama-3.3-70b-versatile')
assert 'groq' not in sys.modules
m._get_client()
assert 'groq' in sys.modules
print('OK')
"""
    code, out, err = _run_in_fresh_subprocess(script)
    assert code == 0, f"subprocess failed: stdout={out!r} stderr={err!r}"
    assert "OK" in out
