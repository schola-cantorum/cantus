# Migrating cantus v0.4.1 → v0.4.2

**Release date: 2026-05-21.** v0.4.2 is a **distribution-lifecycle change with zero code-level migration**. The `cantus` Python package, every public symbol, every endpoint, every default value, every extras group, and every `[tool.uv] conflicts` declaration is byte-identical to v0.4.1. The single change that affects you is **how you install cantus**.

## Breaking

None. v0.4.2 is fully ADDITIVE on the distribution surface. `cantus.__version__` reports `"0.4.2"`; pin assertions that hardcoded `"0.4.1"` need to update — that is the only code-side touch.

## What changed at the distribution layer

1. **Cantus is now on PyPI as `cantus-agent`.** The unqualified `cantus` name on PyPI is occupied by an unrelated musicology placeholder (Tim Eipert / University of Würzburg, version `0.0.0` "Coming soon", uploaded 2024-05-04 — `https://pypi.org/project/cantus/`). The framework therefore ships under the hyphenated distribution name `cantus-agent`. Analogous precedent: `python-dateutil` → `import dateutil`, `pillow` → `import PIL`, `beautifulsoup4` → `import bs4`.
2. **The Python import name is unchanged.** Every existing `import cantus`, `from cantus import …`, and `from cantus.foo import …` continues to work byte-identical. The PyPI distribution name and the Python package directory name are independent.
3. **Two install paths now coexist.** PyPI is the recommended path for tagged releases; git+ remains the escape hatch for `main` and arbitrary commit SHAs.
4. **GitHub Actions release pipeline is now live.** Tagging a release on `schola-cantorum/cantus` triggers `release.yml`, which builds sdist + wheel, runs `twine check --strict`, and publishes via OIDC trusted publisher (no static API tokens). A separate `test.yml` workflow runs the pytest matrix on push to `main` and pull request.
5. **pyproject metadata is now PyPI-complete.** `[project.urls]` declares Homepage / Documentation / Source / Issues / Changelog; `[project].keywords` is populated; `Development Status :: 4 - Beta` and `Operating System :: OS Independent` classifiers are present; the license declaration is upgraded to PEP 639 SPDX expression form (`license = "ECL-2.0"` with explicit `license-files = ["LICENSE"]`).

## Upgrading your install command

### Recommended: PyPI

```bash
pip install cantus-agent==0.4.2
```

After install, your code does not change:

```python
import cantus
print(cantus.__version__)  # "0.4.2"

import importlib.metadata
print(importlib.metadata.version("cantus-agent"))  # "0.4.2"
```

Note that `importlib.metadata.version(...)` takes the **PyPI distribution name** (`cantus-agent`), not the Python import name (`cantus`). This asymmetry matters for downstream diagnostic tooling.

### Escape hatch: git+

For `main`, feature branches, or commit SHAs that PyPI cannot express:

```bash
pip install git+https://github.com/schola-cantorum/cantus@v0.4.2
pip install git+https://github.com/schola-cantorum/cantus@main
pip install git+https://github.com/schola-cantorum/cantus@<commit-sha>
```

This path remains supported indefinitely.

### Optional extras still work

The extras matrix is byte-identical to v0.4.1; only the distribution name changes:

```bash
pip install 'cantus-agent[serve]==0.4.2'
pip install 'cantus-agent[security]==0.4.2'
pip install 'cantus-agent[providers]==0.4.2'
pip install 'cantus-agent[openhands]==0.4.2'   # py3.12 only
pip install 'cantus-agent[all]==0.4.2'
```

The `[tool.uv] conflicts` declaration is byte-identical to v0.4.1 (six pairwise entries plus the `openhands` py3.12 marker).

## Why the PyPI name is `cantus-agent`

Cantus (Latin: *song*, *chant*) treats writing agent code as a form of chanting — every `Skill`, `Memory`, and `Agent` you compose is a verse that wields the underlying LLM. The PyPI name surfaces the relationship: you chant, the agent answers. The `-agent` suffix names what you wield; the harness concept is carried by the verb `cantus` itself.

## FAQ

**Q: Will the `cantus` PyPI name eventually become available?**
A: It is held by a placeholder release that has not been touched since 2024-05-04. PEP 541 reclaim attempts are slow and not guaranteed; the framework cannot block on that outcome. If the name does become available later, a future change can publish under both names with `cantus-agent` retained as an alias.

**Q: Will my Colab notebook break?**
A: No. Existing `pip install git+https://github.com/schola-cantorum/cantus@…` cells continue to work. If you want PyPI metadata pinning, update the cell to `pip install cantus-agent==0.4.2`.

**Q: Does `cantus.__version__` differ from `importlib.metadata.version(...)`?**
A: They are kept identical by design. v0.4.2 explicitly asserts `cantus.__version__ == "0.4.2" == importlib.metadata.version("cantus-agent")`. If these ever diverge in a future release, that is a regression — please file an issue.

**Q: Where do I report PyPI-side issues (broken README rendering, missing classifier, broken sidebar link)?**
A: `https://github.com/schola-cantorum/cantus/issues`.
