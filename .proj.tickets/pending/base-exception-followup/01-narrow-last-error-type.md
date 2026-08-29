# 01: Narrow the last-error attribute's declared type

Entered: 2026-08-29
Pending reason: waiting for cantus-v1-hardening to start, so this can be folded into that change's spec delta rather than spending a full contract-change cycle on one type annotation

## What to build

A downstream user type-checking against a channel's last-error attribute sees a
type that reflects what the attribute can actually hold.

The attribute is declared as admitting any base-tier exception, across three
declaration sites. After the base-exception policy work, only ordinary
exceptions can ever reach it — every base-tier signal now propagates instead of
being recorded. The declaration is therefore wider than the behaviour.

Narrowing it is observable to a type-checking consumer, which makes it a change
to the public API surface, which routes it to the contract-change path rather
than the main line. It is far too small to justify its own propose-and-archive
cycle. The parked v1-hardening change already modifies the capability
specifications that own these attributes, so folding it in there costs close to
nothing.

The existing specifications describe the attribute's **behaviour** ("set to the
most recent exception") and say nothing about its declared type, so the fold-in
adds a type constraint rather than altering an existing requirement.

## Acceptance criteria

- [ ] All three declaration sites admit only ordinary exceptions
- [ ] The owning capability specifications state the narrowed type
- [ ] No behavioural requirement about the attribute is changed
