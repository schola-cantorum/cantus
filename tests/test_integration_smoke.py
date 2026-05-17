"""ARCH-2 integration smoke tests — adapter / Tier 2 isolation guarantees.

These tests fork fresh Python subprocesses so that modules already imported
by the test runner (openai, anthropic — pulled in by the adapter tests) do
not pollute the `sys.modules` snapshot we are inspecting.
"""

from __future__ import annotations

import subprocess
import sys


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
