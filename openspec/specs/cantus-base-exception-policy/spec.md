# cantus-base-exception-policy Specification

## Purpose

TBD - created by archiving change 'cantus-base-exception-policy'. Update Purpose after archive.

## Requirements

### Requirement: Production code does not swallow BaseException-tier signals

Production code under the `cantus` package SHALL NOT catch `BaseException`, nor explicitly catch `asyncio.CancelledError`, `KeyboardInterrupt`, or `SystemExit`, in a manner that suppresses the signal (for example by `pass`, by `return`, or by converting it into an ordinary error result) without re-raising it. Broad defensive catches that are intended only to tolerate ordinary errors SHALL catch `Exception` rather than `BaseException`, so that cancellation, keyboard-interrupt, and system-exit signals propagate.

Two forms are permitted: (a) a *cleanup-then-reraise* block, where the `except BaseException` body performs cleanup and then re-raises the caught exception, so the signal continues to propagate; and (b) a *narrow child-cancellation absorb*, where code that has itself cancelled a child task awaits that child and absorbs only that child's `asyncio.CancelledError` (expressed with `contextlib.suppress(asyncio.CancelledError)` around the awaited child), which SHALL NOT also blanket-absorb other exception types in the same suppression.

#### Scenario: best-effort cleanup does not swallow a base-tier signal

- **GIVEN** a `GoogleChatPubSubChannel` whose subscriber's `close()` raises `KeyboardInterrupt`
- **WHEN** `disconnect()` runs its best-effort close cleanup
- **THEN** the `KeyboardInterrupt` SHALL propagate out of `disconnect()`
- **AND** it SHALL NOT be suppressed by a `BaseException` catch

#### Scenario: a message handler does not convert a base-tier signal into a nack

- **GIVEN** a `GoogleChatPubSubChannel` whose queue `append` raises `KeyboardInterrupt`
- **WHEN** `_on_message` handles a well-formed message
- **THEN** the `KeyboardInterrupt` SHALL propagate out of `_on_message`
- **AND** the message SHALL NOT be nacked-and-returned as if an ordinary enqueue error occurred

#### Scenario: an ordinary Exception during cleanup is still tolerated

- **GIVEN** a `GoogleChatPubSubChannel` whose subscriber's `close()` raises an ordinary `Exception` (a subclass of `Exception`, not of the base-tier signals)
- **WHEN** `disconnect()` runs its best-effort close cleanup
- **THEN** `disconnect()` SHALL complete without raising
- **AND** the ordinary `Exception` SHALL be swallowed as a best-effort cleanup failure

#### Scenario: cleanup-then-reraise is a permitted form

- **GIVEN** the token-refresh path whose `refresh` call raises an exception
- **WHEN** the refresh fails
- **THEN** the cached credentials SHALL be dropped
- **AND** the original exception SHALL be re-raised so it propagates to the caller


<!-- @trace
source: cantus-base-exception-policy
updated: 2026-08-29
code:
  - cantus/serve/channels/_googlechat_internals.py
  - cantus/serve/channels/_realtime.py
  - cantus/serve/channels/googlechat.py
tests:
  - tests/serve/channels/test_exception_policy.py
-->

---
### Requirement: A codebase guard enforces the BaseException policy

The test suite SHALL include a guard that scans the source of the `cantus` package and asserts that every exception handler covering a base-tier signal re-raises within its handler block. A handler covers a base-tier signal when it is a bare `except:`, or when it names `BaseException`, `asyncio.CancelledError`, `KeyboardInterrupt`, or `SystemExit` — each alone or as a member of a tuple, and whether written with or without its module prefix. The guard SHALL fail if any such handler in production code does not re-raise, and SHALL identify the offending location, so that future regressions of this policy are caught automatically.

The guard SHALL NOT flag the permitted narrow child-cancellation absorb. That form is expressed with `contextlib.suppress(asyncio.CancelledError)`, which is a context manager rather than an exception handler, so it falls outside what a handler scan examines.

The guard SHALL NOT carry a list of exempted locations. Every production handler covering a base-tier signal either re-raises or does not exist.

#### Scenario: guard passes on the conforming codebase

- **WHEN** the guard scans the `cantus` package source after this change is applied
- **THEN** every handler covering a base-tier signal SHALL re-raise within its handler block
- **AND** the guard SHALL pass

#### Scenario: guard fails on a non-reraising BaseException catch

