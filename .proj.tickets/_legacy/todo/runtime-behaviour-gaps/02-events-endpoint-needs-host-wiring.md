# 02: GET /events returns [] unless the host attaches persistence by hand

Entered: 2026-09-06

## Context

Third-party audit observation and drift item 13. `cantus/serve/dashboard.py`
reads `app.state.event_persistence` and returns `[]` when it is absent.
Nothing in `cantus/` ever sets that attribute, so out of the box the
endpoint is always empty; the docs page now shows the one-line host wiring
(`app.state.event_persistence = JsonLinesPersistence(...)`) and flags the
default.

Options: (a) `serve()` accepts a persistence argument or reads a settings
field and wires it (public API change, Spectra); (b) keep the manual wiring
and make the empty response carry a hint that persistence is not attached
(observable response change, also Spectra); (c) leave as documented.

## Acceptance criteria

- [ ] A decision between (a), (b), (c) is recorded on this ticket
- [ ] If (a) or (b): capability delta on `cantus-serve-cli` or
      `cantus-runtime-introspection-api`, test, and both docs locales
