## Why

cantus v0.3.2 archived 三件 adapter MVP（`expose_as_anthropic_memory_tool` + `export_as_mcp_server` + `import_mcp_server`），已建立 `cantus.adapters` 套件骨架、error naming convention（`<adapter>_handshake_failed` / `<adapter>_remote_error`）、`_RemoteSkill` closure-based dispatch、lazy SDK gate、`Skill.spec_for_llm()` shape preservation 雙層保險。v0.3.2 design.md 明文 punt 四件跨框架 adapter 到 v0.3.3 `cantus-adapter-layer-batch2`：**LangChain / DSPy / HuggingFace / OpenHands**。

`openspec/discussions/cantus-framework-shift.md` §5 列出「7 個目標 adapter」清單；v0.3.2 ship 後完成 2 件（anthropic_memory + mcp_skill_bridge），本 change 再交付 4 件、累積完成 6 件，最後 1 件（`mcp_memory_server`）視 v0.3.4 排程。本 change 是 cantus 教學弧「畢業生畢業後能無痛接到主流 agent stack」承諾的最後一塊：LangChain 是 agent 生態中心、DSPy 是 prompt-as-program 主流、HuggingFace 是模型 hub 入口、OpenHands 是 software-engineer agent 業界基準。

## What Changes

- **新增** `cantus.adapters` 6 個跨框架 callable：
  - `cantus.adapters.expose_as_langchain_tool(skill: Skill) -> langchain_core.tools.BaseTool`：把任一 cantus Skill 轉成 LangChain Tool（`spec_for_llm()` 的 `args_schema` 轉成 LangChain Tool 的 `args_schema` Pydantic 模型）。
  - `cantus.adapters.import_langchain_tool(tool: BaseTool) -> Skill`：把 LangChain Tool 包成 cantus Skill 實例（沿用 `_RemoteSkill` 模式但 transport 為 in-process callable）。
  - `cantus.adapters.expose_as_dspy_tool(skill: Skill) -> dspy.Tool`：cantus Skill → DSPy Tool；signature 由 `args_schema` 的 properties 推導。
  - `cantus.adapters.import_dspy_tool(tool: dspy.Tool) -> Skill`：DSPy Tool → cantus Skill。
  - `cantus.adapters.expose_as_hf_tool(skill: Skill) -> transformers.Tool`：cantus Skill → HuggingFace transformers Tool（export-only；HF Tool 內部介面偏 export，import 方向延 v0.3.4）。
  - `cantus.adapters.expose_as_openhands_action(skill: Skill) -> openhands.events.Action`：cantus Skill → OpenHands action（export-only；OpenHands 是 host-side agent runtime，import 方向不對等）。
- **新增** `libs/cantus/cantus/adapters/_remote_skill.py`：把 v0.3.2 `mcp_client._RemoteSkill` 抽離為 `cantus.adapters._remote_skill._RemoteSkillBase` 共用基底，供 LangChain / DSPy import 方向沿用（closure-based dispatch + `is_remote=True` marker + bypass signature introspection 三件全保留）。
- **新增** `libs/cantus/cantus/adapters/{langchain,dspy,huggingface,openhands}.py` 四個 adapter 模組，各自含 SDK gate（`try: import <sdk>` + `ImportError("... pip install cantus[<name>]")`）+ 主 callable。
- **修改** `cantus.adapters.mcp_client` 的 `_RemoteSkill` 改為繼承新的 `_RemoteSkillBase`（純 refactor、不破壞 v0.3.2 對外 API 與行為）。
- **新增** `cantus[langchain]` / `cantus[dspy]` / `cantus[huggingface]` / `cantus[openhands]` 四個 extras。
- **新增** 對應測試：每個 adapter 一份 `tests/adapters/test_<framework>.py`（4 個檔）+ 一份 `tests/adapters/test_remote_skill_base.py`；mocked SDK fixture，無需實際安裝任一 framework。
- **修改** `cantus-distribution` capability：擴張 extras matrix 加 4 個新 key。
- **修改** `cantus.adapters.__init__.py`：lazy export 6 個新 callable（沿用 v0.3.2 lazy import stub 模式）。
- **修改** `libs/cantus/cantus/__init__.py`：bump `__version__` 為 `0.3.3`；其他 v0.3.0 / v0.3.1 / v0.3.2 既有 import 全部不變。

