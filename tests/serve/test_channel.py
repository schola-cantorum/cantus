"""Tests for cantus.serve.channel (v0.4.0 cantus-serve-core).

Each test corresponds to one scenario from the
`Channel Protocol defines bidirectional channel contract` and
`LocalMockReceiver provides in-memory channel for ARCH-2 smoke test`
Requirements in the cantus-serve-core capability.
"""

from __future__ import annotations

import importlib
from typing import Any

import pytest


def _load_module() -> Any:
    return importlib.import_module("cantus.serve.channel")


# --- Channel Protocol — runtime checkable ---------------------------------


def test_channel_protocol_accepts_class_with_receive_and_send() -> None:
    channel_mod = _load_module()

    class _ConformingChannel:
        def receive(self) -> dict[str, Any]:
            return {}

        def send(self, message: dict[str, Any]) -> None:
            return None

    obj = _ConformingChannel()
    assert isinstance(obj, channel_mod.Channel) is True


def test_channel_protocol_rejects_class_missing_send() -> None:
    channel_mod = _load_module()

    class _PartialChannel:
        def receive(self) -> dict[str, Any]:
            return {}

    assert isinstance(_PartialChannel(), channel_mod.Channel) is False


def test_channel_protocol_rejects_class_missing_receive() -> None:
    channel_mod = _load_module()

    class _PartialChannel:
        def send(self, message: dict[str, Any]) -> None:
            return None

    assert isinstance(_PartialChannel(), channel_mod.Channel) is False


# --- LocalMockReceiver FIFO behaviour -------------------------------------


def test_local_mock_receiver_send_receive_fifo() -> None:
    channel_mod = _load_module()
    ch = channel_mod.LocalMockReceiver()
    ch.send({"a": 1})
    ch.send({"a": 2})
    assert ch.receive() == {"a": 1}
    assert ch.receive() == {"a": 2}


def test_local_mock_receiver_empty_queue_raises_indexerror() -> None:
    channel_mod = _load_module()
    ch = channel_mod.LocalMockReceiver()
    with pytest.raises(IndexError, match="LocalMockReceiver queue is empty"):
        ch.receive()


def test_local_mock_receiver_send_rejects_non_dict_string() -> None:
    channel_mod = _load_module()
    ch = channel_mod.LocalMockReceiver()
    with pytest.raises(TypeError, match="LocalMockReceiver.send expects dict"):
        ch.send("not a dict")  # type: ignore[arg-type]


def test_local_mock_receiver_send_rejects_non_dict_none() -> None:
    channel_mod = _load_module()
    ch = channel_mod.LocalMockReceiver()
    with pytest.raises(TypeError, match="LocalMockReceiver.send expects dict"):
        ch.send(None)  # type: ignore[arg-type]


def test_local_mock_receiver_zero_argument_construction() -> None:
    channel_mod = _load_module()
    # Constructor must accept no positional args (and no Settings dependency).
    instance = channel_mod.LocalMockReceiver()
    assert isinstance(instance, channel_mod.LocalMockReceiver)


def test_local_mock_receiver_conforms_to_channel_protocol() -> None:
    channel_mod = _load_module()
    ch = channel_mod.LocalMockReceiver()
    assert isinstance(ch, channel_mod.Channel) is True


# --- v0.4.5 WebhookChannel Protocol --------------------------------------


def test_webhook_channel_membership() -> None:
    """LocalMockReceiver is a Channel but NOT a WebhookChannel; a class with
    receive+send+mount is both."""
    channel_mod = _load_module()
    ch = channel_mod.LocalMockReceiver()
    assert isinstance(ch, channel_mod.Channel) is True
    assert isinstance(ch, channel_mod.WebhookChannel) is False

    class _StubWebhookChannel:
        def receive(self) -> dict[str, Any]:
            return {}

        def send(self, message: dict[str, Any]) -> None:
            return None

        def mount(self, app: Any) -> None:
            return None

    stub = _StubWebhookChannel()
    assert isinstance(stub, channel_mod.Channel) is True
    assert isinstance(stub, channel_mod.WebhookChannel) is True


def test_webhook_channel_rejects_missing_mount() -> None:
    channel_mod = _load_module()

    class _Almost:
        def receive(self) -> dict[str, Any]:
            return {}

        def send(self, message: dict[str, Any]) -> None:
            return None

    assert isinstance(_Almost(), channel_mod.WebhookChannel) is False


