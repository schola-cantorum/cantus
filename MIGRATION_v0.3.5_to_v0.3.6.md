# Migrating cantus v0.3.5 → v0.3.6

**ADDITIVE patch release. No host code change required.** v0.3.6 is a pure
internal cleanup release: 15 redundant `# type: ignore[...]` comments that
the v0.3.5 `warn_unused_ignores = true` mypy baseline began reporting have
been removed (or narrowed to the still-needed error codes). No public API,
no dependencies, no optional extras, no wheel-bundled assets, and no
runtime behavior have changed.

## Summary

Upgrading from v0.3.5 to v0.3.6 is byte-equivalent at runtime. The only
observable difference for downstream consumers is that `pip install
git+https://github.com/schola-cantorum/cantus@v0.3.6` resolves to the
v0.3.6 tag instead of v0.3.5, and `cantus.__version__` reports `0.3.6`.

## What changed

- 11 cantus source files had their `# type: ignore[...]` comments cleaned
  up (12 comments removed wholesale, 3 narrowed to retain only the still-
  needed error codes). See the v0.3.6 entry in `CHANGELOG.md` for the
  per-file list.
- `pyproject.toml` `[project] version` bumped `0.3.5` → `0.3.6`.
- `tests/test_distribution_config.py` version-pin assertion bumped to
  `"0.3.6"`; the other five distribution config invariants (PEP 561 marker,
  setuptools package-data, mypy baseline, coverage baseline, pytest
  addopts) remain byte-identical and pass without modification.

## Action required

**None — this is an internal cleanup release.**

All v0.3.0 through v0.3.5 imports, public callables, optional-extras
groups, wheel contents, and migration notes remain valid for v0.3.6. The
v0.3.4 → v0.3.5 migration note (PEP 561 typed surface, mypy baseline,
coverage defaults) still applies — v0.3.6 does not retract any of those
v0.3.5 additions.

If you upgrade directly from v0.3.4 (or earlier), follow
`MIGRATION_v0.3.4_to_v0.3.5.md` first; v0.3.6 layers no additional
migration steps on top.

## Maintainer note: prefer narrow error-code lists in new ignores

`warn_unused_ignores = true` (introduced in v0.3.5) only flags ignores
that resolve cleanly without the suppression. When new ignores are added
to cantus, prefer the narrowest error-code list that mypy accepts:

```python
# Preferred — surfaces drift if `attr-defined` becomes unnecessary later.
some_call()  # type: ignore[attr-defined]

# Avoid — bare ignore swallows future mypy fixes silently.
some_call()  # type: ignore
```

Bare `# type: ignore` comments and over-broad ignore lists are what made
v0.3.6 cleanup necessary; staying disciplined now defers the next round
of `[unused-ignore]` cleanup indefinitely.
