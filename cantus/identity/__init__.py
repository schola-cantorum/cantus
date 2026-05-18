"""cantus.identity — Soul as a first-class identity abstraction.

`Soul` loads a SOUL.md file with six H2 sections (`Name & Role`,
`Personality`, `Rules`, `Tools`, `Output format`, `Handoffs`) and
renders them back as a stable system prompt prefix that can be injected
into `Agent` via the `soul=` keyword.

Failure to parse a SOUL.md raises `SoulParseError`, a `ValueError`
subclass that carries the missing / duplicate / unexpected section
lists so callers can show actionable error messages.
"""

from cantus.identity.soul import Soul, SoulParseError

__all__ = ["Soul", "SoulParseError"]