# --- v0.4.6 RealtimeChannel Protocol -------------------------------------


def test_realtime_channel_membership() -> None:
    """Task 2.2 — Requirement: RealtimeChannel Protocol extends Channel with
    connect/disconnect lifecycle.

    A stub implementing receive+send+connect+disconnect passes both Channel
    and RealtimeChannel; LocalMockReceiver passes Channel only;
    LineWebhookChannel passes Channel + WebhookChannel only (sibling
    independence — neither Protocol inherits from the other).
    """
    channel_mod = _load_module()

    class _StubRealtimeChannel:
        def receive(self) -> dict[str, Any]:
            return {}

        def send(self, message: dict[str, Any]) -> None:
            return None

        async def connect(self) -> None:
            return None

        async def disconnect(self) -> None:
            return None

    stub = _StubRealtimeChannel()
    assert isinstance(stub, channel_mod.Channel) is True
    assert isinstance(stub, channel_mod.RealtimeChannel) is True
    # WebhookChannel needs mount(); the stub does not implement it.
    assert isinstance(stub, channel_mod.WebhookChannel) is False

    # Pure Channel — neither sub-Protocol.
    receiver = channel_mod.LocalMockReceiver()
    assert isinstance(receiver, channel_mod.Channel) is True
    assert isinstance(receiver, channel_mod.RealtimeChannel) is False
    assert isinstance(receiver, channel_mod.WebhookChannel) is False


def test_realtime_channel_sibling_independence_with_line_webhook() -> None:
    """Task 2.2 — sibling Protocols stay orthogonal.

    LineWebhookChannel implements receive+send+mount but NOT connect/disconnect.
    It must be Channel + WebhookChannel but NOT RealtimeChannel.
    """
    channel_mod = _load_module()
    from cantus.serve.channels.line import LineWebhookChannel

    line = LineWebhookChannel(
        channel_secret="dummy-secret",
        channel_access_token="dummy-token",
    )
    assert isinstance(line, channel_mod.Channel) is True
    assert isinstance(line, channel_mod.WebhookChannel) is True
    assert isinstance(line, channel_mod.RealtimeChannel) is False


def test_realtime_channel_rejects_missing_lifecycle_methods() -> None:
    """Task 2.2 — RealtimeChannel needs BOTH connect and disconnect.

    A class with connect but no disconnect (or vice versa) fails membership.
    """
    channel_mod = _load_module()

    class _HasConnectOnly:
        def receive(self) -> dict[str, Any]:
            return {}

        def send(self, message: dict[str, Any]) -> None:
            return None

        async def connect(self) -> None:
            return None

    class _HasDisconnectOnly:
        def receive(self) -> dict[str, Any]:
            return {}

        def send(self, message: dict[str, Any]) -> None:
            return None

        async def disconnect(self) -> None:
            return None

    assert isinstance(_HasConnectOnly(), channel_mod.RealtimeChannel) is False
    assert isinstance(_HasDisconnectOnly(), channel_mod.RealtimeChannel) is False


# --- C2.0 cantus-runtime-introspection-api: QueueIntrospectable -----------


def test_queue_introspectable_detects_capability_presence() -> None:
    """A class exposing queue_depth() conforms; one without it does not."""
    channel_mod = _load_module()

    class _HasDepth:
        def queue_depth(self) -> int:
            return 0

    class _NoDepth:
        def receive(self) -> dict[str, Any]:
            return {}

        def send(self, message: dict[str, Any]) -> None:
            return None

    assert isinstance(_HasDepth(), channel_mod.QueueIntrospectable) is True
    assert isinstance(_NoDepth(), channel_mod.QueueIntrospectable) is False


def test_local_mock_receiver_reports_queue_depth() -> None:
    """LocalMockReceiver exposes a read-only queue_depth reflecting buffered
    messages, without altering receive/send semantics."""
    channel_mod = _load_module()

    receiver = channel_mod.LocalMockReceiver()
    assert isinstance(receiver, channel_mod.QueueIntrospectable) is True
    assert receiver.queue_depth() == 0
    receiver.send({"a": 1})
    receiver.send({"b": 2})
    assert receiver.queue_depth() == 2
    # receive() still pops in FIFO order — behaviour unchanged.
    assert receiver.receive() == {"a": 1}
    assert receiver.queue_depth() == 1
