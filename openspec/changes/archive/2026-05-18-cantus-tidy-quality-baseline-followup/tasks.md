<!--
Each task description states:
- the behavior or contract being delivered (mypy `[unused-ignore]` warning
  no longer raised for the listed lines, or release artifact contract
  satisfied), and
- the verification target (exact CLI invocation + expected output / file
  artifact check) that proves completion.

15 條 redundant ignore 的位置與 mypy 報告 code 來源：cantus v0.3.5 release commit
4f4bbb6（libs/cantus）下執行 `uv run --frozen --extra dev mypy cantus` 輸出。
所有 line 號為 v0.3.5 source tree 的當前值；apply 階段執行前 SHALL 以 mypy
re-run 確認 line 號未漂移。所有改動皆在 `libs/cantus/` submodule 內完成；
主 repo（colab-llm-agent）submodule pointer 不在本 change scope。
-->

## 1. 清掉 cantus 原始碼內 15 條 redundant `# type: ignore[...]`（mypy `warn_unused_ignores` 報告為 unused）

- [x] 1.1 `libs/cantus/cantus/adapters/` 內 5 個 cross-framework adapter 共 8 條 ignore：`openhands.py:20`、`mcp.py:17`、`mcp.py:68`、`langchain.py:17`、`langchain.py:18`、`langchain.py:77`、`dspy.py:17`、`huggingface.py:22`。`openhands.py:20`、`mcp.py:17`、`mcp.py:68`、`langchain.py:17`、`langchain.py:18`、`langchain.py:77`、`dspy.py:17` 七行 trailing `# type: ignore[...]` 註解整段移除，import 本身與其他程式邏輯 byte-identical 保留；`huggingface.py:22` 從 `# type: ignore[import-not-found,attr-defined]` 移除 `import-not-found` 留 `# type: ignore[attr-defined]`（mypy override 已覆蓋 missing-import，但 `attr-defined` 仍 needed for `Tool` 名稱在 transformers `__all__` 動態暴露的場景）。Behavior：5 個 adapter 對外契約不變 — SDK 未安裝時依然在 module top-level import 階段 raise 同樣的 `ImportError`（訊息含 `pip install cantus[<extras>]` 指引），已安裝時 import 與後續 `expose_as_*` / `import_*` callable 行為與 v0.3.5 一致。Verify: `cd libs/cantus && uv run --frozen --extra dev mypy cantus 2>&1 | grep "cantus/adapters/" | grep "unused-ignore"` 不回任何結果（exit 1 from grep 即 expected）。
- [x] 1.2 `libs/cantus/cantus/model/providers/` 內 4 個 cloud provider lazy-import：`openai.py:45`、`groq.py:41`、`anthropic.py:44`、`google.py:46`。`openai.py:45`、`groq.py:41`、`anthropic.py:44` 三行 trailing `# type: ignore[import-not-found]` 整段移除；`google.py:46` 從 `# type: ignore[import-not-found,attr-defined,import-untyped]` 移除 `import-not-found` 留 `# type: ignore[attr-defined,import-untyped]`（mypy override 覆蓋 missing-import，但 `google.genai` 命名空間的 `attr-defined` / `import-untyped` 在 v0.3.5 仍 needed）。Behavior：四個 provider adapter 的 `_get_client()` 延遲 import 行為不變 — SDK 未安裝時依然在 `_get_client()` 呼叫點 raise `ImportError`，已安裝時 client 初始化路徑 byte-identical。Verify: `cd libs/cantus && uv run --frozen --extra dev mypy cantus 2>&1 | grep "cantus/model/providers/" | grep "unused-ignore"` 不回任何結果。
- [x] 1.3 `libs/cantus/cantus/protocols/debug.py:68` 從 `# type: ignore[union-attr,attr-defined]` 移除 `attr-defined` 留 `# type: ignore[union-attr]`（mypy 已能解析 `target._debug_enabled` 的 attribute 暴露，僅剩 `union-attr` 需要 ignore）；`libs/cantus/cantus/model/loader.py:118, 119` 兩行 trailing `# type: ignore` 整段移除（mypy override `transformers.*` 已覆蓋 missing-import）。Behavior：`debug.py` 的 `_debug_enabled` attribute monkey-patch 仍可運作，`enable_debug()` 對 Skill / Memory 兩 kind 的注入行為與 v0.3.5 一致；`loader.py` 的 `_load_with_quant_config()` 內 lazy `torch` / `transformers` import 行為不變，`mount_drive_and_load(variant="E4B"|"E2B")` end-to-end 與 v0.3.5 一致。Verify: `cd libs/cantus && uv run --frozen --extra dev mypy cantus 2>&1 | grep -E "(debug.py:68|loader.py:11[89])" | grep "unused-ignore"` 不回任何結果。

## 2. cantus v0.3.6 PATCH release artifacts（reflect internal cleanup，user-facing surface 不變）

