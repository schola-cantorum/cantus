---
profile: research
profile_version: "1.0.0"
schema_version: "1.0.0"
wiki_path: docs/llm_wiki
raw_path: docs/llm_wiki_raw
index_path: docs/llm_wiki/index.md
log_path: docs/llm_wiki/log.md
---

## Schema

Project: `cantus`. Wiki follows the shipped `research` profile (v1.0.0) defined by the wiki-schema capability suite.

- Sources live under `docs/llm_wiki_raw/` and are immutable.
- Wiki pages live under `docs/llm_wiki/` and are agent-maintained.
- Source pages MUST declare `source_url`, `ingested_at`, `source_type` (one of `paper`, `article`, `book`, `podcast`).
- `docs/llm_wiki/synthesis.md` accumulates cross-source synthesis.
- `docs/llm_wiki/log.md` uses strict format `## [YYYY-MM-DD] <op> | <title>`.

## Ingest

When a new source is dropped into `docs/llm_wiki_raw/`, the agent reads it, summarizes the key takeaways, files a source page under `docs/llm_wiki/pages/`, updates `docs/llm_wiki/index.md`, refreshes related entity and concept pages, refines `docs/llm_wiki/synthesis.md`, and appends a strict-format entry to `docs/llm_wiki/log.md`.

## Query

The agent reads `docs/llm_wiki/index.md` first, then drills into relevant pages and `docs/llm_wiki/synthesis.md` to compose answers. Citations link back to source pages.

## Lint

Periodic lint passes detect contradictions across pages, stale claims, orphan pages, missing cross-references, and synthesis gaps.
