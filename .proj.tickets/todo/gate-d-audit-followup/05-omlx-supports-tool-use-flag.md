# 05: Decide how OmlxChatModel reports supports_tool_use

Entered: 2026-09-06

## Context

Gate D audit finding L4. `OmlxChatModel` inherits `supports_tool_use = True`
unconditionally, but whether a local server can do function calling depends
on the loaded model, not the adapter. Callers branch on the flag. Failures
surface as server errors rather than silently dropped tools, so this is
lower impact than the mlx `stream()` case fixed in the Gate D hardening PR.
Changing the flag's value or making it configurable is a public-API change
(Spectra path); fold into ticket 01's capability delta if both proceed.

## Acceptance criteria

- [ ] The `cantus-local-llm-omlx-server` capability states what the flag
      means for a server-backed adapter and how a caller overrides it
- [ ] The adapter's docstring and `docs/site/model-providers.md` (both
      locales) say the same thing