## Non-Goals

- **不引入 HuggingFace 或 OpenHands 的 import 方向**：HF Tool 介面偏 export-only（HF 預設用 dict spec），OpenHands 是 host-side runtime（import 不對等）。兩者延 v0.3.4 batch3 評估，不在本 change 範圍。
- **不引入 `mcp_memory_server` adapter**（discussion §5 第 2 件）：留 v0.3.4 評估。
- **不引入 `openclaw_channel_compat` / `claude_agent_sdk_skill_export` / `soul_md` adapter**（discussion §5 第 4-6 件）：本 change 為跨框架 batch，這 3 件性質不同（OpenClaw / SOUL.md 格式對接），延後到 v0.3.4 或 v0.3.5。
- **不引入 `Adapter` ABC**：v0.3.2 Decisions §2 拍板「函式式公開介面」，本 change 完全沿用。`_RemoteSkillBase` 是 cantus 內部複用基底、不對外暴露，不違背此拍板。
- **不變動 `cantus.protocols.skill.Skill.spec_for_llm()` JSON shape**（v0.3.0 contract）—任何 schema 轉換在 adapter 端完成；v0.3.2 落地的 `test_skill_spec_for_llm_invariant.py` 自動回證 v0.3.3 新模組 import 後仍守住 shape。
- **不變動 v0.3.1 落地的 Memory 雙層 / Soul / EventStream persistence 任何 API**。
- **不變動 v0.3.2 落地的 `mcp_server.py` / `anthropic_memory.py` 對外行為**；只對 `mcp_client.py` 內部 `_RemoteSkill` 做 inheritance refactor（bytewise compatible）。
- **不引入 LiteLLM 或任何 multi-framework abstraction**（v0.2.0 supply chain 拍板沿用）。
- **不變動 colab-llm-agent 主 repo overlay**（`examples/` / `templates/` / `notebooks/`）：對齊由獨立「bump cantus pin to v0.3.3」change 處理（同 v0.3.1 / v0.3.2 處理方式）。
- **不引入 v0.4.0 `cantus-serve-core` 預期的 auth / TLS / rate limiting / graceful shutdown**。

## Capabilities

### New Capabilities

- `adapter-layer-batch2`：4 個跨框架 adapter（LangChain / DSPy / HuggingFace / OpenHands）+ `_RemoteSkillBase` 共用基底；adapter 為純包裝層、不變動 Skill 行為、不引入新 protocol kind。對齊 v0.3.2 既有 `adapter-layer` capability 確立的 contract（error naming convention、Skill shape preservation）。

### Modified Capabilities

- `cantus-distribution`：擴張 extras matrix 加 `langchain` / `dspy` / `huggingface` / `openhands` 4 個 key；既有 8 個 extras（`runtime` / `memory` / `openai` / `anthropic` / `google` / `groq` / `providers` / `mcp` / `dev`）pin range 與 scenarios 全部保留 byte-identical（REMOVED + ADDED 兩段 delta、避開同名 rename 陷阱）。

## Impact

- Affected specs:
  - New: openspec/specs/adapter-layer-batch2/spec.md（archive 時建立）
  - Modified: openspec/specs/cantus-distribution/spec.md
- Affected code:
  - New:
    - libs/cantus/cantus/adapters/_remote_skill.py
    - libs/cantus/cantus/adapters/langchain.py
    - libs/cantus/cantus/adapters/dspy.py
    - libs/cantus/cantus/adapters/huggingface.py
    - libs/cantus/cantus/adapters/openhands.py
    - libs/cantus/tests/adapters/test_remote_skill_base.py
    - libs/cantus/tests/adapters/test_langchain.py
    - libs/cantus/tests/adapters/test_dspy.py
    - libs/cantus/tests/adapters/test_huggingface.py
    - libs/cantus/tests/adapters/test_openhands.py
    - libs/cantus/docs/protocols/adapters-batch2.md
    - libs/cantus/MIGRATION_v0.3_to_v0.3.3.md
  - Modified:
    - libs/cantus/cantus/adapters/__init__.py
    - libs/cantus/cantus/adapters/mcp_client.py
    - libs/cantus/cantus/__init__.py
    - libs/cantus/pyproject.toml
    - libs/cantus/CHANGELOG.md
  - Removed: 無（v0.3.3 為 MINOR additive，無刪除）
