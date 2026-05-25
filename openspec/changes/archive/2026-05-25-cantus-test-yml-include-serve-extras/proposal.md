## Why

`test.yml` 上 main 從 v0.4.0 ship `cantus-serve-core` capability（commit 15781a9）至 v0.4.3（commit 1c398af）以來，每次 push 與 PR 都 fail，CI 紅燈被當作 known broken state 累積。`cantus-distribution` capability 的「CI test matrix runs pytest on supported Python versions」Requirement 明確要求三個 matrix job 都通過才能 merge to main，但實務上沒有任何 merge 被擋下。

PR review 期間發現 CI 紅燈**有三個失敗源**，原本 proposal 只認到第一個：

1. **collection 階段 abort**：`tests/serve/test_arch2_smoke.py` 在模組頂部 `from fastapi.testclient import TestClient`，而 `[dev]` 不含 `fastapi`，導致 pytest collection 直接掛掉
2. **provider adapter tests FAIL**：`tests/providers/test_anthropic_adapter.py` / `test_openai_adapter.py` / `test_nvidia_adapter.py` 內部 `import anthropic` / `import openai` 來建立 fake SDK，`[dev]` 不含這些 provider SDK，導致 11 個 test FAIL with `ModuleNotFoundError: No module named 'anthropic' / 'openai'`（`test_google_adapter.py` 與 `test_groq_adapter.py` 因為使用 httpx mock 不需 SDK 故 PASS）
3. **hardcoded version anchor tests 過時**：`tests/test_public_api.py::test_version_is_0_4_1`、`tests/test_distribution_config.py::test_pyproject_version_bumped_to_0_4_1`、`tests/serve/test_lazy_import.py::test_import_cantus_succeeds_without_serve_sdks` 三個 test 寫死 `assert cantus.__version__ == "0.4.1"`（function name 也含 `_0_4_1`），但 pyproject 早已 bump 到 0.4.3，導致 v0.4.2 / v0.4.3 release 以來這 3 個 test 持續 FAIL；屬於「每次 release 都會掉的 anti-pattern」

本 change 一次補完整 CI install extras 並修掉 anti-pattern：
- install 從 `[dev]` 改為 `[dev,serve,providers]`，讓 pytest 能 collect 並執行整個 test suite
- 3 個版本錨點 test 改為 semver regex / dynamic 比對，function rename 去除 `_0_4_1` 後綴

## What Changes

- `.github/workflows/test.yml` 中 `Install cantus with dev extras` step 把 `python -m pip install -e ".[dev]"` 改為 `python -m pip install -e ".[dev,serve,providers]"`，使 `fastapi` / `uvicorn` / `pydantic-settings`（serve）與 `anthropic` / `openai` / `google-genai` / `groq`（providers）在 CI 上可解析；step 名稱改為 `Install cantus with dev + serve + providers extras` 反映實際安裝範圍
- `tests/test_public_api.py::test_version_is_0_4_1` → rename 為 `test_version_is_valid_semver`，改為 `re.fullmatch(r"\d+\.\d+\.\d+", cantus.__version__)`
- `tests/test_distribution_config.py::test_pyproject_version_bumped_to_0_4_1` → rename 為 `test_pyproject_version_is_valid_semver`，改為 semver regex；`test_dunder_version_aligned_with_pyproject`（line 175 起）的 dynamic 比對保留不動
- `tests/serve/test_lazy_import.py::test_import_cantus_succeeds_without_serve_sdks` → assert 從 `cantus.__version__ == "0.4.1"` 改為 `assert cantus.__version__`（truthy 即可，重點是「沒 serve SDK 也能 import + 拿到 version」）
- `cantus-distribution` spec 的「CI test matrix runs pytest on supported Python versions」Requirement 文字同步更新，install command 例子改為 `[dev,serve,providers]`，並新增三條 Scenario：「serve test suite collects without ImportError」、「provider adapter SDK imports resolve at install time」、「version anchor tests stay dynamic, never hardcoded」

## Non-Goals (optional)

- **不**為其它 test files 加 `pytest.importorskip` gate——本 change 採取「補完整 install extras」路徑，不引入新的 skip 機制；如果未來新增的 optional dependency tests 想用 skip 而非 install，再另案處理
- **不**改 `[all]` extras 定義（`cantus-agent[runtime,memory,providers,dev]`，不含 `[serve]`）——`[all]` 的歷史設計是「runtime model + adapters + dev tools」，不涵蓋 server 部署層；調整需另外 propose
- **不**改 `test.yml` 的其它步驟（Python 版本 matrix、`pytest` 呼叫方式、coverage 配置等）

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `cantus-distribution`：MODIFY 既有 Requirement「CI test matrix runs pytest on supported Python versions」——install command 從 `pip install -e ".[dev]"` 改為 `pip install -e ".[dev,serve,providers]"`，並補三條 Scenario：「serve test suite collects without ImportError」、「provider adapter SDK imports resolve at install time」、「version anchor tests stay dynamic, never hardcoded」

## Impact

- Affected specs：`cantus-distribution`（MODIFIED Requirement）
- Affected code：
  - Modified：`.github/workflows/test.yml`（單一 install step + step 名稱）
  - Modified：`tests/test_public_api.py`、`tests/test_distribution_config.py`、`tests/serve/test_lazy_import.py`（3 個版本錨點 test 去除 hardcoded `0.4.1`）
  - New：（無）
  - Removed：（無）
- Dependencies：不新增任何 third-party package；`fastapi` / `uvicorn` / `pydantic-settings` 已在 `[serve]` extras 內，`anthropic` / `openai` / `google-genai` / `groq` 已在 `[providers]` extras 內，pyproject 不變
- CI 行為：`test.yml` 三 Python 版本 matrix 在 PR + push to main 從 fail 轉為 pass（修正 v0.4.0 以來的 standing failure）
- 對 PyPI 下游使用者：無影響——`test.yml` 是 repo CI workflow，不影響 published `cantus-agent` package surface（byte-identical）
