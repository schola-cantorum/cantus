## Summary

Finish the documentation overhaul: remove the now-duplicated legacy `docs/*.md` pages (delete true orphans, redirect the link-load-bearing ones to the documentation site), make the NotebookLM corpus discoverable, and ship a version-controlled human sign-off checklist for documentation releases.

## Motivation

The `cantus-docs-overhaul` change (archived 2026-06-21) migrated the English `docs/*.md` pages into the bilingual VitePress site under `docs/site/` but deliberately left the originals in place ("Removed: none") to avoid breaking spec-pinned and runtime-referenced links. Review surfaced three gaps:

1. **Duplicated content drift.** The same pages now exist in three places — legacy `docs/<page>.md` (English-only, orphaned), `docs/site/<page>.md` plus its `zh-tw` companion (canonical bilingual), and `docs/api/<page>.md` (generated NotebookLM corpus). The site and corpus copies are intentional; the legacy copies are superseded and will drift from the canonical site.
2. **NotebookLM corpus is undiscoverable.** The corpus to upload to NotebookLM is the generated `docs/api/` markdown tree, but the similarly-named `notebooks/` directory holds Colab `.ipynb` execution notebooks — an easy mix-up. `docs/llms-txt.md` also references two paths that do not exist (`docs/llms.txt` and `docs/api/llms-txt.md`).
3. **No human sign-off checklist.** The overhaul's automated prose audits ran during apply, but the genuinely human-in-the-loop steps (Cloudflare Pages binding, knowledge-graph snapshot review, NotebookLM upload, zh-TW acceptance, manual visual check) were never collected anywhere.

## Motivation Detail

The site copy serves human readers in two languages; the generated corpus serves NotebookLM under a strict size and source-count budget. The legacy copies serve neither and have no generator keeping them current, so they are pure drift risk.

## Proposed Solution

- **Remove duplicated legacy pages (hybrid).** Delete the true orphans `docs/overview.md` and the three `docs/core/*` pages (no live inbound links other than the README, which this change updates). Replace each link-load-bearing legacy page with a one-line redirect stub pointing to its site equivalent: `docs/quickstart.md`, `docs/tui.md`, the nine `docs/protocols/*` pages that have a site twin, the three `docs/cookbook/*` pages, and the four `docs/cookbook-*-channel.md` pages. Keep `docs/protocols/adapters-batch2.md` and `docs/protocols/adapters-batch3.md` (no site twin), `docs/quickstart-desktop.md` and `docs/migrations/*` (spec-pinned), and `docs/llm_wiki/*` (wiki-suite owned).
- **Rework both README Documentation sections** to present the site as the canonical human-facing source and drop the per-page deep links into the now-stubbed `docs/` pages, while preserving the banner, PyPI badge, ECL-2.0 badge, Colab call-to-action, and language-switch contract.
- **Signpost the NotebookLM corpus.** Expand `docs/llms-txt.md` with a section that names `docs/api/` as the upload target and states that `notebooks/` holds Colab execution notebooks, not corpus; fix the two broken path references. Cross-link `notebooks/README.md` to `docs/api/` and `docs/llms-txt.md`.
- **Ship a human sign-off checklist** at `docs/DOCS_RELEASE_SIGNOFF.md` enumerating the documentation steps that require a person.

## Non-Goals

- No runtime or application code changes; the `cantus/` package, CLI, serve, and tui behaviour are unchanged.
- No changes to the `docs/api/` generator, its pinned file set, or the CI sync guard. The NotebookLM signpost lives in `docs/llms-txt.md` and is never hand-written into the generated `docs/api/` tree.
- No moving of the spec-pinned canonical files (`docs/quickstart-desktop.md`, `docs/migrations/*`) or the wiki suite (`docs/llm_wiki/*`).
- No version bump, no PyPI release, no Cloudflare Pages deployment automation.

## Alternatives Considered

- **Full delete of every legacy page plus rewrite of all inbound references.** Rejected: it would touch sixteen spec-pinned migration files, two runtime docstrings (`cantus/serve/channels/discord.py`, `cantus/serve/channels/googlechat.py`), and `@trace`-heavy specs — re-opening the runtime and spec surface the original change deliberately avoided.
- **Leave everything as-is.** Rejected: the duplicated English content will drift from the canonical site with nothing guarding against it.

## Impact

- Affected specs: `cantus-docs-site` (modified), `cantus-i18n-docs` (modified)
- Affected code:
  - New:
    - docs/DOCS_RELEASE_SIGNOFF.md
  - Modified:
    - README.md
    - README.zhTW.md
    - docs/llms-txt.md
    - notebooks/README.md
    - docs/quickstart.md
    - docs/tui.md
    - docs/protocols/adapters.md
    - docs/protocols/analyzer.md
    - docs/protocols/debug.md
    - docs/protocols/identity.md
    - docs/protocols/memory.md
    - docs/protocols/serve.md
    - docs/protocols/skill.md
    - docs/protocols/validator.md
    - docs/protocols/workflows.md
    - docs/cookbook/errors.md
    - docs/cookbook/patterns.md
    - docs/cookbook/tips.md
    - docs/cookbook-line-channel.md
    - docs/cookbook-telegram-channel.md
    - docs/cookbook-discord-channel.md
    - docs/cookbook-google-chat-channel.md
  - Removed:
    - docs/overview.md
    - docs/core/agent.md
    - docs/core/event-stream.md
    - docs/core/inspector.md
