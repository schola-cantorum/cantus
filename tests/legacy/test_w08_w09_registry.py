"""W8 (get_registry) and W9 (kind "skill", spec_for_llm key "skill"): legacy halves."""

import copy
import pickle
import warnings

import pytest

import cantus
from cantus import register_tool, tool
from cantus.core.registry import Registry, _get_global_registry
from tests.legacy.support import EXPECTED, cantus_records


def _w(caught, text):
    """Records of the cantus category carrying exactly this text."""
    return [
        w
        for w in caught
        if w.category is cantus.CantusDeprecationWarning and str(w.message) == text
    ]


class _Dummy:
    name = "dummy"


# --- Row 18 -----------------------------------------------------------------


def test_kind_skill_is_kind_tool_in_all_three_methods_with_w9_each_time():
    reg = Registry()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        reg.register("skill", _Dummy())  # line A
        found_by_tool = reg.lookup("tool", "dummy")
        found_by_skill = reg.lookup("skill", "dummy")  # line B
        names_by_skill = reg.names_for("skill")  # line C
        reg.register("tool", _Dummy())
    assert found_by_tool is not None
    assert found_by_tool is found_by_skill
    assert names_by_skill == ["dummy"]
    assert reg.names_for("tool") == ["dummy"]
    records = cantus_records(caught)
    assert len(records) == 3
    for record in records:
        assert record.category is cantus.CantusDeprecationWarning
        assert str(record.message) == EXPECTED["W9"]
        assert record.filename == __file__
    assert len(records) == len(_w(caught, EXPECTED["W9"]))


# --- Row 20 (legacy half) ---------------------------------------------------


def test_register_kind_skill_without_a_name_warns_first_then_raises_with_the_tool_text():
    class Anon:
        name = ""

    reg = Registry()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(ValueError) as excinfo:
            reg.register("skill", Anon())
    assert str(excinfo.value) == (
        "Cannot register tool without a `name` attribute on the instance"
    )
    assert [str(w.message) for w in cantus_records(caught)] == [EXPECTED["W9"]]


# --- Row 22 -----------------------------------------------------------------


def _spec_with_one_tool():
    @tool
    def alpha(x: int) -> int:
        """A."""
        return x

    reg = Registry()
    register_tool(alpha, registry=reg)
    return reg.spec_for_llm()


def test_spec_skill_key_answers_like_tool_with_w9_on_each_use():
    spec = _spec_with_one_tool()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        by_item = spec["skill"]  # line A
        by_get = spec.get("skill")  # line B
        has_key = "skill" in spec  # line C
    assert by_item is spec["tool"]
    assert by_get is spec["tool"]
    assert has_key is True
    records = cantus_records(caught)
    assert [str(w.message) for w in records] == [EXPECTED["W9"]] * 3
    assert all(w.category is cantus.CantusDeprecationWarning for w in records)
    assert all(w.filename == __file__ for w in records)
    assert len({w.lineno for w in records}) == 3


def test_spec_tool_key_and_unknown_keys_do_not_warn_or_alias():
    spec = _spec_with_one_tool()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert spec["tool"] is spec.get("tool")
        assert "tool" in spec
        assert spec.get("nope") is None
        assert "nope" not in spec
        with pytest.raises(KeyError):
            spec["nope"]
    assert cantus_records(caught) == []


# --- Row 23 -----------------------------------------------------------------


def test_spec_equality_copies_and_pickle_follow_the_dict_content():
    spec = _spec_with_one_tool()
    content = {"tool": spec["tool"]}
    assert spec == content
    assert spec != {"skill": spec["tool"]}  # legacy-alias
    for plain in (dict(spec), spec.copy()):
        assert plain == content
        assert type(plain) is dict
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            assert "skill" not in plain
        assert cantus_records(caught) == []
    for clone in (copy.copy(spec), copy.deepcopy(spec), pickle.loads(pickle.dumps(spec))):
        assert clone == content


# --- Row 16 -----------------------------------------------------------------


def test_get_registry_returns_the_global_registry_and_warns_w8_each_call():
    from cantus import get_registry, skill

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        @skill
        def registered(x: int) -> int:
            """R."""
            return x

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        first = get_registry()  # line A
        second = get_registry()  # line B
    assert first is second
    assert first is _get_global_registry()
    assert "registered" in first.names_for("tool")
    records = cantus_records(caught)
    assert [str(w.message) for w in records] == [EXPECTED["W8"]] * 2
    assert all(w.category is cantus.CantusDeprecationWarning for w in records)
    assert all(w.filename == __file__ for w in records)
    assert records[0].lineno != records[1].lineno
