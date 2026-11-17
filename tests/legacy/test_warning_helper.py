"""The deprecation-warning helper: category, texts, attribution, W13 path, single emitter."""

import _thread
import ast
import importlib.machinery
import threading
import types
import warnings
from pathlib import Path

import pytest

import cantus
from tests.legacy.support import EXPECTED, cantus_records


# --- Row 1 ------------------------------------------------------------------


def test_cantus_deprecation_warning_is_exported_deprecation_subclass():
    assert "CantusDeprecationWarning" in cantus.__all__
    assert issubclass(cantus.CantusDeprecationWarning, DeprecationWarning)


# --- Row 2 ------------------------------------------------------------------


def _split(key):
    w_id, _, variant = key.partition(":")
    return w_id, (variant or None)


@pytest.mark.parametrize("key", sorted(EXPECTED))
def test_every_table_id_emits_its_section_2_4_text(key):
    from cantus._deprecation import warn_legacy

    w_id, variant = _split(key)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        warn_legacy(w_id, variant=variant)
    records = cantus_records(caught)
    assert len(records) == 1
    assert records[0].category is cantus.CantusDeprecationWarning
    assert str(records[0].message) == EXPECTED[key]


def test_table_ids_are_exactly_w1_to_w18():
    from cantus import _deprecation

    assert set(_deprecation._TABLE) == set(EXPECTED)
    ids = {key.partition(":")[0] for key in _deprecation._TABLE}
    assert ids == {f"W{n}" for n in range(1, 19)}


# --- Row 3 ------------------------------------------------------------------

_CALLER_SRC = "from cantus._deprecation import warn_legacy\n\ndef go():\n    warn_legacy('W2')\n"


class _SourceLoader:
    """Loader stand-in that serves the module's own source, as a real loader would."""

    def __init__(self, source):
        self._source = source

    def get_source(self, name):
        return self._source


def _module(name, source, filename):
    loader = _SourceLoader(source)
    mod = types.ModuleType(name)
    mod.__loader__ = loader
    mod.__spec__ = importlib.machinery.ModuleSpec(name, loader)
    exec(compile(source, filename, "exec"), mod.__dict__)
    return mod


def _record(fn):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fn()
    records = cantus_records(caught)
    assert len(records) == 1
    return records[0]


def test_attribution_skips_cantus_frames_to_the_first_outside_frame():
    inner = _module("cantus.x", _CALLER_SRC, "/pkg/cantus/x.py")
    record = _record(inner.go)
    assert record.filename == __file__


def test_attribution_treats_cantus_homework_as_a_student_frame():
    homework = _module("cantus_homework", _CALLER_SRC, "/fake/homework.py")
    record = _record(homework.go)
    assert record.filename == "/fake/homework.py"
    assert record.lineno == 4


def test_attribution_skips_importlib_bootstrap_frames():
    inner = _module("cantus.x", _CALLER_SRC, "/pkg/cantus/x.py")
    boot = _module(
        "importlib._bootstrap",
        "def call(fn):\n    fn()\n",
        "<frozen importlib._bootstrap>",
    )
    record = _record(lambda: boot.call(inner.go))
    assert record.filename == __file__


def test_attribution_does_not_skip_a_student_module_named_like_the_bootstrap_file():
    student = _module("hw", _CALLER_SRC, "/srv/importlib_practice/_bootstrap_hw.py")
    record = _record(student.go)
    assert record.filename == "/srv/importlib_practice/_bootstrap_hw.py"


def test_attribution_without_an_outside_frame_uses_the_outermost_frame():
    # A raw thread has no threading.py frame below its target, so every frame is cantus.
    outer = _module(
        "cantus.y",
        "from cantus._deprecation import warn_legacy\n\n"
        "def start():\n    try:\n        warn_legacy('W2')\n    finally:\n        done.set()\n",
        "/pkg/cantus/y.py",
    )
    outer.done = threading.Event()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _thread.start_new_thread(outer.start, ())
        assert outer.done.wait(10)
    records = cantus_records(caught)
    assert len(records) == 1
    assert records[0].filename == "/pkg/cantus/y.py"


def test_record_module_is_the_attributed_frames_module_name():
    helper = _module("helpermod", _CALLER_SRC, "/fake/helpermod.py")
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        warnings.filterwarnings("error", category=DeprecationWarning, module="helpermod")
        with pytest.raises(cantus.CantusDeprecationWarning):
            helper.go()


# --- Row 4 ------------------------------------------------------------------


@pytest.mark.parametrize("category", [DeprecationWarning, cantus.CantusDeprecationWarning])
def test_w13_is_never_raised_but_other_ids_are(category):
    from cantus._deprecation import warn_legacy

    with warnings.catch_warnings():
        warnings.simplefilter("error", category)
        warn_legacy("W13")  # returns normally
        with pytest.raises(cantus.CantusDeprecationWarning):
            warn_legacy("W2")


# --- Row 5 ------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parents[2] / "cantus"
_ALLOWED_NAME_FILES = {_ROOT / "_deprecation.py", _ROOT / "__init__.py"}
_BANNED_CATEGORIES = {"DeprecationWarning", "PendingDeprecationWarning"}


def _warn_callables(tree):
    """Names bound to the `warnings` module and to its warn / warn_explicit functions."""
    modules, functions = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "warnings":
                    modules.add(alias.asname or "warnings")
        elif isinstance(node, ast.ImportFrom) and node.module == "warnings":
            for alias in node.names:
                if alias.name in {"warn", "warn_explicit"}:
                    functions.add(alias.asname or alias.name)
    return modules, functions


def _category_name(node):
    if isinstance(node, ast.Call):  # a category passed as an instance: DeprecationWarning("...")
        node = node.func
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _emitting_lines(text):
    """Line numbers of warnings.warn / warn_explicit calls that name a deprecation category."""
    tree = ast.parse(text)
    modules, functions = _warn_callables(tree)
    lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_warn = (
            isinstance(func, ast.Attribute)
            and func.attr in {"warn", "warn_explicit"}
            and isinstance(func.value, ast.Name)
            and func.value.id in modules
        ) or (isinstance(func, ast.Name) and func.id in functions)
        if not is_warn:
            continue
        args = list(node.args) + [kw.value for kw in node.keywords]
        if any(_category_name(arg) in _BANNED_CATEGORIES for arg in args):
            lines.append(node.lineno)
    return lines


def test_helper_is_the_only_emitting_path():
    sources = sorted(_ROOT.rglob("*.py"))
    assert sources, "no cantus sources found"
    name_users, emitters = [], []
    for path in sources:
        text = path.read_text(encoding="utf-8")
        if "CantusDeprecationWarning" in text and path not in _ALLOWED_NAME_FILES:
            name_users.append(str(path))
        if path == _ROOT / "_deprecation.py":
            continue
        emitters.extend(f"{path}:{line}" for line in _emitting_lines(text))
    assert name_users == []
    assert emitters == []
