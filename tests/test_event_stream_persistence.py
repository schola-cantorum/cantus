"""JsonLinesPersistence — append-only JSON-Lines plug for EventStream."""

from __future__ import annotations

import os
import stat
import sys

import pytest

from cantus.core.event_stream_persistence import JsonLinesPersistence


def test_append_load_round_trip(tmp_path):
    p = JsonLinesPersistence(tmp_path / "events.jsonl")
    p.append({"action": "search", "query": "Tainan"})
    events = p.load()
    assert events == [{"action": "search", "query": "Tainan"}]
    content = (tmp_path / "events.jsonl").read_text(encoding="utf-8")
    assert content.endswith("\n")
    assert content.count("\n") == 1


def test_cold_start_empty(tmp_path):
    target = tmp_path / "events-cold.jsonl"
    p = JsonLinesPersistence(target)
    assert p.load() == []
    # load() alone must NOT create the file.
    assert not target.exists()


def test_non_serialisable_no_partial_write(tmp_path):
    target = tmp_path / "events.jsonl"
    target.write_text('{"prior":1}\n', encoding="utf-8")
    p = JsonLinesPersistence(target)
    with pytest.raises(TypeError, match="not JSON serializable"):
        p.append({"x": object()})
    # File content unchanged.
    assert target.read_text(encoding="utf-8") == '{"prior":1}\n'


def test_fsync_called(tmp_path, monkeypatch):
    calls: list[int] = []
    orig_fsync = os.fsync

    def fake_fsync(fd: int) -> None:
        calls.append(fd)
        orig_fsync(fd)

    monkeypatch.setattr(os, "fsync", fake_fsync)
    p = JsonLinesPersistence(tmp_path / "events.jsonl")
    p.append({"k": 1})
    p.append({"k": 2})
    assert len(calls) == 2


def test_file_mode_0600(tmp_path):
    if sys.platform.startswith("win"):
        pytest.skip("POSIX permission semantics not applicable on Windows")
    target = tmp_path / "events-perms.jsonl"
    p = JsonLinesPersistence(target)
    p.append({"k": 1})
    mode = stat.S_IMODE(os.stat(target).st_mode)
    assert mode == 0o600


def test_serialise_failure_does_not_create_file(tmp_path):
    target = tmp_path / "fresh.jsonl"
    p = JsonLinesPersistence(target)
    with pytest.raises(TypeError, match="not JSON serializable"):
        p.append({"x": object()})
    assert not target.exists()
