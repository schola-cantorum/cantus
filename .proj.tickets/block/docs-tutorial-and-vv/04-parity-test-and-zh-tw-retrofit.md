# 04: Parity test and zh-tw retrofit of the twelve pages

Entered: 2026-09-06
Blocked by: 03

## Context

Spec: Implementation Decisions → "Parity test"; Appendix A.2.7 (token rule,
expected-output parity, shell parity), A.2.1 (zh-tw marker repeats the English
reason verbatim); Further Notes (8 of 12 pages differ today, only by translated
comments, docstrings and CJK strings; errors cookbook differs in fence indent
only, absorbed by dedent).

Traditional Chinese pages are never executed. They are proven equivalent to the
English source by comparison, so a fix on one side cannot be forgotten on the
other. This ticket lands the comparison and brings the twelve zh-tw pages up to
the English pages as edited in ticket 03.

## Acceptance criteria

- [ ] For each parity pair both files are parsed with A.2.0; block counts equal;
      position by position both or neither carry a marker; zh-tw marker reason
      equals the English reason verbatim (length rule English-side only)
- [ ] Token comparison per A.2.7: COMMENT/NL/NEWLINE/INDENT/DEDENT/ENCODING/
      ENDMARKER dropped; FSTRING_START…FSTRING_END collapsed into one STRING
      carrying the source slice; equal length; per position equal tokens, or both
      STRING with zh-tw containing CJK, every ASCII run of ≥4 chars
      (U+0021–U+007E, split on spaces and non-range chars) a substring of the
      English text, and verbatim equality when the English contains `://`,
      `pip install`, `uv pip` or `npm `
- [ ] Expected-output parity: the zh-tw block is found by `你應該看到` and its
      non-empty stripped lines equal the English block's, in order
- [ ] Shell parity: `bash`/`sh`/`console` fences present in the same order with
      identical content after trailing-whitespace strip, except lines starting
      with `#`
- [ ] A missing zh-tw page, or an identifier that differs, fails
- [ ] Unit cases cover all thirteen A.4 zh-tw pair rows on Python 3.10, 3.11 and
      3.12 (the f-string row must pass on all three)
- [ ] All twelve zh-tw pages pass against their English pair, in Taiwan
      Traditional Chinese wording
