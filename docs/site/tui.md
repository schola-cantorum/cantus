# `cantus tui` — Terminal Observability Dashboard

`cantus tui` is a **read-only** terminal dashboard (a Textual TUI). It connects to a running `cantus serve` instance over the server's `/introspection` and `/health` endpoints and renders its live runtime state. The dashboard never issues commands and never mutates server state, so you can leave it running against a class demo or a misbehaving server without worrying that a keystroke will change anything.

For the data contract behind each endpoint, see [`docs/protocols/serve.md`](./protocols/serve.md#introspection-endpoints).

## Install and launch

`cantus tui` requires the `tui` extra. The Textual dependency sits behind a lazy import gate, so if the extra is missing, `cantus tui` prints a hint to run `pip install cantus-agent[tui]`:

```bash
pip install cantus-agent[tui]
cantus tui --url http://127.0.0.1:8765
```

Common flags:

| Flag | Default | Purpose |
| --- | --- | --- |
| `--url` | `http://127.0.0.1:8765` | Base URL of the target `cantus serve` (either a local address or one exposed through a tunnel) |
| `--auth-mode` | `none` | Authentication mode; one of `none` / `bearer` / `api-key`. Must match the server's `auth_mode` |
| `--poll-interval` | `2.0` | Auto-refresh interval, in seconds |

## The five tabs

On startup the screen is a `TabbedContent` with five tabs. Press number keys `1`–`5` to switch between them:

| Key | Tab | What it shows |
| --- | --- | --- |
| `1` | **Dashboard** | The main overview. On the left, a Sessions list (the most recently dispatched runs). On the right, Queue (the queue depth per channel) and Health (whether the server is reachable, plus `cantus_version`) stacked top to bottom |
| `2` | **Skills** | The `name`, `description`, and `args_schema` of every registered Skill. A skill that an in-flight run is currently using is marked |
| `3` | **Permissions** | The effective authentication settings: `auth_mode`, the `dashboard_requires_auth` / `introspection_requires_auth` flags, and the list of paths behind the auth gate. Token values are **never** shown |
| `4` | **Dataflow** | The static component topology derived from the registry and channels (nodes and edges: serve, the event stream, each skill, each channel) |
| `5` | **Inspector** | The Action/Observation step trace for a single run (drilled in from a Sessions row; see below) |

## Key bindings

| Key | Action |
| --- | --- |
| `1`–`5` | Switch to the matching tab |
| `Enter` | On a Sessions row in the Dashboard, press `Enter` to jump to the **Inspector** tab and show that run's step trace (moving the highlighted row also updates the Inspector content) |
| `r` | Refresh immediately (without waiting for the next auto-poll) |
| `p` | Pause / resume auto-refresh (when paused, the subtitle shows `PAUSED`) |
| `q` | Quit |

The workflow step `summary` shown in the Inspector is a **structural projection** that the server has already sanitized. It contains only the skill name, the argument **key names**, and the result or exception **type name**. It **never** contains argument values, result values, or raw exception messages. So even when you connect to a publicly exposed server, the Inspector will not surface secrets or PII.

## The three authentication modes

`--auth-mode` must match the server's `auth_mode`. The token is always read from an **environment variable**, never passed in through a command-line flag:

| `--auth-mode` | Header | Token environment variable |
| --- | --- | --- |
| `none` (default) | (none) | — |
| `bearer` | `Authorization: Bearer <token>` | `CANTUS_SERVE_BEARER_TOKEN` |
| `api-key` | `X-API-Key: <token>` | `CANTUS_SERVE_API_KEY` |

Example: connecting to a server protected in bearer mode:

```bash
export CANTUS_SERVE_BEARER_TOKEN="<your-token>"
cantus tui --url https://<slug>.trycloudflare.com --auth-mode bearer
```

> ⚠️ **Tokens are credentials.** Treat `CANTUS_SERVE_BEARER_TOKEN` and `CANTUS_SERVE_API_KEY` the way you would a password: keep them out of source code, logs, screenshots, and version control, and rotate them if one leaks. `cantus tui` masks tokens internally, so no tab ever prints their plaintext value.

## How it relates to serve

`cantus tui` does not start a server of its own. It is only the render side of `/introspection`. Start `cantus serve` in another shell first (see [`docs/quickstart-desktop.md`](./quickstart-desktop.md)), then point this tool at it. If the server enables introspection with `auth_mode=none`, it prints a warning at startup noting that `/introspection` is currently reachable without authentication. Once it is exposed publicly, switch to `bearer` or `api-key`.
