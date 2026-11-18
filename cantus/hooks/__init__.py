"""Hook helpers — Analyzer and Validator as Tool pre/post hook binding targets.

v0.3.0 demoted `Analyzer` and `Validator` from independent protocol kinds to
reusable callable helpers that attach to a `Tool` via `pre_hook=` and
`post_hook=` keyword arguments. They are imported from this submodule
(`cantus.hooks`) rather than `cantus` top level to make the role explicit:
hook helpers, not protocol kinds.

    from cantus import tool
    from cantus.hooks import analyzer, validator, Result

    @analyzer
    def parse_location(text: str) -> Location: ...

    @validator
    def non_empty(value: str) -> Result: ...

    @tool(pre_hook=parse_location, post_hook=non_empty)
    def get_weather(loc: Location) -> str: ...
"""

from cantus.core.result import Result
from cantus.protocols.analyzer import Analyzer, analyzer
from cantus.protocols.validator import (
    ReservedValidatorNameError,
    Validator,
    validator,
)

__all__ = [
    "Analyzer",
    "ReservedValidatorNameError",
    "Result",
    "Validator",
    "analyzer",
    "validator",
]
