# Documentation release sign-off

The documentation toolchain builds the site, generates the NotebookLM corpus, and ships an interactive manual, and CI checks the build and keeps `docs/api/` in sync. The steps below are the ones a machine cannot finish for you. Work through them before announcing a documentation release; tick each box once you have done it, not once you intend to.

This is an operator runbook, kept in English only.

## Sign-off checklist

- [ ] **Bind the site on Cloudflare Pages.** In the Cloudflare Pages dashboard, connect the `schola-cantorum/cantus` repository, set the build command to `npm run docs:build`, and set the output directory to `docs/site/.vitepress/dist/`. The repository ships the buildable site but no deployment automation, so this binding is manual and one-time. Confirm a deploy succeeds and the published URL serves both `/` and `/zh-tw/`.

- [ ] **Review the knowledge-graph snapshot before it freezes.** The interactive manual renders `docs/interactive/data/knowledge-graph.json`, a snapshot captured from `/understand`. Read the snapshot, confirm it reflects the current architecture, and scrub any absolute developer paths before it is committed. A machine cannot judge whether the graph is faithful — you have to look.

- [ ] **Upload the corpus to NotebookLM.** Upload the generated `docs/api/` Markdown tree as NotebookLM sources (optionally with `docs/llms-txt.md` for context), then share the notebook with the people who need it. The repository only produces the corpus; creating and sharing the notebook is a manual step. Do not upload `notebooks/` — those are Colab execution notebooks, not corpus.

- [ ] **Accept the Traditional Chinese translation.** The `docs/site/zh-tw/**` pages pass the automated zh-TW prose gate, but only a Traditional Chinese reader can judge whether they read naturally for teachers and students. Read the changed zh-TW pages and confirm the wording is right.

- [ ] **Open the manual and the site in a browser.** Open `cantus-manual.html` and click through the built site, including the interactive manual at `/interactive/`. Interactive output is not something the automated gates can verify — confirm with your own eyes that it renders and the links work.

- [ ] **Confirm the documentation-layout decisions still hold.** Check that superseded legacy `docs/` pages remain redirect stubs (not re-grown duplicates) and that the `llms.txt` references in `docs/llms-txt.md` still point at real files. These are judgement calls that drift silently if no one watches them.
