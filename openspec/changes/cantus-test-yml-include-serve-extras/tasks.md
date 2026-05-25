<!--
Behavior + verification convention:
- 每個 task 描述「完成後可觀察到什麼」與「用什麼動作驗證完成」
- 檔案路徑為 locator context，不能單獨作為 task
- `parallel_tasks: true`（per `.spectra.yaml`）：互不依賴、touch 不同檔案的 task 標 `[P]`
- Scope 在 PR #4 review 期間擴大（2026-05-25）：原本只修 `[dev,serve]`，發現 provider adapter tests 也因缺 SDK 紅燈，調整為 `[dev,serve,providers]`
-->

## 1. CI test workflow extras 更新（落實 MODIFIED Requirement「CI test matrix runs pytest on supported Python versions」）

- [x] 1.1 為 MODIFIED Requirement「CI test matrix runs pytest on supported Python versions」更新 `.github/workflows/test.yml` 的 install step：將 `python -m pip install -e ".[dev]"` 改為 `python -m pip install -e ".[dev,serve,providers]"`，使 `fastapi` / `uvicorn` / `pydantic-settings`（serve）與 `anthropic` / `openai` / `google-genai` / `groq`（providers）一次進入 CI 環境；不改 Python matrix 版本、不改 `pytest` 呼叫方式、不改其它 step；step 名稱改為 `Install cantus with dev + serve + providers extras` 反映實際安裝範圍；驗證：`grep -F "pip install -e \".[dev,serve,providers]\"" .github/workflows/test.yml` 命中

## 2. 本機收口驗證

- [x] 2.1 為 Scenario「serve test suite collects without ImportError」與「provider adapter SDK imports resolve at install time」提供本機證據：在乾淨 venv 內 `uv pip install -e ".[dev,serve,providers]"` 後跑 `pytest --collect-only tests/` 應 exit 0 且不出現 `ModuleNotFoundError: No module named 'fastapi' / 'anthropic' / 'openai'`；驗證：CLI 輸出 `collected N items`（N >= 538，對應整套 test suite）；可選擇先跑 `pytest tests/providers/test_anthropic_adapter.py tests/providers/test_openai_adapter.py tests/providers/test_nvidia_adapter.py` 觀察 PASS

## 3. 收尾驗證

- [ ] 3.1 為 Scenario「PR triggers full matrix」、「Push to main triggers full matrix」、「serve test suite collects without ImportError」、「provider adapter SDK imports resolve at install time」確認 PR branch push 後 `test.yml` 三 Python 版本 job 從 fail 翻為 pass；驗證：PR #4 頁面 `test / pytest on Python 3.10` / `3.11` / `3.12` 三個 check 皆 green
- [x] 3.2 `spectra validate cantus-test-yml-include-serve-extras` 通過；驗證：CLI 輸出無 error
