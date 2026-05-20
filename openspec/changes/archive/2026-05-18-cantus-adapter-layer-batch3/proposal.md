## Why

cantus v0.3.3 透過 `adapter-layer-batch2` 一次出貨 6 個 cross-framework callable（LangChain / DSPy 雙向、HuggingFace / OpenHands 只 export），並在 spec 把 HF 與 OpenHands 的 import 方向標記為「deferred to v0.3.4 batch3 evaluation」。實際 spike 後發現兩條 punt 的語義並不對稱：

- **HuggingFace** `transformers.Tool` 是 callable + `inputs` dict-schema，跟 LangChain `BaseTool.invoke` 對等，import 方向可以乾淨對應；只是 batch2 時程沒做完。
- **OpenHands** `openhands.events.Action` 是 declarative event record，被 host runtime dispatch，本身沒有 `__call__`，沒有可以餵進 `Skill.run(**kwargs)` 的 callable。把 Action 包成 Skill 沒有可呼叫的目標，這是**語義不對稱**，不是工時問題。

batch3 收尾的正確做法是：補上 `import_hf_tool` 把雙向矩陣補齊到 7 個 callable，並把 spec 對 OpenHands import 方向的措辭從「deferred」改成「not applicable」，避免未來再有人去做永遠做不出來的 batch3b。

## What Changes

- 新增 `cantus.adapters.import_hf_tool(tool: Tool) -> Skill`：以新的 `_HuggingFaceRemoteSkill(_RemoteSkillBase)` 內部子類包裝 HF Tool；schema 從 `tool.inputs` dict 直接組成 v0.3.0 JSON Schema dict（`type: "object"` + properties + required）。
- `cantus.adapters.__init__` 加入 `import_hf_tool` 的 lazy-load stub 並列入 `__all__`，與既有 6 個 batch2 callable 對齊。
- 改寫 `cantus/adapters/huggingface.py` docstring，移除「intentionally deferred to v0.3.4 batch3」段落，改成「雙向皆支援」。
- 改寫 `cantus/adapters/openhands.py` docstring，把「deferred to v0.3.4 batch3」改成「import direction is permanently not applicable — OpenHands Action is a declarative event record with no `__call__`」。
- 刪除 `tests/adapters/test_huggingface.py::test_import_hf_tool_not_exported` 與 `tests/adapters/test_openhands.py::test_import_openhands_action_not_exported` 兩個防呆 case；HF 端改成正向 round-trip 測試，OpenHands 端改成永久 not-exported assertion（保留 ImportError 行為但理由改為「semantic mismatch」）。
- cantus 版本 0.3.3 → 0.3.4；無 BREAKING、無新 dependency、無新 optional extras。

## Non-Goals

- **不做 `import_openhands_action`**。OpenHands Action 沒有 callable 可被 `Skill.run` 呼叫，沒有意義的語義可以實作。本 change 把 spec 措辭從 v0.3.3 的「deferred」永久改為「not applicable」，避免未來再開 batch3b。
- **不做 `mcp_memory_server`**。v0.3.3 spec Purpose 提到「mcp_memory_server queued for v0.3.4 evaluation」，但本 change 只負責收尾 cross-framework import 方向，mcp_memory_server 另排。
- **不改 `_RemoteSkillBase`**。v0.3.3 已穩定，新增 subclass 即可。
- **不重構** LangChain / DSPy / MCP 既有 adapter。
- **不在主 repo 開 `bump-cantus-pin-to-v0-3-4`**。等 cantus v0.3.4 git tag 出來後另開。
- **不順便 backfill** `agent-protocols` / `identity-protocol` / `llm-wiki` / `memory-protocol` / `model-loader` / `model-providers` 6 個遺留 Purpose TBD，避免 scope creep；另開 change 處理。

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `adapter-layer-batch2`: 新增 `import_hf_tool` Requirement；MODIFY `expose_as_hf_tool` Requirement（移除「NOT introduce import_hf_tool」與 deferred scenarios）；MODIFY `expose_as_openhands_action` Requirement（把 import 方向措辭從 deferred 改為 not applicable，scenario 保留 ImportError 行為但理由更新）；MODIFY 「six callables」總覽 Requirement → 七 callables。

## Impact

- Affected specs:
  - Modified: `openspec/specs/adapter-layer-batch2/spec.md`
- Affected code:
  - Modified: `libs/cantus/cantus/adapters/huggingface.py`, `libs/cantus/cantus/adapters/openhands.py`, `libs/cantus/cantus/adapters/__init__.py`, `libs/cantus/tests/adapters/test_huggingface.py`, `libs/cantus/tests/adapters/test_openhands.py`, `libs/cantus/pyproject.toml`, `libs/cantus/cantus/__init__.py`, `libs/cantus/CHANGELOG.md`, `libs/cantus/docs/protocols/adapters-batch2.md`
  - New: `libs/cantus/docs/protocols/adapters-batch3.md`, `libs/cantus/MIGRATION_v0.3.3_to_v0.3.4.md`
  - Removed: (none)
- Dependencies: 無新增；`cantus[huggingface]` 既存 extras 已涵蓋 transformers SDK。
- Downstream: 主 repo 之後需另開 `bump-cantus-pin-to-v0-3-4` 把 submodule pin 推進到 v0.3.4 並調整 demo / README 版本字串。
