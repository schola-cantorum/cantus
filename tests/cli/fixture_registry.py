"""Top-level Registry fixture for cantus CLI tests.

Provides a no-skill `Registry()` instance importable as
`tests.cli.fixture_registry:registry`, used by tests that exercise
`--registry-import` resolution and end-to-end CLI flow.
"""

from cantus.core.registry import Registry
from cantus.serve.channel import LocalMockReceiver

registry = Registry()
dashboard_registry = Registry()
not_a_registry = "I am a str, not a Registry"
not_a_channel = "hello"
mock_channel = LocalMockReceiver()
