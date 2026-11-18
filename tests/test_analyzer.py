"""Analyzer: parses text into typed Pydantic / dataclass instances."""

from pydantic import BaseModel

from cantus.protocols.analyzer import Analyzer, analyzer, register_analyzer


class Book(BaseModel):
    title: str
    isbn: str


def test_decorator_analyzer_returns_pydantic():
    @analyzer
    def parse_book(text: str) -> Book:
        """Parse a text into a Book."""
        title, isbn = text.split("/", 1)
        return Book(title=title, isbn=isbn)

    book = parse_book("Foundation/9780553293357")
    assert isinstance(book, Book)
    assert book.title == "Foundation"


def test_function_pass_analyzer_equivalent():
    def parse(text: str) -> Book:
        """Parse."""
        title, isbn = text.split("/", 1)
        return Book(title=title, isbn=isbn)

    a = register_analyzer(parse)
    out = a("X/9780553293357")
    assert isinstance(out, Book)


def test_class_first_analyzer():
    class ParseBook(Analyzer):
        """Parse text → Book."""

        name = "parse_book"

        def run(self, text: str) -> Book:
            title, isbn = text.split("/", 1)
            return Book(title=title, isbn=isbn)

    inst = ParseBook()
    out = inst("Y/9780553293357")
    assert out.title == "Y"


# --- Hook helper (v0.3.0): no registry side-effect ----------------------


def test_decorator_analyzer_no_registry_entry():
    """v0.3.0: @analyzer SHALL NOT mutate the runtime registry."""
    from cantus.core.registry import _get_global_registry

    @analyzer
    def parse_book(text: str) -> Book:
        """Parse."""
        title, isbn = text.split("/", 1)
        return Book(title=title, isbn=isbn)

    assert _get_global_registry().names_for("tool") == []


def test_register_analyzer_no_registry_entry():
    """v0.3.0: register_analyzer() SHALL NOT mutate the runtime registry."""
    from cantus.core.registry import _get_global_registry

    def parse(text: str) -> Book:
        """Parse."""
        title, isbn = text.split("/", 1)
        return Book(title=title, isbn=isbn)

    register_analyzer(parse)
    assert _get_global_registry().names_for("tool") == []


def test_class_first_analyzer_no_registry_entry():
    """v0.3.0: instantiating an Analyzer subclass SHALL NOT mutate the registry."""
    from cantus.core.registry import _get_global_registry

    class ParseSomething(Analyzer):
        """Parse something."""

        name = "parse_something"

        def run(self, text: str) -> Book:
            return Book(title=text, isbn="x")

    ParseSomething()
    assert _get_global_registry().names_for("tool") == []
