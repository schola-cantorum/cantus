# 06: Site-scoped token patterns and the install-name pin test

Entered: 2026-09-06

## Context

Spec: Implementation Decisions → "Hygiene pattern", "Install-pin test" (the
`cantus-agent` spelling half; the `==0.6.0` half for tutorial fences lands in
ticket 09); user stories 17, 32; A.4 Hygiene ×2, "In-scope shell fence" row.
Handoff pitfall: the desktop quickstart spells the distribution `cantus[mlx]`
and `cantus[openai]` today in both locales; the repo-wide path group must stay
unchanged because test fixtures hold fake tokens.

## Acceptance criteria

- [ ] The hygiene script gains a second pattern group applied only to paths under
      the site directory: `sk-[A-Za-z0-9]{20,}`, `ghp_[A-Za-z0-9]{36}`,
      `Bearer [A-Za-z0-9._-]{20,}`; the repo-wide path group is unchanged
- [ ] Its self-test gains one positive case per pattern (file under the site
      directory → fail) and asserts a fake token in a fixture outside the site
      directory still passes
- [ ] A pin test parses every `bash`/`sh`/`console` fence (using the ticket 01
      parser) on every in-scope page and its parity pair and fails on any line,
      including `#` comment lines, that contains `pip install cantus[` without
      `-agent`
- [ ] The desktop quickstart's mlx and Ollama install lines read
      `cantus-agent[...]` in both locales; the pin test passes on all twelve
      pages
