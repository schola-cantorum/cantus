# Migrating cantus v0.3.6 → v0.4.0

**Release date: 2026-05-20.** v0.4.0 是 `cantus-serve-core` minor release，
帶來三件事：(1) 新的 `cantus.serve` + `cantus.config` 模組與 `cantus[serve]`
extras 群組；(2) mypy `strict = true` 全面開啟（v0.3.6 baseline 是
`disallow_untyped_defs = false`）；(3) `pyproject.toml` 新增
`[tool.uv] conflicts` 宣告，修掉 fresh `uv sync` 下 `cantus[all]` 與
`cantus[openhands]` 的 resolver 衝突。沒有 API 移除、沒有 import path
rename，所有 v0.3.x ship 的 callables 仍可在原路徑取得。

## Breaking

- **mypy `strict = true` 啟用。** v0.3.6 的 mypy baseline 仍允許
  `disallow_untyped_defs = false`；v0.4.0 起 cantus 自身原始碼通過
  `mypy --strict`，public symbols 從原本 `Any`-leaking 收緊成精確型別。
  屬於 ADDITIVE / 收緊 (tightening) — 過去寫成 `Any`-相容的 narrowing
  程式碼仍會綠；但若下游有 `# type: ignore[assignment]` 抑制過 cantus
  回傳值，可能因為型別收緊而觸發 `warn_unused_ignores`，需要把多餘的
  ignore 拿掉。
- **`cantus.__version__` 對齊回 `"0.4.0"`。** v0.3.6 的 `pyproject.toml`
  與 `cantus/__init__.py` `__version__` 之間有 drift（pyproject 標
  `0.3.6`、`__init__.py` 仍寫 `"0.3.4"`）；v0.4.0 一併修正，兩處皆為
  `"0.4.0"`。下游若有對 `cantus.__version__` 做 assert，需要更新。
- **無 API 移除、無 import path rename。** 所有 v0.3.x ship 的
  callables（`cantus.hooks.*`、`cantus.workflows.*`、`cantus.adapters.*`、
  `cantus.memory.*`、`cantus.soul.*`、`cantus.events.*` 等）仍在原路徑、
  原 signature 可用；v0.4.0 純粹是疊加 `cantus.serve` / `cantus.config`
  兩個新模組。

## ADDITIVE

- **`cantus.serve(registry, *, channels=None, settings=None) -> FastAPI`
  入口。** 把 `Registry` 內註冊的 Skill 自動接成 REST endpoint，並在
  `/docs` 暴露 OpenAPI / Swagger UI。需要 `pip install cantus[serve]`
  才能 import。
- **`cantus.config.Settings`（pydantic-settings `BaseSettings`）。**
  12-factor 環境變數設定，prefix 為 `CANTUS_SERVE_`（例：
  `CANTUS_SERVE_PORT`、`CANTUS_SERVE_HOST`）。
- **`cantus.serve.channel.Channel` Protocol + `LocalMockReceiver`。**
  Channel 抽象的型別協定；內建一個 in-memory FIFO 的 `LocalMockReceiver`
  供本地測試與 demo。
- **`cantus.serve` / `cantus.config` 為 PEP 562 top-level lazy
  attributes。** 沒有裝 `cantus[serve]` extras 的環境，`import cantus`
  本身仍正常；只在第一次 access `cantus.serve` 或 `cantus.config` 時才
  觸發 SDK gate（缺 fastapi / uvicorn / pydantic-settings 時報 friendly
  ImportError）。
- **新 `cantus[serve]` extras 群組。** Pin 為
  `fastapi>=0.115,<1`、`uvicorn>=0.30,<1`、`pydantic-settings>=2.4,<3`。
- **`[tool.uv] conflicts` 宣告。** `cantus[all]` 與 `cantus[openhands]`
  宣告為互斥；fresh `uv sync` 不會再撞
  `cantus[all] and cantus[openhands] are incompatible` 的 resolver
  error。pip 安裝路徑無感（pip 不解析 `[tool.uv]` table），純 uv-only
  metadata。
- **mypy overrides 補加三組 `ignore_missing_imports = true`。**
  `fastapi.*`、`uvicorn.*`、`pydantic_settings.*` 三組 third-party
  module 的 mypy override 已內建，下游不需要自己加。

## Migration steps

1. 取得 serve SDK：`pip install -U 'cantus[serve]'`（或 uv：
   `uv add 'cantus[serve]'`）。不需要 server 能力的下游可以略過此步驟，
   `import cantus` 本身不會因為缺 fastapi / uvicorn /
   pydantic-settings 而 fail。
2. 若下游有對 cantus 程式碼跑 mypy 嚴格檢查，重跑一次 `mypy --strict`
   確認過綠；如果遇到 `warn_unused_ignores` 觸發的 warning，把對應的
   多餘 `# type: ignore[...]` 清掉即可（cantus 的回傳型別已經收緊，
   不再需要抑制）。
3. 若下游 cantus 環境採用 uv，重新跑一次 `uv sync`。v0.4.0 的
   `[tool.uv] conflicts` 已經宣告 `cantus[all]` ⊗ `cantus[openhands]`
   互斥，fresh sync 不再需要 `--frozen` 或手動指定 extras 子集來繞開
   resolver。
4. （Optional）若要起一個 server，最小程式碼如下：

   ```python
   from cantus import serve
   from cantus.core.registry import Registry
   import uvicorn

   uvicorn.run(serve(Registry()))
   ```

   把自己的 Skill 註冊到 `Registry` 後，`/docs` 即為自動生成的 Swagger
   UI。
5. 12-factor 環境變數透過 `CANTUS_SERVE_` prefix 設定，例：

   ```bash
   export CANTUS_SERVE_PORT=8080
   export CANTUS_SERVE_HOST=0.0.0.0
   ```

   `cantus.config.Settings` 會自動 pick up。

若直接從 v0.3.5（或更早）升上 v0.4.0，請依序套用
`MIGRATION_v0.3.5_to_v0.3.6.md` 與本檔；v0.3.6 是純內部清理 release，
無額外 host code 動作。
