## Why

cantus v0.3.0 確立 Skill / Memory 雙 kind 模型，v0.3.1 補上 Memory 雙層 API + Soul identity + EventStream 持久化 — 三大教學抽象（Skill / Memory / Soul）落地後，學生與 LLM 的接觸面已完整。但 cantus 與業界既有生態（MCP、Anthropic Memory tool、LangChain / DSPy / OpenHands）之間缺少 bridge：學生若要把寫好的 cantus Skill 接到 Claude Desktop / Claude Code、把 Anthropic Memory tool 包成 cantus Memory、或 import 第三方 MCP server 為 cantus Skill — 全部得自己寫 glue code。

`openspec/discussions/cantus-framework-shift.md` §4（MCP 雙向 adapter）+ §5（`cantus.adapters` 模組）凍結了本 change 的範圍與業界依據；roadmap §4 trigger condition「`cantus-memory-soul-twin-tier` shipped」由 v0.3.1 ship 後滿足、「MCP spec revision target chosen (2025-11-25 or later)」由 design.md 直接選 2025-11-25 拍板。

本 change 為 v0.3.x 教學弧最後一塊：把 cantus 從「自成一格的教學框架」升級為「與業界生態互通的教學框架」，學生畢業後接到任何主流 agent stack（Claude / OpenClaw / LangChain）都能直接用 cantus 訓練到的 mental model。

## What Changes

- **新增** `cantus.adapters` 套件 root，含 `__init__.py` 公開 3 個函式 + `cantus.adapters.mcp` 子模組。
- **新增** MCP server mode：`cantus.adapters.export_as_mcp_server(skills: list[Skill], name: str, version: str) -> McpServer` — 把 cantus Skill list 轉成符合 MCP 2025-11-25 spec 的 tool schema、啟動 stdio 或 streamable HTTP transport。`McpServer.run(transport: Literal["stdio", "http"])` 阻塞執行 server loop。
- **新增** MCP client mode：`cantus.adapters.import_mcp_server(transport: str, command_or_url: str) -> list[Skill]` — 連到外部 MCP server、enumerate tool list、把每個 MCP tool 包成 cantus `Skill` 實例（含正確的 `args_schema` JSON Schema 轉換、`description` 來自 MCP tool description）。
- **新增** Anthropic Memory adapter：`cantus.adapters.expose_as_anthropic_memory_tool(memory: Memory | AutoMemory) -> dict` — 把 cantus Memory 包成 Anthropic Memory tool spec 的 4-action（`view` / `create` / `str_replace` / `delete`）tool 定義 dict，可直接餵給 Anthropic API `tools=[...]`。
- **新增** 對應測試與 fixtures：MCP server stdio loopback test、MCP client connect-then-list mocked test、Anthropic Memory tool spec shape 守住 test、`Skill.spec_for_llm()` JSON shape 不變 regression test。
- **修改** `cantus-distribution`：新增 `cantus[mcp]` extras（依賴 `mcp` SDK package）；現有 `openai` / `anthropic` / `google` / `groq` / `providers` / `dev` 6 個 extras 不動。
- **修改** `agent-protocols`：新增「Skill 與外部 tool schema 之間透過 cantus.adapters 模組 bridge」Requirement，明示「`Skill.spec_for_llm()` 是 adapter 唯一讀取的 LLM-facing JSON」與「adapter 不應變更 Skill 行為，純包裝 schema」。

## Non-Goals (optional)

- **不在本 change 引入 HuggingFace / LangChain / DSPy / OpenHands adapter — 延至 v0.3.3 `cantus-adapter-layer-batch2`**（user 2026-05-18 拍板 MVP scope；roadmap §4 「~7 adapters」由 v0.3.2 + v0.3.3 兩 change 共同滿足，本 change 只交付 3 件）。
- 不引入 MCP resource、prompt、roots 三類 MCP 概念（v0.3.2 只做 tools 一類；其餘 MCP 概念列入 v0.4+ 評估）。
- 不為 MCP server 引入 auth / TLS / rate limiting — 教學定位，假設 trusted local environment；production-grade serve 留給 v0.4.0 `cantus-serve-core`。
- 不變動 `cantus.protocols.skill.Skill.spec_for_llm()` JSON shape（既有 v0.3.0 contract，必須維持）— 任何讓 adapter 工作的支援都在 adapter 端做轉換，不污染 Skill。
- 不引入 LiteLLM 或任何 multi-provider abstraction 進 adapter — supply chain 風險已由 user 在 v0.2.0 拍板拒絕，本 change 沿用。
- 不變動 v0.3.1 落地的 Memory 雙層 / Soul / EventStream 持久化任何 API — 只在 adapter 端 expose 它們到外部 schema。

## Capabilities

### New Capabilities

- `adapter-layer`: cantus 與業界 agent stack 之間的 bridge — MCP 雙向 adapter + Anthropic Memory tool adapter；adapter 為純包裝層，不變動 Skill / Memory 行為。

### Modified Capabilities

- `agent-protocols`: 新增 Requirement「Skill 透過 cantus.adapters 對外暴露時保持 spec_for_llm() JSON shape 不變」，把 v0.3.0 既有的 shape contract 提升為 capability-level 對外承諾；adapter 不引入新 protocol kind。
- `cantus-distribution`: 既有 extras matrix Requirement 擴張 `cantus[mcp]`；REMOVED + ADDED 兩段 delta 避開 RENAMED + MODIFIED archive 跳過陷阱（feedback memory `feedback_spectra_renamed_modified.md`）。

## Impact

- Affected specs:
  - New: openspec/specs/adapter-layer/spec.md（archive 時建立）
  - Modified: openspec/specs/agent-protocols/spec.md
  - Modified: openspec/specs/cantus-distribution/spec.md
- Affected code:
  - New:
    - libs/cantus/cantus/adapters/__init__.py
    - libs/cantus/cantus/adapters/mcp.py
    - libs/cantus/cantus/adapters/mcp_server.py
    - libs/cantus/cantus/adapters/mcp_client.py
    - libs/cantus/cantus/adapters/anthropic_memory.py
    - libs/cantus/tests/adapters/test_mcp_server.py
    - libs/cantus/tests/adapters/test_mcp_client.py
    - libs/cantus/tests/adapters/test_anthropic_memory.py
    - libs/cantus/tests/adapters/test_skill_spec_for_llm_invariant.py
    - libs/cantus/tests/adapters/fixtures/sample_mcp_tools.json
    - libs/cantus/docs/protocols/adapters.md
    - libs/cantus/MIGRATION_v0.3_to_v0.3.2.md
  - Modified:
    - libs/cantus/cantus/__init__.py
    - libs/cantus/pyproject.toml
    - libs/cantus/CHANGELOG.md
  - Removed: 無（v0.3.2 為 MINOR additive，無刪除）
