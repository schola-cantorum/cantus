## Problem

Production code under `cantus/` violates the capability spec that governs it.

`cantus-base-exception-policy` Requirement 1 states that production code SHALL NOT catch `BaseException`, "nor explicitly catch `asyncio.CancelledError`, `KeyboardInterrupt`, or `SystemExit`, in a manner that suppresses the signal (for example by `pass`, by `return`, or by converting it into an ordinary error result) without re-raising it." It permits exactly two forms: cleanup-then-reraise, and a narrow child-cancellation absorb expressed with `contextlib.suppress(asyncio.CancelledError)` around an awaited child task.

Three sites in the channel layer match neither permitted form. Two swallow a cancellation that interrupted a sleep by returning from the handler. The third returns early from a handler when a disconnect flag is set. All three are `return` inside an `except asyncio.CancelledError` block, which the requirement names explicitly as prohibited. One of the three was written by the very change that introduced this requirement.

The guard that exists to prevent exactly this regression cannot see any of them: it scans only for `except BaseException`, so an explicitly named base-tier exception passes through untouched.

Separately, the docstring and inline comment on the third site describe a mechanism that does not exist. They state that cancelling the streaming-pull future surfaces in that handler as a `CancelledError`. The client library's future overrides `cancel()` to bypass the base future's state and resolves with a result instead, so `.result()` returns normally and never raises. A test written against that false model constructs a stand-in that raises where the real library does not.

## Root Cause

The guard's scope was set to the syntactic form that the original change was cleaning up — `except BaseException` — rather than to the behaviour the requirement describes, which is suppression of a base-tier signal by any spelling. Explicitly naming `asyncio.CancelledError` is the other spelling, and it is the more common one, so the guard's blind spot covers the majority of the surface it was written to protect.

The requirement's own text was correct throughout; only the enforcement was narrow. That is why the violations survived review, the test suite, and a release: nothing mechanical was looking for them, and the requirement's prose is long enough that a reader checking a single handler does not necessarily re-derive which two forms are permitted.

## Proposed Solution

Bring the code to the requirement, then widen the guard so the requirement is enforceable as written.

Both sleep-interrupting handlers re-raise instead of returning. For the heartbeat loop this is not merely compliance: its parent already wraps the awaited child in `contextlib.suppress(asyncio.CancelledError)`, which is precisely the permitted narrow-absorb form, so re-raising from the child makes the whole path the shape the requirement describes rather than an ad-hoc pair of workarounds.

The third handler is removed entirely rather than made to re-raise. A handler whose only action is to re-raise is not a handler, and leaving one behind implies a special case that does not exist. Removing it also retires the false mechanism described in the surrounding comment and docstring, and the test that encodes that mechanism.

The guard then covers every spelling the requirement names: `BaseException` and the three base-tier exceptions, alone or inside a tuple. No exemption list is introduced, and none is needed: `contextlib.suppress` is a `with` statement rather than an exception handler, so the permitted narrow-absorb form is outside what an AST handler scan examines.

Two duplicated close-then-clear blocks in the Pub/Sub channel are extracted while the surrounding handlers are being edited. They are the direct neighbours of the changed code, and touching that code twice is the alternative.

## Non-Goals

- **Widening the requirement instead of the code.** Loosening the permitted forms to admit a flag-guarded early return was considered and rejected. The requirement's value is that the permitted forms are structurally recognisable; a form whose legitimacy depends on what a boolean means at runtime is not recognisable to a guard, and the guard would stay permanently half-enforcing.
- **An exemption list in the guard.** No production site needs one after this change, and an exemption list that can be appended to is a mechanism for silencing the guard rather than satisfying it.
- **Narrowing the last-error attribute's declared type.** It is a public attribute on three channel classes, so narrowing it is a public API surface change. It is registered as pending work to be folded into the parked hardening change, which already modifies the capability specs that own those attributes.
- **Auditing other libraries for the same false-mechanism class of comment.** Only the site being edited is corrected.
- **Any behaviour change to reconnect, backoff, or delivery semantics.** Ordinary exceptions keep every existing path.

## Success Criteria

- Every explicit base-tier exception handler under `cantus/` either re-raises within its handler block or does not exist.
- The guard fails on a handler that catches `asyncio.CancelledError`, `KeyboardInterrupt`, or `SystemExit` — alone or in a tuple — and returns without re-raising, and identifies the offending location.
- The guard continues to pass on the permitted narrow-absorb form expressed with `contextlib.suppress`.
- Cancelling the Pub/Sub channel's `connect()` task propagates the cancellation out of `connect()` rather than being recorded as a delivery failure.
- Cancelling the Discord heartbeat task leaves the parent's shutdown path unchanged, with the cancellation absorbed by the parent's existing suppression rather than by the child.
- No comment or docstring in the edited files describes the streaming-pull future as raising on cancellation.
- The capability spec's guard requirement describes the widened scope, so the specification and the enforcement agree.
- Full test suite passes; lint and type-check deltas are zero.

## Impact

- Affected specs: `cantus-base-exception-policy` (modified)
- Affected code:
  - Modified:
    - cantus/serve/channels/googlechat.py
    - cantus/serve/channels/_realtime.py
    - tests/serve/channels/test_exception_policy.py
    - openspec/specs/cantus-base-exception-policy/spec.md
  - New:
    - docs/adr/0002-base-exception-guard-scope.md
  - Removed: (none)
