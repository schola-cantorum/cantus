"""Soul — SOUL.md parser and deterministic system-prompt renderer.

The on-disk format is the six-section H2 markdown convention from
aaronjmars/soul.md: each section opens with `## <header>` (case-sensitive,
byte-for-byte) and the body runs until the next H2 or EOF, with leading
and trailing whitespace stripped. The canonical headers, in canonical
order, are:

    ## Name & Role
    ## Personality
    ## Rules
    ## Tools
    ## Output format
    ## Handoffs

The framework treats SOUL.md content as trusted host-authored input —
section bodies are NOT escaped, sanitised, or inspected for control
characters. Host code reading SOUL.md from untrusted sources must
validate the content itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CANONICAL_SECTIONS: tuple[tuple[str, str], ...] = (
    ("Name & Role", "name_and_role"),
    ("Personality", "personality"),
    ("Rules", "rules"),
    ("Tools", "tools"),
    ("Output format", "output_format"),
    ("Handoffs", "handoffs"),
)
_HEADER_BY_TITLE: dict[str, str] = {title: attr for title, attr in CANONICAL_SECTIONS}


class SoulParseError(ValueError):
    """Raised when a SOUL.md file cannot be parsed into a complete Soul.

    Attributes
    ----------
    path:
        The originating file path (or `None` when parsing in-memory text).
    missing_sections:
        Canonical H2 titles that did not appear in the file.
    duplicates:
        Canonical H2 titles that appeared more than once.
    unexpected:
        H2 titles that appeared but fell outside the canonical vocabulary
        (for example `Examples` or a casing variant of a canonical title).
    """

    def __init__(
        self,
        path: str | Path | None = None,
        missing_sections: list[str] | None = None,
        duplicates: list[str] | None = None,
        unexpected: list[str] | None = None,
    ) -> None:
        self.path: Path | None = Path(path) if path is not None else None
        self.missing_sections: list[str] = list(missing_sections or [])
        self.duplicates: list[str] = list(duplicates or [])
        self.unexpected: list[str] = list(unexpected or [])
        parts: list[str] = []
        if self.missing_sections:
            parts.append(f"missing={self.missing_sections}")
        if self.duplicates:
            parts.append(f"duplicates={self.duplicates}")
        if self.unexpected:
            parts.append(f"unexpected={self.unexpected}")
        loc = str(self.path) if self.path is not None else "<in-memory>"
        super().__init__(f"SOUL.md parse error at {loc}: {'; '.join(parts) or 'no detail'}")


@dataclass(frozen=True)
class Soul:
    """Six-section identity loaded from a SOUL.md file."""

    name_and_role: str
    personality: str
    rules: str
    tools: str
    output_format: str
    handoffs: str

    @classmethod
    def from_file(cls, path: str | Path) -> "Soul":
        path_obj = Path(path)
        text = path_obj.read_text(encoding="utf-8")
        return _parse(text, path=path_obj)

    @classmethod
    def from_text(cls, text: str) -> "Soul":
        return _parse(text, path=None)

    def to_system_prompt(self) -> str:
        sections = [
            (title, getattr(self, attr)) for title, attr in CANONICAL_SECTIONS
        ]
        return "\n\n".join(f"## {title}\n{body}" for title, body in sections)


def _parse(text: str, *, path: Path | None) -> Soul:
    """Internal parser shared by from_file and from_text."""
    found: dict[str, str] = {}
    duplicates: list[str] = []
    unexpected: list[str] = []

    current_title: str | None = None
    current_body: list[str] = []
    is_canonical: bool = False

    def _flush() -> None:
        nonlocal current_title, current_body, is_canonical
        if current_title is None:
            return
        body = "\n".join(current_body).strip()
        if is_canonical:
            if current_title in found:
                duplicates.append(current_title)
            else:
                found[current_title] = body
        else:
            unexpected.append(current_title)
        current_title = None
        current_body = []
        is_canonical = False

    for line in text.split("\n"):
        if line.startswith("## ") and not line.startswith("### "):
            _flush()
            current_title = line[3:].strip()
            current_body = []
            is_canonical = current_title in _HEADER_BY_TITLE
        elif current_title is not None:
            current_body.append(line)
    _flush()

    missing = [title for title, _ in CANONICAL_SECTIONS if title not in found]

    if missing or duplicates or unexpected:
        raise SoulParseError(
            path=path,
            missing_sections=missing,
            duplicates=duplicates,
            unexpected=unexpected,
        )

    return Soul(
        name_and_role=found["Name & Role"],
        personality=found["Personality"],
        rules=found["Rules"],
        tools=found["Tools"],
        output_format=found["Output format"],
        handoffs=found["Handoffs"],
    )
