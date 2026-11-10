# 01: Decide whether an inbound channel message should drive an Agent

Entered: 2026-09-06

## Context

Third-party audit (2026-09-05) observation 5. Every channel's inbound path
(`LineWebhookChannel`, `TelegramWebhookChannel`, `DiscordRealtimeChannel`,
`GoogleChatPubSubChannel`) appends the payload to its own `deque` and stops.
Nothing in `cantus/` reads `channel.receive()` and calls `Agent.run`, and
`SessionTracker.start` is called only from `POST /skills/{name}`
(`cantus/serve/app.py`, around the `tracker.start(f"skill:{name}")` line).
The CHANGELOG entry for v0.5.0 says a session is recorded "per skill endpoint
call / channel message"; the second half has no call site.

The docs-and-tutorial work planned on 2026-09-05 will state this as a known
limitation on `docs/site/protocols/serve.md` and the four channel pages. Wiring a channel
to an Agent is new public behaviour and routes through Spectra; the
alternative is to correct the CHANGELOG wording and keep the channel layer as
a transport only.

## Acceptance criteria

- [ ] A decision is recorded: either a capability delta that specifies the
      receive → `Agent.run` → `send` loop and session recording, or a
      CHANGELOG/docs correction that scopes channels to transport
- [ ] Whichever is chosen, the four channel pages and `serve.md` (both
      locales) say the same thing as the code
