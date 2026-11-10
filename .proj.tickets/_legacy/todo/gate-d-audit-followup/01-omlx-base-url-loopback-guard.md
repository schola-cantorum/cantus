# 01: Guard OmlxChatModel against a non-loopback base_url with the sentinel key

Entered: 2026-09-06

## Context

Gate D audit (v0.5.0 → v0.6.0 bundle, 2026-09-06) finding M5. The adapter's
premise is that a local MLX server does not authenticate, so it sends the
literal string `omlx` as the credential. `base_url` is required but not
validated: a typo'd or copy-pasted URL sends every prompt over plaintext HTTP
to an arbitrary host with a fake credential, and nothing warns. Validating the
host changes observable constructor behaviour, so this is a public-API change
and routes through Spectra rather than the main line.

## Acceptance criteria

- [ ] A capability delta on `cantus-local-llm-omlx-server` states which hosts
      are accepted without an explicit opt-in (`localhost`, `127.0.0.1`, `::1`)
- [ ] Constructing the adapter with a non-loopback `http://` host while the
      sentinel key is in play raises, or requires an explicit opt-in argument
- [ ] The existing `api_key=""` coalescing behaviour is unchanged
- [ ] `docs/site/quickstart-desktop.md` (both locales) shows the opt-in
