<!--
Behavior + verification convention:
- 每個 task 描述「完成後可觀察到什麼」與「用什麼動作驗證完成」
- 檔案路徑為 locator context，不能單獨作為 task
- `parallel_tasks: true`（per `.spectra.yaml`）：互不依賴、touch 不同檔案的 task 標 `[P]`
-->

## 1. CI test workflow extras 更新（落實 MODIFIED Requirement「CI test matrix runs pytest on supported Python versions」）

- [x] 1.1 為 MODIFIED Requirement「CI test matrix runs pytest on supported Python versions」更新 `.github/workflows/test.yml` 的 `Install cantus with dev extras` step：將 `python -m pip install -e ".[dev]"` 改為 `python -m pip install -e ".[dev,serve]"`，使 `fastapi` / `uvicorn` / `pydantic-settings` 進入 CI 環境；不改 Python matrix 版本、不改 `pytest` 呼叫方式、不改其它 step；驗證：`grep -F "pip install -e \".[dev,serve]\"" .github/workflows/test.yml` 命中且 step 名稱保留為 `Install cantus with dev extras`（或改為更精確的 `Install cantus with dev + serve extras`）

## 2. 本機收口驗證

- [x] 2.1 為 Scenario「serve test suite collects without ImportError」提供本機證據：在乾淨 venv 內 `uv pip install -e ".[dev,serve]"` 後跑 `pytest --collect-only tests/serve/` 應 exit 0 且不出現 `ModuleNotFoundError: No module named 'fastapi'`；驗證：CLI 輸出最後一行為 `collected N items`（N >= 6，對應 `tests/serve/` 下既有 6 個 test files）

## 3. 收尾驗證

- [ ] 3.1 為 Scenario「PR triggers full matrix」與「Push to main triggers full matrix」確認 PR branch push 後 `test.yml` 三 Python 版本 job 從 fail 翻為 pass；驗證：PR 頁面 `test / pytest on Python 3.10` / `3.11` / `3.12` 三個 check 皆 green
- [x] 3.2 `spectra validate cantus-test-yml-include-serve-extras` 通過；驗證：CLI 輸出無 error
