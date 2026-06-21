# Security Policy

Cantus runs model-driven agents, exposes an optional HTTP server (`cantus
serve`), and connects to messaging channels. Each of those handles untrusted
input and moves secrets like API keys and channel tokens, so a bug here can do
damage. We take reports seriously even though this is a teaching project
maintained by volunteers.

## Supported versions

Security fixes land on the latest released minor version. Older versions do not
receive backports — upgrade to the newest `cantus-agent` release to stay
covered.

| Version | Supported |
| ------- | --------- |
| latest released minor (currently 0.5.x) | ✅ |
| any earlier version | ❌ — upgrade to the latest release |

Because cantus versions are immutable Git tags, a fix always ships as a new tag,
never as a moved one.

## Reporting a vulnerability

**Do not open a public issue for a security problem.** Public issues disclose
the weakness before a fix exists.

Instead, report privately through GitHub:

1. Go to the repository's **Security** tab.
2. Choose **Report a vulnerability** to open a
   [private security advisory](https://github.com/schola-cantorum/cantus/security/advisories/new).
3. Describe the issue, the affected version, and a reproduction if you have one.

Please include enough detail to reproduce: the cantus version, the provider or
channel involved, and the smallest example that triggers the problem.

## What to expect

- We aim to acknowledge a report within a week, subject to volunteer capacity.
- If the report is valid, we will work on a fix, agree on a disclosure timeline
  with you, and credit you in the release notes unless you prefer to stay
  anonymous.
- If we decide the report is out of scope, we will explain why.

## Scope notes

- Treat any API keys, bearer tokens, or channel secrets as secrets: never commit
  them, and never paste them into issues or advisories.
- The pre-publication audit gate scans the repository for leaked credentials,
  hardcoded paths, and recorded HTTP cassettes that may contain authorization
  material before any release is pushed.
