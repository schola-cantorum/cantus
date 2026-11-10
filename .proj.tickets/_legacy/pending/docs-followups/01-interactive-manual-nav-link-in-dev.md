# 01: Interactive manual nav link resolves in the dev server too

Entered: 2026-09-06
Pending reason: user decision — schedule after the docs-tutorial-and-vv batch (15 tickets) lands, so it does not ride on that PR

## Context

The site nav links the interactive manual as the directory URL. On the built
site a static host answers a directory URL with its index file, so the link
works. Under `vitepress dev` Vite hands a directory URL to the VitePress SPA,
which has no such page and renders its 404; the file URL (with `index.html`)
serves the manual correctly in both environments. Observed 2026-09-06 while
checking the dev server for ticket docs-tutorial-and-vv/01; behaviour dates
from PR #24. The release sign-off checklist already tells a human to open the
manual in a browser, which is how this was noticed.

## Acceptance criteria

- [ ] Clicking "Interactive manual" in the nav opens the manual under
      `vitepress dev`, `vitepress preview` and the built site alike, in both
      locales
- [ ] The comment in the site config that explains how the manual is served
      still describes the link accurately
- [ ] `npm run docs:build` passes and the `api-docs` sync check stays green
