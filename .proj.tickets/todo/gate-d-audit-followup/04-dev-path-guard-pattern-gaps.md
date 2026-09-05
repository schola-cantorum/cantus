# 04: Widen the development-path guard and exempt its own docs by path

Entered: 2026-09-06

## Context

Gate D audit finding L3. `scripts/check_no_dev_paths.sh` matches
`/Users/[A-Za-z]|/home/[A-Za-z]`, which misses usernames starting with `_` or
a digit, Windows `C:\Users\`, and macOS `/var/folders/` temp paths. The
alphabetic requirement exists so the script's own documentation does not
trip it; that self-exemption is fragile and the next example path in a doc
will be "fixed" by weakening the pattern. ADR-0003 (proposed) also wants
token shapes (`sk-`, `ghp_`, `Bearer `) scanned once expected-output blocks
are committed.

## Acceptance criteria

- [ ] Pattern covers `/Users/<any>`, `/home/<any>`, `C:\Users\`,
      `/var/folders/`, and the three token shapes
- [ ] The guard's own file and its documentation are exempted by path, not by
      pattern shape
- [ ] `tests/test_check_no_dev_paths.py` gains one case per new pattern
