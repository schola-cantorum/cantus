# The base-exception guard carries no exemption list

The `cantus-base-exception-policy` capability forbids production code from
swallowing a base-tier signal, and permits exactly two forms: cleanup then
re-raise, and a narrow absorb of the cancellation of a child task the code
itself just cancelled. The guard that enforces it originally scanned only for
`except BaseException`, so none of the three `except asyncio.CancelledError`
blocks in the channel layer were visible to it — including one written by the
change that introduced the requirement. We widened the guard to cover every
spelling the requirement names (`BaseException`, `asyncio.CancelledError` and a
bare `CancelledError`, `KeyboardInterrupt`, `SystemExit`, each alone or inside a
tuple, plus a bare `except:`), and we did **not** add a list of exempted
locations.

The reason an exemption list is unnecessary is not obvious from reading either
the guard or the policy, which is why it is written down here: the permitted
narrow absorb is expressed as `contextlib.suppress(asyncio.CancelledError)`.
That is a context manager, so in the AST it is a `With` node, not an
`ExceptHandler` — it is structurally outside what a handler scan examines and
can never be flagged. The permitted form and the enforced form do not overlap,
so there is nothing to exempt.

## Considered options

- **Relax the requirement** to permit an absorb guarded by an explicit
  self-cancellation flag. Rejected: whether such a return is legitimate depends
  on the value of a boolean at run time, which no AST scan can determine. The
  guard would be permanently half-enforcing, and the whole value of the two
  permitted forms is that they are *structurally* recognisable.
- **Keep the narrow guard and add an exemption list** for the handlers it would
  newly flag. Rejected: after this change no production location needs an
  exemption, and a list that can be appended to is a mechanism for silencing the
  guard rather than for satisfying it. Once the first entry is added there is no
  natural point at which to stop.

## Consequences

- Any future absorb of a self-issued cancellation must be written in the
  `contextlib.suppress` form to pass the guard. This is the intent, not a side
  effect.
- The guard's coverage is now a claim the test suite verifies both ways: a
  synthetic sample per spelling must be reported, and the permitted `suppress`
  form and an ordinary `except Exception` must not be.
- A base-tier handler whose body contains any `raise` still passes. The guard
  checks that the signal is re-raised, not where in the handler body it happens.