- **GIVEN** a hypothetical production block that catches `BaseException` and returns without re-raising
- **WHEN** the guard scans the source
- **THEN** the guard SHALL fail and identify the offending location

#### Scenario: guard fails on a non-reraising cancellation catch

- **GIVEN** a hypothetical production block that catches `asyncio.CancelledError` and returns without re-raising
- **WHEN** the guard scans the source
- **THEN** the guard SHALL fail and identify the offending location

#### Scenario: guard fails on a non-reraising interrupt or exit catch

- **GIVEN** a hypothetical production block that catches `KeyboardInterrupt` or `SystemExit` and returns without re-raising
- **WHEN** the guard scans the source
- **THEN** the guard SHALL fail and identify the offending location

#### Scenario: guard fails on a base-tier exception inside a tuple

- **GIVEN** a hypothetical production block whose handler names a tuple containing both an ordinary exception type and a base-tier signal, and which returns without re-raising
- **WHEN** the guard scans the source
- **THEN** the guard SHALL fail and identify the offending location

#### Scenario: guard accepts the permitted narrow absorb

- **GIVEN** production code that cancels a child task and awaits it inside `contextlib.suppress(asyncio.CancelledError)`
- **WHEN** the guard scans the source
- **THEN** the guard SHALL NOT report that code
- **AND** the guard SHALL pass

#### Scenario: guard ignores an ordinary exception handler

- **GIVEN** production code that catches `Exception` and returns without re-raising
- **WHEN** the guard scans the source
- **THEN** the guard SHALL NOT report that code

<!-- @trace
source: cantus-base-exception-policy
updated: 2026-08-29
code:
  - cantus/serve/channels/_googlechat_internals.py
  - cantus/serve/channels/_realtime.py
  - cantus/serve/channels/googlechat.py
tests:
  - tests/serve/channels/test_exception_policy.py
-->

---
### Requirement: Cancellation propagates out of the channel connect and heartbeat paths

A channel coroutine that is cancelled SHALL let the `asyncio.CancelledError` propagate, rather than returning as though it had finished its work. This holds for a cancellation that interrupts a retry-backoff sleep, and for one that interrupts the wait on an inbound-message stream.

A cancellation that a channel initiated against its own child task SHALL be absorbed by the code that issued the cancellation, using `contextlib.suppress(asyncio.CancelledError)` around the awaited child, and SHALL NOT be absorbed inside the child itself.

A channel's normal shutdown path SHALL NOT depend on an exception handler. `GoogleChatPubSubChannel.disconnect()` stops the streaming pull by cancelling the client library's streaming-pull future; that future resolves with a result rather than raising, so `connect()` observes the stop by checking its disconnected flag after the wait returns.

Cancellation SHALL NOT be recorded as a delivery failure. A channel's `last_error` attribute SHALL NOT be written when a coroutine is cancelled, and a cancellation SHALL NOT advance any consecutive-failure counter or backoff schedule.

#### Scenario: a cancelled retry-backoff sleep propagates

- **GIVEN** a `GoogleChatPubSubChannel` whose `connect()` is sleeping between reconnect attempts after a delivery failure
- **WHEN** the task running `connect()` is cancelled
- **THEN** the `asyncio.CancelledError` SHALL propagate out of `connect()`
- **AND** `self.last_error` SHALL NOT be set to the cancellation

#### Scenario: a cancelled inbound-stream wait propagates

- **GIVEN** a `GoogleChatPubSubChannel` whose `connect()` is awaiting the streaming-pull result
- **WHEN** the task running `connect()` is cancelled from outside the channel
- **THEN** the `asyncio.CancelledError` SHALL propagate out of `connect()`
- **AND** the cancellation SHALL NOT be counted as a delivery failure

#### Scenario: disconnect stops the pull without raising

- **GIVEN** a `GoogleChatPubSubChannel` running its streaming pull
- **WHEN** `disconnect()` cancels the streaming-pull future
- **THEN** the awaited result SHALL return rather than raise
- **AND** `connect()` SHALL observe the disconnected flag and return cleanly

#### Scenario: a cancelled heartbeat child is absorbed by its parent

- **GIVEN** a Discord gateway session whose heartbeat task has been cancelled by the session that started it
- **WHEN** the session awaits the cancelled heartbeat task
- **THEN** the `asyncio.CancelledError` SHALL propagate out of the heartbeat task
- **AND** the session SHALL absorb it with `contextlib.suppress(asyncio.CancelledError)`
- **AND** the session's shutdown SHALL otherwise proceed unchanged
