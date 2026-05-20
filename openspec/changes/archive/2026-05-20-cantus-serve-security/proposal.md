## Why

cantus v0.4.0 釋出 `cantus-serve-core`（FastAPI registry + `cantus.config.Settings` + Channel Protocol + dashboard）時刻意延後了 auth / secret 管理（`libs/cantus/cantus/config.py` 第 6 行留 TODO `# secret + .env management lands in cantus-serve-security (v0.4.1)`、`libs/cantus/CHANGELOG.md` 第 663 行明文「Deferred to v0.4.1: unified secret management via pydantic-settings」）。在 v0.4.1 補上 auth gate 與 SecretStr 安全載入之前，使用者一旦把 cantus serve 暴露到 loopback 之外（不論是直接綁 `0.0.0.0`、或之後接 v0.4.2 tunnel helper），所有註冊的 Skill 都會在無認證的情況下被任意外部請求觸發、且 env 內的密鑰會以明文形式進入 `repr(Settings)`、log、OpenAPI schema。本 change 把這個 v0.4.0 留下的安全缺口收掉，作為 v0.4.x 教學弧進入 deploy 章節前的必備前置。

## What Changes

- 新增 `cantus.serve.security` 模組：FastAPI dependency `require_auth()`、`AuthMode` enum（`none` / `bearer` / `api-key`）、constant-time token 比對 helper。
- `cantus.config.Settings` 新增三個欄位：`auth_mode: AuthMode = AuthMode.NONE`、`api_key: SecretStr | None = None`、`bearer_token: SecretStr | None = None`，env prefix 沿用既有 `CANTUS_SERVE_`。
- `cantus.serve.app.serve()` 整合：當 `settings.auth_mode != AuthMode.NONE` 時自動把 `Depends(require_auth)` 掛到 `POST /skills/{name}` 與 dashboard endpoints（`GET /skills` / `GET /health` / `GET /events`），dashboard 是否套 auth 由 `settings.dashboard_requires_auth: bool = True` 控制。
- `cantus.serve.__init__` export `AuthMode`、`require_auth` 兩個新公開 symbol（保持既有 `serve` / `Channel` / `LocalMockReceiver` 不變）。
- 新增 `cantus[security]` extras 別名（指向已存在於 `cantus[serve]` 的 `pydantic-settings`，作為文件性入口；不引入新 dependency、不破壞既有 `[tool.uv] conflicts` 6 pairs）。
- 新增 `libs/cantus/tests/serve/test_security.py`，含六 case 矩陣（401 缺 token / 401 錯 token / 200 bearer 通過 / 200 api-key 通過 / SecretStr 不在 `repr(settings)` 內洩漏 / SecretStr 不在 JSON serialize 內洩漏）；並在 `libs/cantus/tests/serve/test_config.py` 增 SecretStr env 載入 case。
- 新增 `libs/cantus/docs/protocols/serve.md` 的「Authentication」段（auth 三模式 + env 變數表 + 生產環境警示）。
- 新增 `libs/cantus/MIGRATION_v0.4.0_to_v0.4.1.md`：ADDITIVE release（host code 無需改動，因為 `auth_mode` 預設 `NONE` 維持 v0.4.0 行為），但 docs 明文警告生產環境必須改 `auth_mode`。
- 新增 `libs/cantus/CHANGELOG.md` 的 `## [0.4.1]` entry。

本 release 為 ADDITIVE：v0.4.0 既有 `POST /skills/{name}` / `GET /skills` / `GET /health` / `GET /events` / Channel Protocol / `app.state.channels` 行為與簽章完全不變，使用者保留 `auth_mode = NONE` 即可繼續用 v0.4.0 的呼叫方式。

## Capabilities

### New Capabilities

(none — 沿用 v0.4.0 housekeeping-v0-4-0-followup 的決定，cantus 上游 capability narrative 落在 cantus 內的 CHANGELOG、v0.4.0 到 v0.4.1 的 MIGRATION 文件、以及 docs/protocols/ 內的 serve 協定文件，不在主 repo openspec/specs/ 開新 capability spec。)

### Modified Capabilities

- `cantus-distribution`: ADDED Requirement 描述 v0.4.1 引入的 opt-in auth gate（auth_mode 三模式 + SecretStr token 欄位 + `cantus[security]` extras alias），沿用 v0.3.5 quality-baseline 的 release-content 慣例（給 cantus-distribution 加 ADDED Requirement、不開新 capability）。既有 Requirement「Cantus framework is distributed as standalone GitHub repo」內的版本字串更新由獨立的後續 change `bump-cantus-pin-to-v0-4-1` 處理。

## Impact

- Affected specs:
  - Modified: `openspec/specs/cantus-distribution/spec.md`（ADDED Requirement「Cantus serve gates Skill endpoints behind opt-in authentication」+ scenarios 涵蓋 auth_mode 三模式行為 + SecretStr 不洩漏）。
- Affected code:
  - New:
    - `libs/cantus/cantus/serve/security.py`（`AuthMode` enum、`require_auth()` dependency、constant-time compare helper）
    - `libs/cantus/tests/serve/test_security.py`（六 case 測試矩陣）
    - `libs/cantus/MIGRATION_v0.4.0_to_v0.4.1.md`（migration 文件）
  - Modified:
    - `libs/cantus/cantus/config.py`（`Settings` 新增三欄位 + `dashboard_requires_auth`）
    - `libs/cantus/cantus/serve/app.py`（`serve()` 整合 auth dependency）
    - `libs/cantus/cantus/serve/__init__.py`（export `AuthMode` / `require_auth`）
    - `libs/cantus/tests/serve/test_config.py`（增 SecretStr env 載入 case）
    - `libs/cantus/pyproject.toml`（`[project.version]` 0.4.0 → 0.4.1；`[project.optional-dependencies]` 新增 `security` extras alias）
    - `libs/cantus/docs/protocols/serve.md`（新增 Authentication 段）
    - `libs/cantus/CHANGELOG.md`（新增 `## [0.4.1]` entry）
  - Removed: 無
- Dependencies: 無新增、無移除；`pydantic>=2.0` 與 `pydantic-settings>=2.4,<3` 在 v0.4.0 已存在。
- Submodule pointer: 本 change 在 `libs/cantus` 內 commit + tag `v0.4.1` 後，submodule pointer 自然指向新 commit；主 repo `.gitmodules` 與 README/overlay 對齊由獨立 change `bump-cantus-pin-to-v0-4-1` 處理。
- Downstream: ADDITIVE。`auth_mode` 預設 `NONE` 維持 v0.4.0 行為，既有 cookbook 與 examples 無需改動；但 docs 與 MIGRATION 文件明文要求生產環境必須改 `auth_mode`。
- Tags / Releases: cantus 上游需在 commit 後手動 `git tag v0.4.1`（release notes 走 `/tw-emoji-release-note` skill 產出）；本 Spectra archive 本身不打 tag。
