"""W14 (SkillsPane), W15 (active_skill_names) and W17 (update_skills): the legacy TUI names."""

import warnings

import pytest

pytest.importorskip("textual")

import cantus  # noqa: E402
import cantus.tui.widgets  # noqa: E402
from tests.legacy.support import (  # noqa: E402
    EXPECTED,
    cantus_records,
    import_module_from,
    run_python,
    write_module,
)

_ROWS = [
    {
        "name": "echo",
        "description": "echo back",
        "args_schema": {"type": "object", "properties": {"text": {}}},
    },
    {"name": "sum", "description": "add numbers", "args_schema": {}},
]


def _bare_app():
    from textual.app import App

    class BareApp(App):
        def compose(self):
            yield cantus.tui.widgets.ToolsPane()

    return BareApp()


# --- Row 9: SkillsPane (W14) --------------------------------------------------


def test_skills_pane_resolves_to_tools_pane_with_one_w14_at_the_accessing_line(tmp_path):
    write_module(
        tmp_path,
        "reach_skills_pane",
        "import cantus.tui.widgets as widgets\n\ncls = widgets.SkillsPane\n",
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        reached = import_module_from(tmp_path, "reach_skills_pane")

    assert reached.cls is cantus.tui.widgets.ToolsPane
    records = cantus_records(caught)
    assert len(records) == 1
    assert records[0].category is cantus.CantusDeprecationWarning
    assert str(records[0].message) == EXPECTED["W14"]
    assert records[0].filename == str(tmp_path / "reach_skills_pane.py")
    assert records[0].lineno == 3


def test_from_import_of_skills_pane_prints_the_w14_text_once_under_default_filters(tmp_path):
    result = run_python(["-c", "from cantus.tui.widgets import SkillsPane"], cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stderr.count(EXPECTED["W14"]) == 1


@pytest.mark.anyio("asyncio")
async def test_a_subclass_of_the_legacy_pane_is_found_as_a_tools_pane():
    from textual.app import App
    from textual.widgets import DataTable

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        class Mine(cantus.tui.widgets.SkillsPane):
            pass

    class SubApp(App):
        def compose(self):
            yield Mine()

    app = SubApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        pane = app.query_one(cantus.tui.widgets.ToolsPane)
        assert isinstance(pane, Mine)
        assert isinstance(pane, DataTable)


# --- Row 10: active_skill_names (W15) ------------------------------------------


def test_active_skill_names_is_active_tool_names_with_one_w15_at_the_accessing_line(tmp_path):
    write_module(
        tmp_path,
        "reach_active_names",
        "import cantus.tui.widgets as widgets\n\n\n"
        "def reach():\n"
        "    return widgets.active_skill_names\n",
    )
    module = import_module_from(tmp_path, "reach_active_names")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        reached = module.reach()

    assert reached is cantus.tui.widgets.active_tool_names
    records = cantus_records(caught)
    assert len(records) == 1
    assert records[0].category is cantus.CantusDeprecationWarning
    assert str(records[0].message) == EXPECTED["W15"]
    assert records[0].filename == str(tmp_path / "reach_active_names.py")
    assert records[0].lineno == 5


def test_from_import_of_active_skill_names_prints_the_w15_text_once(tmp_path):
    result = run_python(["-c", "from cantus.tui.widgets import active_skill_names"], cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stderr.count(EXPECTED["W15"]) == 1


def test_the_legacy_active_names_function_reads_v06_shaped_sessions():
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        legacy = cantus.tui.widgets.active_skill_names
    sessions = [{"source": "skill:echo", "status": "running"}]

    assert legacy(sessions) == {"echo"}


# --- Row 11: update_skills (W17) ------------------------------------------------


@pytest.mark.anyio("asyncio")
async def test_update_skills_fills_the_rows_and_emits_one_w17_per_call_at_the_calling_line(
    tmp_path,
):
    write_module(
        tmp_path,
        "call_update_skills",
        "def call(pane, rows):\n"
        "    pane.update_skills(rows, {'echo'})\n"
        "\n"
        "\n"
        "def call_keywords(pane, rows):\n"
        "    pane.update_skills(skills=rows, active=set())\n",
    )
    module = import_module_from(tmp_path, "call_update_skills")
    app = _bare_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        pane = app.query_one(cantus.tui.widgets.ToolsPane)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            module.call(pane, _ROWS)
        records = cantus_records(caught)
        assert len(records) == 1
        assert records[0].category is cantus.CantusDeprecationWarning
        assert str(records[0].message) == EXPECTED["W17"]
        assert records[0].filename == str(tmp_path / "call_update_skills.py")
        assert records[0].lineno == 2
        assert tuple(pane.get_row_at(0)) == ("echo", "echo back", "text", "active")
        assert tuple(pane.get_row_at(1)) == ("sum", "add numbers", "—", "")
        assert pane.row_count == 2

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            module.call_keywords(pane, _ROWS)
        records = cantus_records(caught)
        assert len(records) == 1
        assert str(records[0].message) == EXPECTED["W17"]
        assert records[0].lineno == 6
        assert tuple(pane.get_row_at(0)) == ("echo", "echo back", "text", "")


def test_update_skills_prints_the_w17_text_once_under_default_filters(tmp_path):
    code = (
        "import asyncio\n"
        "from textual.app import App\n"
        "from cantus.tui.widgets import ToolsPane\n"
        "\n"
        "class BareApp(App):\n"
        "    def compose(self):\n"
        "        yield ToolsPane()\n"
        "\n"
        "async def main():\n"
        "    app = BareApp()\n"
        "    async with app.run_test() as pilot:\n"
        "        await pilot.pause()\n"
        "        app.query_one(ToolsPane).update_skills([], set())\n"
        "\n"
        "asyncio.run(main())\n"
    )
    result = run_python(["-c", code], cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stderr.count(EXPECTED["W17"]) == 1
    assert result.stderr.count("is deprecated since cantus") == 1


# --- Row 12: the names stay out of the public surface ---------------------------


def test_legacy_names_are_not_in_all_and_not_bound_in_the_module():
    assert "SkillsPane" not in cantus.tui.widgets.__all__
    assert "active_skill_names" not in cantus.tui.widgets.__all__
    assert "SkillsPane" not in vars(cantus.tui.widgets)
    assert "active_skill_names" not in vars(cantus.tui.widgets)


def test_an_unknown_name_raises_attribute_error():
    with pytest.raises(AttributeError):
        getattr(cantus.tui.widgets, "no_such_name")
