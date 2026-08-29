## ADDED Requirements

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

---

### Requirement: A codebase guard enforces the BaseException policy

The test suite SHALL include a guard that scans the source of the `cantus` package and asserts that every `except BaseException` (including `except BaseException as <name>`) occurrence in production code re-raises within its handler block (the cleanup-then-reraise form). The guard SHALL fail if any production `except BaseException` block does not re-raise, so that future regressions of this policy are caught automatically.

#### Scenario: guard passes on the conforming codebase

- **WHEN** the guard scans the `cantus` package source after this change is applied
- **THEN** every `except BaseException` occurrence found SHALL re-raise within its handler block
- **AND** the guard SHALL pass

#### Scenario: guard fails on a non-reraising BaseException catch

- **GIVEN** a hypothetical production block that catches `BaseException` and returns without re-raising
- **WHEN** the guard scans the source
- **THEN** the guard SHALL fail and identify the offending location
