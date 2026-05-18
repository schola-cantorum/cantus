"""Soul — identity loaded from a SOUL.md file with six H2 sections."""

from __future__ import annotations

from pathlib import Path

import pytest

from cantus.identity import Soul, SoulParseError

FIXTURES = Path(__file__).parent / "fixtures"


# --- Task 3.1: parsing ----------------------------------------------------


def test_full_parse():
    soul = Soul.from_file(FIXTURES / "soul_full.md")
    assert soul.name_and_role
    assert soul.personality
    assert soul.rules
    assert soul.tools
    assert soul.output_format
    assert soul.handoffs


def test_missing_sections():
    with pytest.raises(SoulParseError) as info:
        Soul.from_file(FIXTURES / "soul_missing_two.md")
    err = info.value
    assert set(err.missing_sections) == {"Output format", "Handoffs"}
    assert err.duplicates == []
    assert err.unexpected == []


def test_duplicate_sections():
    with pytest.raises(SoulParseError) as info:
        Soul.from_file(FIXTURES / "soul_duplicate_rules.md")
    err = info.value
    assert "Rules" in err.duplicates
    assert err.missing_sections == []


def test_missing_file_raises_fnf(tmp_path):
    with pytest.raises(FileNotFoundError) as info:
        Soul.from_file(tmp_path / "nonexistent.md")
    assert not isinstance(info.value, SoulParseError)


def test_wrong_case_header_reported_missing_plus_unexpected():
    with pytest.raises(SoulParseError) as info:
        Soul.from_file(FIXTURES / "soul_wrongcase_name.md")
    err = info.value
    assert "Name & Role" in err.missing_sections
    assert "name & Role" in err.unexpected
    assert err.duplicates == []


def test_unrecognised_h2_rejected():
    with pytest.raises(SoulParseError) as info:
        Soul.from_file(FIXTURES / "soul_extra_examples.md")
    err = info.value
    assert "Examples" in err.unexpected


# --- Task 3.2: rendering --------------------------------------------------


def test_to_system_prompt_deterministic():
    soul = Soul.from_file(FIXTURES / "soul_full.md")
    out1 = soul.to_system_prompt()
    out2 = soul.to_system_prompt()
    assert out1 == out2
    assert out1.startswith("## Name & Role")
    assert not out1.startswith("\n")


def test_to_system_prompt_round_trip():
    soul1 = Soul.from_file(FIXTURES / "soul_full.md")
    soul2 = Soul.from_text(soul1.to_system_prompt())
    for attr in (
        "name_and_role",
        "personality",
        "rules",
        "tools",
        "output_format",
        "handoffs",
    ):
        assert getattr(soul1, attr) == getattr(soul2, attr), f"diverged on {attr}"
