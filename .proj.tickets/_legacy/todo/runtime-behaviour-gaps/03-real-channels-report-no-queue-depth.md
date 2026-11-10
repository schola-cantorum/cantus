# 03: Real channels keep a deque but never report its depth

Entered: 2026-09-06

## Context

Third-party audit observation 4. `QueueIntrospectable.queue_depth` is
implemented only by `LocalMockReceiver` (`cantus/serve/channel.py`). All four
real channels hold `self._queue: deque` (for example
`cantus/serve/channels/line.py`) but do not implement the protocol, so
`GET /introspection/queues` reports `depth=None` for every real channel and
the `cantus tui` Dataflow pane shows nothing useful in production.

Implementing `queue_depth()` on the four channels changes an observable
introspection response from `None` to an integer: public API surface,
Spectra path. Candidate to fold into the parked `cantus-v1-hardening`
change.

## Acceptance criteria

- [ ] The four channel classes implement `queue_depth()` returning
      `len(self._queue)`
- [ ] `cantus-runtime-introspection-api` spec states real channels report an
      integer depth
- [ ] `docs/site/core/inspector.md` / `tui.md` no longer describe `None` as
      the normal case
