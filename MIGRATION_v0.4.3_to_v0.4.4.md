# Migrating cantus v0.4.3 → v0.4.4

**Release date: 2026-05-27.** v0.4.4 is a **Gate A audit hardening PATCH release**. The `cantus` Python package surface, every public symbol, every endpoint, every default value, every extras group (`cantus[serve]` / `cantus[security]` / `cantus[providers]` / `cantus[openhands]` / `cantus[runtime]`), and every `[tool.uv] conflicts` declaration is byte-identical to v0.4.3. Five hardening fixes from the post-Gate-A audit (2 High + 2 Medium + 1 Low) ship together; none of them break callers.

## Breaking

None. v0.4.4 is fully ADDITIVE / hardening-only. `cantus.__version__` reports `"0.4.4"`; pin assertions that hardcoded `"0.4.3"` need to update — that is the only code-side touch.

Two error-message wording changes (L1, H2) are non-breaking by category: the new strings preserve the same exception type (`ValueError` / `RegistryImportError`) and remain machine-stable identifiers. Downstream code that string-matched against the literal `"v0.2.1 ships only:"` substring will need to relax to substring-matching on `"supported providers:"` or, preferably, switch to type-based handling.

## Impact on OSS users — minimal

If you only consume cantus via `pip install cantus-agent`, the user-visible surface stays the same:

```python
import cantus
print(cantus.__version__)  # "0.4.4"

import importlib.metadata
print(importlib.metadata.version("cantus-agent"))  # "0.4.4"
```

Upgrade command:

```bash
pip install --upgrade cantus-agent==0.4.4
```

## What changed — five Gate A audit hardening items

