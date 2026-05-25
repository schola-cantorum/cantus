## Why

`test.yml` 上 main 從 v0.4.0 ship `cantus-serve-core` capability（commit 15781a9）至 v0.4.3（commit 1c398af）以來，每次 push 與 PR 都 fail，根本原因是 workflow 安裝 `cantus[dev]` 不含 `fastapi`，而 `tests/serve/test_arch2_smoke.py` 在模組頂部 `from fastapi.testclient import TestClient`，導致 pytest 在 collection 階段 abort（`ModuleNotFoundError: No module named 'fastapi'`），三個 Python 版本 job 全紅。`cantus-distribution` capability 的「CI test matrix runs pytest on supported Python versions」Requirement 明確要求三個 matrix job 都通過才能 merge to main，但實務上沒有任何 merge 被擋下——CI 紅燈被當作 known broken state 累積。本 change 修這條既有 Requirement，把 install 從 `[dev]` 改為 `[dev,serve]`，讓 pytest 能 collect 並執行 serve test suite。

## What Changes

- `.github/workflows/test.yml` 中 `Install cantus with dev extras` step 把 `python -m pip install -e ".[dev]"` 改為 `python -m pip install -e ".[dev,serve]"`，使 `fastapi` / `uvicorn` / `pydantic-settings` 在 CI 上可解析
- `cantus-distribution` spec 的「CI test matrix runs pytest on supported Python versions」Requirement 文字同步更新，install command 例子改為 `[dev,serve]`，並新增一條 Scenario 明列 serve test suite 必須能 collect

## Non-Goals (optional)

- **不**為其它 test files 加 `pytest.importorskip` gate（如 `tests/providers/test_google_adapter.py` 等）——本 change 只修「test.yml 安裝 extras 不足以 collect serve tests」這個具體故障；其它 tests 若有類似 latent 問題（如 provider tests 仰賴 provider extras）留給後續 change
- **不**改 `[all]` extras 定義（`cantus-agent[runtime,memory,providers,dev]`）——`[all]` 不含 `[serve]` 是既有設計，調整需另外 propose
- **不**改 `test.yml` 的其它步驟（Python 版本 matrix、`pytest` 呼叫方式、coverage 配置等）

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `cantus-distribution`：MODIFY 既有 Requirement「CI test matrix runs pytest on supported Python versions」——install command 從 `pip install -e ".[dev]"` 改為 `pip install -e ".[dev,serve]"`，並補一條 Scenario「serve test suite collects without ImportError」

## Impact

- Affected specs：`cantus-distribution`（MODIFIED Requirement）
- Affected code：
  - Modified：`.github/workflows/test.yml`（單一 install step 一行改動）
  - New：（無）
  - Removed：（無）
- Dependencies：不新增任何 third-party package；`fastapi` / `uvicorn` / `pydantic-settings` 已在 `[serve]` extras 內，pyproject 不變
- CI 行為：`test.yml` 三 OS Python matrix 在 PR + push to main 從 fail 轉為 pass（修正 v0.4.0 以來的 standing failure）
- 對 PyPI 下游使用者：無影響——`test.yml` 是 repo CI workflow，不影響 published package surface
