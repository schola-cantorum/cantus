<!-- Doc-only follow-up to the archived cantus-docs-overhaul. Implementation tasks 1-5 touch disjoint file sets and carry [P]; tasks 6-7 are sequential gates. No runtime code, no docs/api generator changes. -->

## 1. Remove superseded orphan pages

- [x] 1.1 [P] Delete the four true-orphan legacy pages `docs/overview.md`, `docs/core/agent.md`, `docs/core/event-stream.md`, `docs/core/inspector.md` (their only live inbound link is the README, updated in task 3.1); satisfies the `cantus-docs-site` "Superseded legacy documentation pages SHALL NOT duplicate site content" Requirement (removal branch). Verify: the four files are absent; `grep -rn` across tracked files excluding `docs/site/`, `docs/api/`, `CHANGELOG.md`, and `openspec/changes/archive/` finds no remaining live Markdown link to them. (Design: delete true orphans, redirect-stub the link-load-bearing pages.)

## 2. Redirect-stub the link-load-bearing legacy pages

- [x] 2.1 [P] Replace `docs/quickstart.md` and `docs/tui.md` with redirect stubs — each keeping its original H1 plus a repository-relative Markdown link to `docs/site/quickstart.md` / `docs/site/tui.md`, with no hardcoded site domain; satisfies the `cantus-docs-site` redirect-stub Requirement and its "Redirect stub keeps inbound links resolving" Scenario. Verify: each file body is only the stub; the `./quickstart.md` and `./tui.md` links in `docs/quickstart-desktop.md` resolve to these files. (Design: redirect stub format.)
- [x] 2.2 [P] Replace the nine `docs/protocols/{adapters,analyzer,debug,identity,memory,serve,skill,validator,workflows}.md` pages with redirect stubs to their `docs/site/protocols/*` counterparts; leave `docs/protocols/adapters-batch2.md` and `docs/protocols/adapters-batch3.md` untouched (no site twin), satisfying the "Pages without a site twin are left intact" Scenario. Verify: nine stubs present, batch2/batch3 unchanged; the `docs/protocols/*` links from `docs/migrations/*` resolve to existing files.
- [x] 2.3 [P] Replace `docs/cookbook/{errors,patterns,tips}.md` and the four `docs/cookbook-{line,telegram,discord,google-chat}-channel.md` pages with redirect stubs to their `docs/site/cookbook/*` / `docs/site/channels/*` counterparts. Verify: seven stubs present; the inbound references from `CONTRIBUTING.md`, `CONTRIBUTING.zhTW.md`, `notebooks/README.md`, and the `cantus/serve/channels/discord.py` and `cantus/serve/channels/googlechat.py` docstrings all resolve to existing files.

## 3. README Documentation section rework

- [x] 3.1 [P] Rework the `## Documentation` section of `README.md` and `README.zhTW.md` to present `docs/site/` as the canonical human-facing source and remove the per-page deep links into the deleted/stubbed pages (`overview`, `quickstart`, `protocols/`, `cookbook/`), keeping the genuinely docs-only links `llms.txt` and `docs/llm_wiki/index.md`; satisfies the `cantus-distribution` "README Documentation section SHALL link to the documentation site" Requirement. Verify: the `cantus-distribution` README banner scenarios pass — first 30 lines of each README still contain `assets/banner_hero.jpeg`, `img.shields.io/pypi/v/cantus-agent`, `ECL-2.0`, the Colab CTA, and the `繁體中文`/`English` switch; no `img.shields.io/badge/release-` is present.

## 4. NotebookLM corpus signposting

- [x] 4.1 [P] Expand `docs/llms-txt.md` with a "feed NotebookLM" section that names `docs/api/` as the upload target and states `notebooks/` holds Colab execution notebooks (not NotebookLM corpus); fix the two broken references by changing `docs/llms.txt` to `llms.txt` and `docs/api/llms-txt.md` to `docs/llms-txt.md`. Verify: `grep` of `docs/llms-txt.md` finds neither `docs/llms.txt` nor `docs/api/llms-txt.md`, and the file names both `docs/api/` and `notebooks/`. (Design: NotebookLM signpost in docs/llms-txt.md.)
- [x] 4.2 [P] Add a cross-link near the top of `notebooks/README.md` clarifying that the NotebookLM corpus is `docs/api/` (see `docs/llms-txt.md`), distinct from these Colab execution notebooks. Verify: `notebooks/README.md` references both `docs/api/` and `docs/llms-txt.md`.

## 5. Human sign-off checklist

- [x] 5.1 [P] Create `docs/DOCS_RELEASE_SIGNOFF.md`, an English-only operator runbook listing the six human steps: (1) bind Cloudflare Pages (repo, `npm run docs:build`, output `docs/site/.vitepress/dist/`); (2) review and path-scrub the `/understand` knowledge-graph snapshot before freezing `docs/interactive/data/knowledge-graph.json`; (3) upload the `docs/api/` corpus to NotebookLM and share the notebook; (4) accept the `docs/site/zh-tw/**` Traditional Chinese translation; (5) open `cantus-manual.html` and the built site in a browser for a visual check; (6) confirm the duplicate-cleanup and `llms.txt` path decisions. This satisfies the `cantus-i18n-docs` "Excluded-from-translation documents SHALL remain single-language" Requirement (the runbook joins that enumeration). Verify: the file exists with all six items and is classified in the Excluded-from-translation layer (no zh-TW companion demanded by Gate 1). (Design: sign-off checklist classification.)

## 6. Final verification + prose audit

- [x] 6.1 Run the full gate: `npm run docs:build` exits 0 with both locales; `npm run docs:api` then `git diff --exit-code docs/api/` is clean (generator untouched); `scripts/check_no_dev_paths.sh` is green; every redirect stub's pre-existing inbound link resolves to an existing file; the `cantus-distribution` README banner scenarios pass; `/spectra-audit cantus-docs-i18n-baseline` (Gate 1) reports zero Critical/Warning; spot-check `pytest` and mypy/ruff show delta 0 (runtime untouched). Verify: all checks green.
- [x] 6.2 Run `/ai-slop-auditor` and `/humane-prose-audit` on the changed prose (`docs/llms-txt.md`, `docs/DOCS_RELEASE_SIGNOFF.md`, the two README Documentation sections, `notebooks/README.md`) and fix findings to zero Critical/Warning. Verify: both audits report zero Critical/Warning.

## 7. Commit + PR

- [x] 7.1 Stage the change, generate the commit message with `/tw-emoji-commit` and commit, then open a PR with `/tw-emoji-pr-note` (do not merge). Verify: the PR is open and unmerged with a skill-generated description.
