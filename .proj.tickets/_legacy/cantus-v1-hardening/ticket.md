# cantus-v1-hardening: H1/H2/H4/H5/H6 hardening deferred from Gate A/B/C

Entered: 2026-05-31 (Spectra change, parked [0/18])
Frozen: 2026-11-10 (exported when Spectra was removed; see ADR on the harness-agile migration)

## Status

Legacy, frozen. Not a harness ticket yet: no `T-NNNN` id, no spec, no traceability.
When someone picks this up, it re-enters the pipeline at stage 1 (`/grill-with-docs`)
and becomes an epic; the material below is input to that conversation, not an approved spec.

## Scope (from the parked proposal)

- **H1** `OllamaChatModel(probe_on_init=False)` opt-in startup reachability probe.
- **H2** `scripts/smoke_install.sh` prechecks `command -v uv` before using it.
- **H4** `Settings.session_tracking` (default `True`) plus `cantus serve --session-tracking / --no-session-tracking`;
  `False` makes `/introspection/sessions` return `[]` and keep no run data.
- **H5** `_gated_routes()` stops relying on `is require_auth` identity.
- **H6a/b** TUI Inspector shows different placeholders for 404 (evicted) and 200-with-no-steps.
- **H6c** `PermissionsPane` docstring states the allow-list is fixed by design.

All backward compatible; H1 and H4 are opt-in. H3 (BaseException policy) shipped separately
in PR #31.

## Source material

- `spectra-export/proposal.md`, `design.md`, `tasks.md` (18 tasks, none started)
- `spectra-export/specs/<capability>/spec.md`: deltas against the capability specs that were
  deleted with `openspec/`. Read the base specs with
  `git show pre-harness-migration:openspec/specs/<capability>/spec.md`.

## 給使用者（zh-TW）

Gate A／B／C 三輪 audit 刻意延後的 v1.0 前 hardening（H1、H2、H4、H5、H6），原本是 parked 的
Spectra change，移除 Spectra 時匯出到這裡凍結。重新啟動時要從 `/grill-with-docs` 開始收斂成
epic；這裡的 proposal、design、tasks 只是參考資料，不是核准過的 spec。