The post-Gate-A audit (`/spectra-audit` + `/humane-prose-audit`, covering the A0 / C1 / A1' archive trio) surfaced 2 High + 4 Medium + 2 Low findings. The five items below — labelled **L1 / H1 / H2 / M1 / M4** — are the v1.0-pre-resolvable subset shipped in this release; the remaining audit items (M2 base-URL reachability, M3 `uv` smoke pre-check) are deferred to follow-up changes.

### L1 — `load_chat_model` docstring + error message are now version-agnostic

`cantus.model.factory.load_chat_model` previously hardcoded `v0.2.1 ships only: ...` in both its docstring and the `ValueError` raised on unsupported provider. The string was stale ever since the registry grew past the v0.2.1 five-provider list. v0.4.4 replaces both with version-agnostic phrasing that automatically reflects the current `_REGISTRY`:

- Docstring: `Supported providers: {dynamic list joined from _REGISTRY}.`
- Error message: `unsupported provider {provider!r}; supported providers: {dynamic list}`

The `_REGISTRY` is read at module-import time and embedded into the docstring via `load_chat_model.__doc__.format(...)`. Adding a new provider (e.g. the Ollama provider already shipped in v0.4.3) automatically refreshes both surfaces.

**Migration impact:** None for typical callers. If your code grep'd for the literal `v0.2.1 ships only:` substring (highly unusual), update to match `supported providers:` instead.

### H1 — `OllamaChatModel` class docstring discloses silent api_key override

`cantus.model.providers.ollama.OllamaChatModel.__init__` accepts an `api_key` argument for signature compatibility with sibling provider adapters, but the value is silently overridden with the sentinel string `"ollama"` before reaching the underlying OpenAI SDK call. v0.4.3's docstring was a single sentence and did not disclose this. v0.4.4 expands the docstring to explicitly state:

- the `api_key` parameter is accepted but ignored;
- the Ollama daemon does not authenticate requests;
- the adapter unconditionally substitutes the sentinel `"ollama"` for the OpenAI SDK's `api_key` field;
- to run against a non-local Ollama instance (Docker / remote VM / etc.), pass `base_url=` pointing at that host's `/v1` endpoint.

**Migration impact:** Behaviour-identical to v0.4.3; the change is documentation-only. Tooling that introspects `OllamaChatModel.__doc__` may now report a longer string.

### H2 — CLI import resolvers validate identifier shape + list candidates on typo

`cantus.cli._resolve_registry_import` and `cantus.cli._resolve_channels_import` resolve `module.dotted.path:attr` specs from `--registry-import` / `--channels` flags. v0.4.3 raised `RegistryImportError` with the raw `AttributeError` message on missing-attribute, which was often confusing (the user wouldn't see the available names). v0.4.4 adds two hardening checks:

1. **`isidentifier()` precheck** on the `attr` portion — invalid Python identifiers (`123`, `foo-bar`, etc.) raise `RegistryImportError` immediately with the message `attr_name '...' is not a valid Python identifier (spec '...')`.
2. **Candidate-listing on `AttributeError`** — when the module imports but the attribute is missing, the error now lists up to 10 sorted public attribute names (filtering double-underscore names), with the literal suffix `(truncated)` appended when more than 10 exist. Modules with zero public attributes report `; available: (none)`.

The error formatting helper is named `_format_attribute_error` and is a pure function (input fully determines output).

**Migration impact:** Failure mode preserved (`RegistryImportError` still raised); only the message is richer. Test code that string-matches on `module 'x' has no attribute 'y'` continues to work, since the new format keeps that exact prefix and appends `(spec '...'); available: ...` after it.

### M1 — `cantus serve` prints stderr WARNING for unsafe default combination

`cantus serve` accepts `--auth-mode` and `--dashboard` as independent flags. The combination `auth-mode=none AND dashboard=on` is the v0.4.0 default (preserved here for backwards compatibility), but it exposes an unauthenticated dashboard surface — fine for local dev, unsafe for any externally reachable deployment.

v0.4.4 adds a stderr WARNING line at server start when this combination is detected:

```
cantus serve: WARNING: auth-mode=none AND dashboard=on — server is unauthenticated and exposes dashboard endpoints. Set --auth-mode (bearer|api-key) or CANTUS_SERVE_DASHBOARD=false for production deployment.
```

The warning:

- writes to **stderr** (not stdout, not dashboard log), so it does not pollute structured output capture;
- does **not** affect exit code, does **not** block startup;
- fires after `_build_app` succeeds (so a config-level `ValueError` won't trigger a false warning).

**Migration impact:** Production deployments that intentionally accept the unsafe default (e.g. behind a reverse-proxy that does the auth) will see a one-line WARNING per process start. Either flip the default (`--auth-mode bearer|api-key` or `CANTUS_SERVE_DASHBOARD=false`) or suppress stderr at the wrapper level.

### M4 — `--channels` runtime Protocol check

`cantus.cli._resolve_channels_import` resolves `--channels` specs and previously appended every resolved object to the channels list without a type check. A non-channel object (a `Registry`, a plain string, a dict) would surface as a crash deep inside `cantus.serve` startup. v0.4.4 imports `cantus.serve.channel.Channel` (already a `@runtime_checkable Protocol`) **lazily** inside `_resolve_channels_import` and adds an `isinstance(obj, Channel)` check; non-conforming values raise `RegistryImportError` at startup with the message `channel '<spec>' resolved to <type>, expected cantus.serve.channel.Channel-compatible object`.

The lazy import preserves the property that `import cantus.cli` does not transitively pull `cantus.serve.channel` into `sys.modules` — verified by a subprocess-isolated test.

**Migration impact:** Any `--channels` target that previously slipped through but crashed deep inside startup now fails earlier with a clear type-mismatch message. Channel objects that satisfy the `Channel` Protocol surface unchanged.

## No breaking change to anything else

- `cantus.serve`, `cantus.config`, `cantus.serve.security`, `cantus.adapters`, `cantus.workflows`, `cantus.hooks`, and every other module preserve their v0.4.3 public API surface byte-identical.
- `Registry.KINDS`, the ten exposed callables in `cantus.adapters`, and the five `cantus.workflows` building blocks are unchanged.
- The `[tool.uv] conflicts` declaration with its six pairwise entries is unchanged.
- The `cantus[openhands]` extras `python_version >= "3.12" and python_version < "3.13"` marker and the `cantus[runtime]` extras `sys_platform == 'linux'` marker on `bitsandbytes` are unchanged from v0.4.3.
- The OIDC release pipeline (`.github/workflows/release.yml`) and the CI matrices (`.github/workflows/test.yml`, `.github/workflows/cross-platform-install.yml`) shipped at v0.4.3 are unchanged.
- The `cantus-serve-cli` entry-point (`cantus.cli:main`) and the six `cantus serve` args (`--host` / `--port` / `--auth-mode` / `--bearer-token-env` / `--api-keys-env` / `--registry-import` / `--channels` / `--dashboard`) are unchanged.
- The desktop walkthrough surface (`docs/quickstart-desktop.md`, `cantus[providers-ollama]` extras) shipped at v0.4.3 is unchanged.

## Why ship Gate A hardening as a PATCH release?

v0.4.4 contains no new public symbol, no new endpoint, no new extras group, and no new spec capability. Every change is either a docstring, an error message, or an additional startup-time validation that fails earlier (never later) and never silently changes existing behaviour. By SemVer this is a PATCH release. MINOR (`0.5.0`) is reserved for the next runtime capability arc — first candidate is **B1 `cantus-channel-gateway-webhook`** (LINE / Telegram / Google Chat HTTP webhook + HMAC-SHA256 verifier).

## Audit-finding cross-reference

| Item | Severity | Surface | Spec |
|------|---------|---------|------|
| L1   | Low     | `cantus.model.factory.load_chat_model` docstring + ValueError | `model-providers` MODIFIED |
| H1   | High    | `cantus.model.providers.ollama.OllamaChatModel` class docstring | `cantus-local-llm-and-desktop-walkthrough` MODIFIED |
| H2   | High    | `cantus.cli._resolve_registry_import` / `_resolve_channels_import` | `cantus-serve-cli` MODIFIED |
| M1   | Medium  | `cantus serve` startup WARNING | `cantus-serve-cli` ADDED Requirement |
| M4   | Medium  | `cantus.cli._resolve_channels_import` Protocol check | `cantus-serve-cli` MODIFIED |

Audit items deferred to follow-ups: **M2** base-URL reachability ping (would make adapter init I/O-bound — out of scope), **M3** `uv` availability precheck in `smoke_install.sh` (distribution-followup change).

Full archive: `openspec/changes/archive/2026-05-27-gate-a-audit-hardening/`.
