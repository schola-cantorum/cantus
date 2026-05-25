<!--
Behavior + verification convention:
- 每個 task 描述「完成後可觀察到什麼」與「用什麼動作驗證完成」
- 檔案路徑為 locator context，不能單獨作為 task
- `parallel_tasks: true`（per `.spectra.yaml`）：互不依賴、touch 不同檔案的 task 標 `[P]`
- Scope 在 PR #4 review 期間兩次擴大（2026-05-25）：
  - 第一次：發現 provider adapter tests 因缺 SDK 紅燈，install 從 `[dev,serve]` 改為 `[dev,serve,providers]`
  - 第二次：發現 3 個 hardcoded `0.4.1` 版本錨點 test FAIL，改為 semver regex / dynamic 比對，並補一條 Scenario 抑制 anti-pattern
-->

## 1. CI test workflow extras 更新（落實 MODIFIED Requirement「CI test matrix runs pytest on supported Python versions」）

- [x] 1.1 為 MODIFIED Requirement「CI test matrix runs pytest on supported Python versions」更新 `.github/workflows/test.yml` 的 install step：將 `python -m pip install -e ".[dev]"` 改為 `python -m pip install -e ".[dev,serve,providers]"`，使 `fastapi` / `uvicorn` / `pydantic-settings`（serve）與 `anthropic` / `openai` / `google-genai` / `groq`（providers）一次進入 CI 環境；不改 Python matrix 版本、不改 `pytest` 呼叫方式、不改其它 step；step 名稱改為 `Install cantus with dev + serve + providers extras` 反映實際安裝範圍；驗證：`grep -F "pip install -e \".[dev,serve,providers]\"" .github/workflows/test.yml` 命中

- [x] 1.2 為新 Scenario「version anchor tests stay dynamic, never hardcoded」修掉 3 個 hardcoded `0.4.1` 版本錨點 test：
  - `tests/test_public_api.py`：`test_version_is_0_4_1` → `test_version_is_valid_semver`，assert 改為 `re.fullmatch(r"\d+\.\d+\.\d+", cantus.__version__)`
  - `tests/test_distribution_config.py`：`test_pyproject_version_bumped_to_0_4_1` → `test_pyproject_version_is_valid_semver`，assert 改為 semver regex；既有的 `test_dunder_version_aligned_with_pyproject` 保留不動
  - `tests/serve/test_lazy_import.py`：`test_import_cantus_succeeds_without_serve_sdks` 內部 assert 從 `cantus.__version__ == "0.4.1"` 改為 `assert cantus.__version__`（truthy 即可）
  - 驗證：`.venv/bin/pytest tests/test_public_api.py::test_version_is_valid_semver tests/test_distribution_config.py::test_pyproject_version_is_valid_semver tests/serve/test_lazy_import.py::test_import_cantus_succeeds_without_serve_sdks --no-cov` 三個皆 PASS

## 2. 本機收口驗證

- [x] 2.1 為 Scenario「serve test suite collects without ImportError」與「provider adapter SDK imports resolve at install time」提供本機證據：在乾淨 venv 內 `uv pip install -e ".[dev,serve,providers]"` 後跑 `pytest --collect-only tests/` 應 exit 0 且不出現 `ModuleNotFoundError: No module named 'fastapi' / 'anthropic' / 'openai'`；驗證：CLI 輸出 `collected N items`（N >= 538，對應整套 test suite）；可選擇先跑 `pytest tests/providers/test_anthropic_adapter.py tests/providers/test_openai_adapter.py tests/providers/test_nvidia_adapter.py` 觀察 PASS

- [x] 2.2 為新 Scenario「version anchor tests stay dynamic, never hardcoded」+ task 1.2 提供本機綠燈：`.venv/bin/pytest tests/ --no-cov -q` 整套 535 passed, 3 skipped, 0 failed

## 3. 收尾驗證

- [x] 3.1 為 Scenario「PR triggers full matrix」、「Push to main triggers full matrix」、「serve test suite collects without ImportError」、「provider adapter SDK imports resolve at install time」、「version anchor tests stay dynamic, never hardcoded」確認 PR branch push 後 `test.yml` 三 Python 版本 job 從 fail 翻為 pass；驗證：PR #4 頁面 `test / pytest on Python 3.10` / `3.11` / `3.12` 三個 check 皆 green
- [x] 3.2 `spectra validate cantus-test-yml-include-serve-extras` 通過；驗證：CLI 輸出無 error
