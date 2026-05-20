## Why

cantus v0.3.0 確立 Skill + Memory 雙 kind 模型，但 Memory 端僅完成 protocol 收斂，雙層 API 與身份抽象皆未交付。`openspec/discussions/cantus-framework-shift.md` §8（Memory C++）與 §9（SOUL.md / Identity）已凍結 v0.3.1 範圍：底層 4 件 Memory 實作（補齊 `MarkdownMemory`）、高階 `AutoMemory` 暴露 LLM 自主 CRUD、EventStream 持久化跨 session reload、`cantus.identity.Soul` 載入 SOUL.md 6 區塊。

v0.3.0 design.md `Non-Goals` 明列「不引入 Memory 高階 API、SOUL identity、EventStream persistence — 保留給 v0.3.1」；roadmap §3 trigger condition「`cantus-protocol-reorg` shipped」已於 2026-05-18 滿足。本 change 為 v0.3.x 教學弧「Skill = 能力 / Memory = 記憶 / Soul = 身份」三大抽象並列的最後一塊。

## What Changes

- **新增** `cantus.protocols.memory.MarkdownMemory`：file-backed Memory 實作，path 為 explicit 建構子參數，`recall` / `remember` 對 markdown frontmatter + body 做 lossless round-trip。
- **新增** `cantus.protocols.memory.AutoMemory`：高階 Memory，接受任一底層 Memory 為 backend；暴露 4 個 LLM-facing tool（`view` / `create` / `str_replace` / `delete`），對齊 Anthropic Memory tool spec。
- **新增** `cantus.core.event_stream` 的檔案持久化層：JSON-Lines append-only 後端 + cross-session reload；既有 in-memory EventStream 行為保留為預設。
- **新增** `cantus.identity` 模組：`Soul` 類別 + `Soul.from_file(path)` 工廠，解析 SOUL.md 六區塊（Name & Role / Personality / Rules / Tools / Output format / Handoffs）；`Agent(model=..., soul=soul)` 自動把 soul render 為 system prompt 前綴。
- **擴張** `cantus.protocols.memory.Turn` dataclass：新增 `timestamp: datetime | None`、`type: Literal["user", "assistant", "system", "tool"]`；舊有 `user` / `assistant` 兩個欄位**保留**以維持 v0.3.0 ABI（兩欄位若同時提供則自動推導 `type`）。
- **修改** `cantus.core.agent.Agent.__init__`：新增 `soul: Soul | None = None` 關鍵字參數；Memory 仍維持 explicit injection by parameter（不自動）— 對齊 discussion §8 C2 拍板。
- **修改** 8 個 capability spec 之一：`agent-protocols` 增 Memory 雙層 + EventStream persistence Scenarios；`agent-runtime` 增 EventStream 持久化插件點 Scenarios。
- **不修改** v0.3.0 既有 Requirement「Memory has class-first entry only」— discussion §8 C1 拍板 Memory 保持 class-only entry，不引入 `@memory` decorator 或 `register_memory` 函式入口；既有測試 `libs/cantus/tests/test_memory.py::test_no_memory_decorator_at_module_level` 沿用、不刪。

## Capabilities

### New Capabilities

- `memory-protocol`: Memory 雙層 API — 底層 4 件 explicit Memory（`ShortTermMemory` / `BM25Memory` / `EmbeddingMemory` / `MarkdownMemory`）+ 高階 `AutoMemory` 暴露 4 個 LLM-facing tool；`Turn` data model 擴張（保留 v0.3.0 ABI 不破壞）。
- `identity-protocol`: `cantus.identity.Soul` 從 SOUL.md 載入六區塊身份結構，注入 Agent system prompt；高階 API，底層保留學生手寫 system prompt 路徑。

### Modified Capabilities

- `agent-protocols`: 既有「Memory has class-first entry only」Requirement 沿用不動；新增 Memory 雙層 + AutoMemory 4-tool LLM-facing surface 的 Requirement；新增 `Soul` 與 `Agent.soul=` 關鍵字的 Requirement。
- `agent-runtime`: 新增 EventStream 持久化（JSON-Lines append-only + cross-session reload）的 Requirement；既有 in-memory 預設行為作為 Requirement scenario 保留。

## Impact

- Affected specs:
  - New: openspec/specs/memory-protocol/spec.md（由本 change archive 時建立）
  - New: openspec/specs/identity-protocol/spec.md（由本 change archive 時建立）
  - Modified: openspec/specs/agent-protocols/spec.md
  - Modified: openspec/specs/agent-runtime/spec.md
- Affected code:
  - New:
    - libs/cantus/cantus/protocols/memory_markdown.py
    - libs/cantus/cantus/protocols/memory_auto.py
    - libs/cantus/cantus/identity/__init__.py
    - libs/cantus/cantus/identity/soul.py
    - libs/cantus/cantus/core/event_stream_persistence.py
    - libs/cantus/tests/test_memory_markdown.py
    - libs/cantus/tests/test_memory_auto.py
    - libs/cantus/tests/test_identity_soul.py
    - libs/cantus/tests/test_event_stream_persistence.py
    - libs/cantus/tests/fixtures/soul_minimal.md
    - libs/cantus/tests/fixtures/soul_full.md
    - libs/cantus/docs/protocols/memory.md
    - libs/cantus/docs/protocols/identity.md
    - libs/cantus/MIGRATION_v0.3_to_v0.3.1.md
  - Modified:
    - libs/cantus/cantus/protocols/memory.py
    - libs/cantus/cantus/core/agent.py
    - libs/cantus/cantus/core/event_stream.py
    - libs/cantus/cantus/__init__.py
    - libs/cantus/pyproject.toml
    - libs/cantus/CHANGELOG.md
  - Removed: 無（v0.3.1 為 MINOR additive，無刪除）