- [x] 2.1 `libs/cantus/pyproject.toml` `[project] version` 從 `"0.3.5"` 改為 `"0.3.6"`。Behavior：`python -m build` 產出的 wheel filename 為 `cantus-0.3.6-py3-none-any.whl`，wheel metadata `Version: 0.3.6`。Verify: `grep -n '^version = ' libs/cantus/pyproject.toml` 顯示 `version = "0.3.6"`；`cd libs/cantus && uv run --frozen --extra dev python -c "from importlib.metadata import version; print(version('cantus'))"` 印出 `0.3.6`（local editable install 已 re-sync）。
- [x] 2.2 `libs/cantus/CHANGELOG.md` 頂端新增 `## [0.3.6] - 2026-05-18 — Internal Cleanup` 區塊（Keep a Changelog 格式），首行明確標示 `**ADDITIVE — no public API change, no BREAKING, no new dependencies, no new optional extras, no user-facing surface change.**`；`### Internal` 條目逐項列出 15 條 ignore 清理（依檔案分組）；`### Notes` 條目記錄 `[all] + [openhands] extras resolver conflict` 為已知 release engineering issue（屬另一支 follow-up，非本 release 範圍）。Behavior：CHANGELOG 反映 v0.3.6 為純 internal cleanup release，downstream reader 不會誤以為有任何 API 行為變動。Verify: `head -20 libs/cantus/CHANGELOG.md | grep -F "[0.3.6]"` 至少回一筆；`grep -F "no public API change" libs/cantus/CHANGELOG.md` 至少回一筆；`grep -cF "type: ignore" libs/cantus/CHANGELOG.md` ≥ 1。
- [x] 2.3 新增 `libs/cantus/MIGRATION_v0.3.5_to_v0.3.6.md`，內容說明 no user action required（升 v0.3.6 = 升 v0.3.5）；格式與既有 `MIGRATION_v0.3.4_to_v0.3.5.md` 對齊（H1 標題、Summary 段、What changed 段、Action required 段）；Action required 段明確寫 `None — this is an internal cleanup release.`。Behavior：升級指引文件齊全，downstream 從 v0.3.5 升 v0.3.6 看得到 explicit「無需任何 action」聲明。Verify: 檔案存在；`grep -F "None — this is an internal cleanup release" libs/cantus/MIGRATION_v0.3.5_to_v0.3.6.md` 至少回一筆。
- [x] 2.4 `libs/cantus/tests/test_distribution_config.py` 內所有對 `"0.3.5"` 的版本 pin assertion 更新為 `"0.3.6"`（依 v0.3.5 archive change 紀錄，該檔含 6 條 assertion 涵蓋 py.typed marker、setuptools package-data、mypy baseline、coverage baseline、pytest addopts、version pin；只有 version pin assertion 需要 bump，其他五條 byte-identical 保留）。Behavior：v0.3.5 加入的 distribution config 六條 invariant 在 v0.3.6 commit 仍全部成立。Verify: `cd libs/cantus && uv run --frozen --extra dev pytest tests/test_distribution_config.py -v` exit 0 且 stdout 顯示 `6 passed`。

## 3. 最終驗證（cantus 端 + 主 repo 端）

- [x] 3.1 cantus 端 mypy 全綠 + 無 unused-ignore：`cd libs/cantus && uv run --frozen --extra dev mypy cantus` exit 0，stdout 顯示 `Success: no issues found in 58 source files`；`uv run --frozen --extra dev mypy cantus 2>&1 | grep -c "unused-ignore"` 回 `0`。
- [x] 3.2 cantus 端 pytest 全綠 + coverage artifact 產生：`cd libs/cantus && uv run --frozen --extra dev pytest tests/` exit 0；stdout 包含 coverage 區塊（substring `"---------- coverage"` 或 `"Name              Stmts   Miss"`）；`ls libs/cantus/coverage.xml` 確認 artifact 存在。
- [x] 3.3 cantus 端 wheel build 含 py.typed marker：`cd libs/cantus && rm -rf dist/ && uv run --frozen --extra dev python -m build` 成功；`unzip -l libs/cantus/dist/cantus-0.3.6-py3-none-any.whl | grep -F "cantus/py.typed"` 至少回一筆（PEP 561 marker 仍正確 bundle 進 v0.3.6 wheel，cantus-distribution spec 第 `py.typed is shipped in the wheel` Scenario 仍滿足）。
- [x] 3.4 主 repo spectra validate 通過：`spectra validate cantus-tidy-quality-baseline-followup` exit 0；無 error 或 warning。
- [x] 3.5 主 repo spectra analyze 無 Critical / Warning：`spectra analyze cantus-tidy-quality-baseline-followup --json` 後過濾 `findings[].severity in ["critical", "warning"]` 應為空 array（依 propose skill step 9 慣例，Suggestion 嚴重度 OK）。
