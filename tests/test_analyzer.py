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
