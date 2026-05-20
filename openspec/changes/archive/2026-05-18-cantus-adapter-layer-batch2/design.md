## Context

cantus v0.3.0 收斂為 Skill + Memory 雙 protocol kind 模型。v0.3.1 補上 Memory 雙層 API（`MarkdownMemory` / `AutoMemory`）+ `cantus.identity.Soul` + EventStream 持久化。v0.3.2 開立 `cantus.adapters` 套件，交付 3 件 MVP（`expose_as_anthropic_memory_tool` + `export_as_mcp_server` + `import_mcp_server`），並落地三條 capability-level convention：
- **Error naming convention**（adapter-layer spec.md「cantus.adapters error naming convention」Requirement）：handshake 失敗 `RuntimeError("<adapter>_handshake_failed: ...")`；call-time 失敗 `RuntimeError("<adapter>_remote_error: ...")` 由 Agent dispatcher 包成 `ToolErrorObservation`。
- **Skill shape preservation contract**（adapter-layer + agent-protocols spec 雙層守住）：adapter import 後 `Skill.spec_for_llm()` 回傳 top-level keys 仍恰為 `{"name", "description", "args_schema"}` byte-identical。
- **`_RemoteSkill` closure-based dispatch 模式**（v0.3.2 `mcp_client.py:91-144`）：繼承 `Skill` 但 `__init__` 繞過 signature introspection、`spec_for_llm()` 直接帶入遠端 schema、`run()` 走 closure 呼叫遠端 dispatcher。

v0.3.2 design.md line 26 + Decisions §3 明文 punt 四件跨框架 adapter 到 v0.3.3 `cantus-adapter-layer-batch2`：LangChain / DSPy / HuggingFace / OpenHands。本 change 為 cantus 教學弧承諾「畢業生畢業後能無痛接到主流 agent stack」的最後一塊。

當前程式碼狀態（2026-05-18 驗證）：`libs/cantus/cantus/adapters/` 含 `__init__.py` / `anthropic_memory.py` / `mcp.py` / `mcp_server.py` / `mcp_client.py` 五檔；`pyproject.toml` 有 9 個 extras（`runtime` / `memory` / `openai` / `anthropic` / `google` / `groq` / `mcp` / `providers` / `dev`）；`Skill.is_remote = False` 類別屬性已加（v0.3.2 落地）；`test_skill_spec_for_llm_invariant.py` 已守住 v0.3.0 shape contract。

主要 stakeholder：（1）走 cantus 教學弧的學生 — 課程畢業後接到 LangChain / DSPy / HuggingFace agent stack 是常見路徑，需要 export adapter；想用 cantus 為 host 框架但仰賴 LangChain Tool 生態的學生需要 import adapter；（2）OpenHands 用戶 — 把寫好的 cantus Skill 包成 OpenHands action 用於 software-engineering agent workflow；（3）v0.3.4 作者 — 本 change 確立的 `_RemoteSkillBase` 將被 v0.3.4 batch3（可能補 HF import / OpenHands import / mcp_memory_server）沿用。

## Goals / Non-Goals

**Goals:**

- 交付 6 個新 callable：`expose_as_langchain_tool` / `import_langchain_tool` / `expose_as_dspy_tool` / `import_dspy_tool` / `expose_as_hf_tool` / `expose_as_openhands_action`。
- 抽離 v0.3.2 `mcp_client._RemoteSkill` 為 `cantus.adapters._remote_skill._RemoteSkillBase` 共用基底，LangChain / DSPy import 方向沿用。
- 4 個 framework 各自獨立 SDK gate（`langchain.py` / `dspy.py` / `huggingface.py` / `openhands.py` 內 top-level `try: import <sdk>` + `ImportError("... pip install cantus[<name>]")`）。
- 4 個新 extras：`langchain-core>=0.3,<1` / `dspy-ai>=2.5,<3` / `transformers>=4.40,<5` / `openhands>=1.16,<2`。
- v0.3.3 ship 後 `Skill.spec_for_llm()` JSON shape **byte-identical**（既有 contract 不破，由 `test_skill_spec_for_llm_invariant.py` 雙層保險守住）。
- `cantus[mcp]`（v0.3.2 落地）+ 既有 8 個 extras pin range 與 scenarios 全部保留 **byte-identical**。
- v0.3.2 對外 API（`McpServer` / `mcp_server` / `mcp_client` / `anthropic_memory`）對使用者觀察行為 byte-identical；只允許 `mcp_client.py` 內部 `_RemoteSkill` 重新繼承 `_RemoteSkillBase` 的純 refactor。
- 提供 `MIGRATION_v0.3_to_v0.3.3.md` + `docs/protocols/adapters-batch2.md`，學生能 copy-paste 範例跑通 6 條 callable。

**Non-Goals:**

- 不引入 HuggingFace 或 OpenHands 的 import 方向（HF 介面偏 export-only、OpenHands 是 host-side runtime）。
- 不引入 `mcp_memory_server` adapter（discussion §5 第 2 件，留 v0.3.4）。
- 不引入 `openclaw_channel_compat` / `claude_agent_sdk_skill_export` / `soul_md` adapter（discussion §5 第 4-6 件，留 v0.3.4 或更後）。
- 不引入 `Adapter` ABC（v0.3.2 拍板「函式式公開介面」沿用；`_RemoteSkillBase` 為內部複用、不對外）。
- 不變動 `cantus.protocols.skill.Skill.spec_for_llm()` JSON shape。
- 不變動 v0.3.0 / v0.3.1 / v0.3.2 任何既有 import 或行為。
- 不變動 colab-llm-agent 主 repo overlay。
- 不引入 LiteLLM 或 multi-framework abstraction。
- 不為 4 個新 adapter 引入 auth / TLS / rate limiting（皆為 in-process call、無網路；OpenHands 即使有 IPC 也在 trusted local）。
- 不在 v0.3.3 範圍變動 `agent-protocols` capability spec（v0.3.2 已加的 error naming convention + shape preservation 兩條 Requirement 涵蓋本 change；新概念皆在 `adapter-layer-batch2` capability 內表達）。

## Decisions

### LangChain pin `langchain-core` 而非 `langchain` 主套件

`cantus[langchain]` 改 pin `langchain-core>=0.3,<1` 而非完整的 `langchain` aggregator。原因：（a）LangChain 自 0.1.x 起把核心抽象（`BaseTool` / `Runnable` / `BaseMessage`）拆到獨立 `langchain-core` 套件、`langchain` aggregator 反而帶 chains / agents / integrations 等大包，對 cantus adapter 只需要 `BaseTool` 而言過重；（b）`langchain-core` 0.3.x 為撰寫時穩定 release line，介面變更節奏比 `langchain` 主套件慢；（c）對學生 install footprint 也較友善（少裝 ~50MB 的 chains/agents 程式碼）。**替代方案考量**：pin `langchain>=0.3,<1`。否決原因：拉入大量學生不需要的 dependency（含 `langchain-community` 的所有 integration），且 LangChain release notes 多次提醒「只用 BaseTool 應該 pin langchain-core」。

### DSPy pin `dspy-ai>=2.5,<3`

`cantus[dspy]` pin `dspy-ai>=2.5,<3`。原因：（a）DSPy 2.5 為撰寫時穩定 release line、`dspy.Tool` 介面已穩定；（b）3.x 預期是重大版本翻轉（DSPy 2026 路線圖預告），cap 在 `<3` 避免自動升級；（c）`dspy-ai` 是 DSPy 在 PyPI 的官方套件名（`dspy` 是同一套件的舊別名、官方推薦用 `dspy-ai`）。**替代方案考量**：pin `dspy>=2.5,<3`。否決原因：`dspy` 別名未來可能 deprecated，pin 官方主名更穩。

### HuggingFace pin `transformers>=4.40,<5`

`cantus[huggingface]` pin `transformers>=4.40,<5`。原因：（a）`transformers.Tool` 介面自 4.40 起穩定（之前的 release 介面變動較頻繁）；（b）5.x 為未來重大版本，cap 在 `<5` 避免自動升級；（c）`transformers` 已在 `cantus[runtime]` extras 中以 `>=4.53.0` 出現，本 change 的 `huggingface` extras 只是 expose 給 adapter scope 使用、不重複 install（pip 會 unify）。**替代方案考量**：另開 `cantus[hf-tool]` extras 細分。否決原因：增加學生記憶負擔；`transformers>=4.40` 涵蓋本 change 所需的 `Tool` 介面、不需更細分。

### OpenHands pin `openhands>=1.16,<2`（主套件而非 sdk 子套件）

> 拍板對應 plan file Open Question #1。

`cantus[openhands]` pin `openhands>=1.16,<2` 而非 `openhands-sdk` 子套件。原因：（a）PyPI 上 `openhands` 1.16.0（2026-05-08）是 user-facing 主套件，含完整 `openhands.events.Action` 類別 + 子類（`CmdRunAction` / `IPythonRunCellAction` / etc.），是 cantus adapter 直接需要的目標；（b）`openhands-sdk` 是內部抽象層、子集 API、學生較不熟悉；（c）`openhands` 套件已自 1.16 起 re-export `openhands-sdk` 的 `Action` base class，install `openhands` 等於同時拉入 sdk 必要 import。**替代方案考量**：pin `openhands-sdk>=1.16,<2`。否決原因：學生在 OpenHands 教材 / GitHub example 看到的 import 多走 `from openhands.events import Action`、跟教材一致；如果 `openhands` 主套件未來 deprecate（無此跡象），patch change 改 pin 即可。

### LangChain / DSPy `import_*` 的 schema 轉換策略

> 拍板對應 plan file Open Question #3。

- **`import_langchain_tool(tool: BaseTool)`**：直接呼叫 `tool.args_schema.model_json_schema()`（LangChain Tool 的 `args_schema` 強制要求 Pydantic v2 `BaseModel`），把回傳 dict 設為 cantus `args_schema`。處理 `tool.args_schema is None` 的邊界：fall back 為 `{"type": "object", "properties": {}, "required": []}`（無參數 tool）。
- **`import_dspy_tool(tool: dspy.Tool)`**：從 `tool.signature.input_fields`（dict）逐 field 構建 JSON Schema：每 field name → `properties[name]`，type annotation 對應 Python type 用 `{"str": "string", "int": "integer", "float": "number", "bool": "boolean"}` mapping；required 列表為 `[name for name, field in tool.signature.input_fields.items() if not field.json_schema_extra.get("optional")]`（或 DSPy 等價判斷）。

兩條策略都**不**做 schema 標準化（normalisation）—保留 LangChain Pydantic / DSPy 原生欄位，與 v0.3.2 「不轉換、直接帶入」對齊。**替代方案考量**：自寫共用 schema converter。否決原因：framework 之間 schema 結構分歧、共用 converter 反而要套上額外抽象層；個別 adapter 走自己最直接的轉換更穩定。

### 不為 batch2 新增 `agent-protocols` delta

> 拍板對應 plan file Open Question #4。

`agent-protocols` capability spec 不在本 change 範圍。原因：（a）v0.3.2 archive 已加「`cantus.adapters` error naming convention」+「`cantus.adapters` preserves Skill.spec_for_llm JSON shape」兩條 Requirement，涵蓋「any adapter under cantus.adapters」全集；（b）本 change 4 個新 adapter 沿用同 convention、無新 contract 引入；（c）maintain 上越少 capability 越好—如果 batch3 確實需要新 contract（例：跨 process adapter 的 timeout 約定），再對 `agent-protocols` 補 delta。**替代方案考量**：補一條「batch2 specific error naming」Requirement。否決原因：v0.3.2 既有 Requirement 用 `<adapter>` 變數涵蓋所有 token，langchain / dspy / huggingface / openhands 4 個 token 自然套用。

### HuggingFace import 方向延 v0.3.4

> 拍板對應 plan file Open Question #2。

本 change **不**引入 `import_hf_tool`。原因：（a）`transformers.Tool` 在 HuggingFace 設計上是 stateless callable + JSON schema dict，沒有對等於 LangChain `BaseTool` 的執行單元；HF Tool 通常直接 inline 給 `HfAgent`、不像 LangChain Tool 那樣作為獨立 reusable unit；（b）即使技術上可以包，學生使用情境 90% 是「把 cantus Skill 給 HuggingFace agent 用」，不是反向；（c）對 OpenHands import 方向同樣 punt（OpenHands action 是 host-side runtime 結構，import 為 cantus Skill 語義不清）。**替代方案考量**：補 `import_hf_tool` 範例範圍。否決原因：教學情境不足以撐起 API、徒增維護成本。v0.3.4 batch3 評估時若有真實 user 需求再補。

### 抽離 `_RemoteSkillBase` 為共用基底

`libs/cantus/cantus/adapters/_remote_skill.py` 新增 `_RemoteSkillBase(Skill)` 類別，把 v0.3.2 `mcp_client._RemoteSkill` 三個核心模式提升到共用層：（1）`__init__` 繞過 signature introspection 直接設 `self.name` / `self.description` / `self._args_schema_dict` / `self._pre_hook = None` / `self._post_hook = None`；（2）`spec_for_llm()` 回傳 `{"name": self.name, "description": self.description, "args_schema": self._args_schema_dict}`；（3）`validate_args()` 接 dict 即直接 dict-cast（信任外部 schema）；（4）`is_remote = True` class attribute。`mcp_client.py` 的 `_RemoteSkill` 改繼承 `_RemoteSkillBase`、自己只放 `run()`（呼叫 MCP `_call_remote_tool`）與額外 attributes（`_transport` / `_command_or_url`）。LangChain / DSPy import 方向各建一個 `_LangChainRemoteSkill` / `_DspyRemoteSkill` 同樣繼承 `_RemoteSkillBase`、自己只放 `run()`。原因：（a）三個 import 方向（MCP / LangChain / DSPy）共 ~80% 邏輯相同，重複實作會 drift；（b）`_RemoteSkillBase` 是 framework-internal、不對外暴露，符合 v0.3.2「不引入 `Adapter` ABC」精神（只是私有複用基底，沒上升為對外 contract）；（c）為 v0.3.4 batch3 預留無痛擴張位（OpenHands import 真的要加時直接繼承）。**替代方案考量**：保持 `_RemoteSkill` 在 `mcp_client.py`、LangChain / DSPy 各自寫獨立 class。否決原因：3 條獨立實作維護成本高、且任何 `Skill.spec_for_llm()` shape contract 修正需要改三處易漏。

### 各 adapter 模組 SDK gate 設計

每個 adapter 模組（`langchain.py` / `dspy.py` / `huggingface.py` / `openhands.py`）採用相同的 SDK gate pattern，但**不**像 v0.3.2 `mcp.py` 那樣抽出獨立 gate file。原因：（a）v0.3.2 `mcp.py` 同時是 gate + SDK glue + re-export 三件事，本 change 4 個 adapter SDK glue 量少（每個 ~50-80 行）、不必要拆檔；（b）gate 邏輯只是 module top-level `try: import <sdk> as _<sdk>` + `except ImportError: raise ImportError("... pip install cantus[<name>]") from exc`，整合在主 adapter 模組內可讀性更高；（c）測試端用 `monkeypatch.setitem(sys.modules, "<sdk>", None)` 模擬 SDK 缺席、走 fresh re-import 路徑（沿用 v0.3.2 `test_mcp_server.py::test_import_without_mcp_sdk_raises_actionable_error` 模式）。

### Input validation 沿用 v0.3.2 audit fix 模板

每個新 callable 在 implementation contract 中強制：
- `expose_as_*(skill)`：reject non-Skill input 用 `TypeError("expose_as_<framework>_<thing> expects Skill, got <type>")`。
- `import_*(tool)`：reject 非該 framework 對應 type 用 `TypeError("import_<framework>_<thing> expects <FrameworkType>, got <type>")`；reject None 同樣處理。
- `import_*` 路徑下，handshake-time 失敗（schema 解析失敗、Tool 缺必要欄位）→ `RuntimeError("<framework>_handshake_failed: <reason>")`；call-time 失敗 → 走 `_RemoteSkillBase.run()` 既有錯誤包裝、訊息含 `<framework>_remote_error`。

不引入新類別的 Critical attack surface（無 path / shell / URL 參數），所以 v0.3.2 sharp-edge audit Trap-1 / Trap-2 / Trap-4 三條（command injection / port collision / name regex injection）不適用於本 change。

## Implementation Contract

**觀察行為（v0.3.3 ship 後）**

- `python -c "import cantus; print(cantus.__version__)"` 印 `0.3.3`。
- `python -c "from cantus.adapters import expose_as_langchain_tool, import_langchain_tool, expose_as_dspy_tool, import_dspy_tool, expose_as_hf_tool, expose_as_openhands_action"` 成功（基底安裝即可 import 函式名稱）。
- `python -c "from cantus.adapters.langchain import expose_as_langchain_tool"` 在未安裝 `cantus[langchain]` 時 raise `ImportError` 含子字串 `"pip install cantus[langchain]"`；其他 3 個 adapter 同理。
- 既有 v0.3.0 / v0.3.1 / v0.3.2 import 全部不變：`from cantus import Skill, Memory, Agent, MarkdownMemory, AutoMemory, JsonLinesPersistence`、`from cantus.identity import Soul`、`from cantus.adapters import export_as_mcp_server, import_mcp_server, expose_as_anthropic_memory_tool`、`from cantus.adapters.mcp import McpServer` 全綠。
- `Skill.spec_for_llm()` 回傳 top-level keys 仍恰為 `{"name", "description", "args_schema"}` — `test_spec_for_llm_shape_unchanged` + `..._with_hooks` 不破，且 `test_skill_spec_for_llm_invariant.py` 在 import 4 個新 adapter 模組後仍綠。
- `expose_as_langchain_tool(my_skill)` 回 `langchain_core.tools.BaseTool` 子類實例；其 `name` / `description` / `args_schema` 對齊 `my_skill.spec_for_llm()` 三鍵。
- `import_langchain_tool(some_lc_tool)` 回 cantus `Skill` 實例；其 `spec_for_llm()` top-level keys 恰為 `{"name", "description", "args_schema"}`，`is_remote == True`，`is_remote` 不在 `spec_for_llm()` 回傳 dict 內。
- `expose_as_dspy_tool` / `import_dspy_tool` / `expose_as_hf_tool` / `expose_as_openhands_action` 行為同上對齊。
- `cantus.adapters.mcp_client._RemoteSkill` 在 v0.3.3 改繼承 `_RemoteSkillBase`；外部觀察 `import_mcp_server(...)` 回傳 list[Skill] 對使用者 byte-identical（屬性 / 方法 / spec_for_llm 行為皆不變）。
- `pip install cantus` 不裝 4 個 framework SDK；`pip install cantus[langchain]` 只多裝 `langchain-core`，不裝 dspy / transformers / openhands。

**Interface 形狀**

```python
# cantus.adapters._remote_skill — 新增共用基底（私有，不在 cantus.adapters.__init__ re-export）
class _RemoteSkillBase(Skill):
    is_remote = True

    def __init__(
        self,
        *,
        name: str,
        description: str,
        args_schema_dict: dict[str, Any],
    ) -> None:
        # 繞過 Skill.__init__ 的 signature introspection
        self.name = name
        self.description = description
        self._args_schema_dict = args_schema_dict
        self._pre_hook = None
        self._post_hook = None

    def spec_for_llm(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "args_schema": self._args_schema_dict,
        }

    def validate_args(self, args: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(args, dict):
            raise TypeError(
                f"remote adapter tool args must be a dict, got {type(args).__name__}"
            )
        return dict(args)

    def run(self, **kwargs: Any) -> Any:
        raise NotImplementedError("subclass must implement run() with framework-specific dispatch")


# cantus.adapters.langchain — 新增
def expose_as_langchain_tool(skill: Skill) -> "langchain_core.tools.BaseTool": ...
def import_langchain_tool(tool: "langchain_core.tools.BaseTool") -> Skill: ...

# cantus.adapters.dspy — 新增
def expose_as_dspy_tool(skill: Skill) -> "dspy.Tool": ...
def import_dspy_tool(tool: "dspy.Tool") -> Skill: ...

# cantus.adapters.huggingface — 新增
def expose_as_hf_tool(skill: Skill) -> "transformers.Tool": ...

# cantus.adapters.openhands — 新增
def expose_as_openhands_action(skill: Skill) -> "openhands.events.Action": ...

# cantus.adapters.mcp_client._RemoteSkill — 修改：改繼承 _RemoteSkillBase（refactor，不改觀察行為）
from cantus.adapters._remote_skill import _RemoteSkillBase
class _RemoteSkill(_RemoteSkillBase):
    def __init__(self, *, tool_name, description, input_schema, transport, command_or_url) -> None:
        super().__init__(name=tool_name, description=description, args_schema_dict=input_schema)
        self._transport = transport
        self._command_or_url = command_or_url
    def run(self, **kwargs): ...  # 同 v0.3.2，呼叫 _call_remote_tool
```

**失敗模式**

- `from cantus.adapters.langchain import expose_as_langchain_tool` 在無 `langchain-core` SDK 時 raise `ImportError("cantus.adapters.langchain requires the langchain-core SDK. Run: pip install cantus[langchain]")`；`dspy` / `huggingface` / `openhands` 同理對應子字串 `"pip install cantus[dspy]"` / `"pip install cantus[huggingface]"` / `"pip install cantus[openhands]"`。
- `expose_as_langchain_tool(non_skill_obj)` → `TypeError("expose_as_langchain_tool expects Skill, got <type>")`；其他 5 個 callable 同理。
- `import_langchain_tool(non_basetool_obj)` → `TypeError("import_langchain_tool expects langchain_core.tools.BaseTool, got <type>")`；`import_dspy_tool` 同理對 `dspy.Tool`。
- `import_langchain_tool(tool_with_broken_args_schema)` → `RuntimeError("langchain_handshake_failed: <reason>")`；`import_dspy_tool` 同理對 `dspy_handshake_failed`。
- imported Skill 被呼叫時 framework 端 raise（例 LangChain Tool 內部錯誤）→ wrap 為 `RuntimeError("<framework>_remote_error: ...")`，由 Agent dispatcher 包成 `ToolErrorObservation`。

**Acceptance criteria**

- `uv run pytest libs/cantus/tests/adapters/test_remote_skill_base.py -v` 綠（含 `is_remote = True`、`spec_for_llm()` shape、`validate_args` dict-cast、`run()` `NotImplementedError`）。
- `uv run pytest libs/cantus/tests/adapters/test_langchain.py -v` 綠（含 expose round-trip、import round-trip、SDK gate `ImportError`、`is_remote == True`、`spec_for_llm` shape、handshake / remote error 子字串）。
- `uv run pytest libs/cantus/tests/adapters/test_dspy.py -v` 綠（同 langchain）。
- `uv run pytest libs/cantus/tests/adapters/test_huggingface.py -v` 綠（含 expose round-trip、SDK gate `ImportError`、non-Skill 拒絕）。
- `uv run pytest libs/cantus/tests/adapters/test_openhands.py -v` 綠（同 huggingface）。
- `uv run pytest libs/cantus/tests/adapters/test_mcp_client.py -v` 綠（v0.3.2 既有測試在 `_RemoteSkill` 繼承重組後仍綠）。
- `uv run pytest libs/cantus/tests/adapters/test_skill_spec_for_llm_invariant.py -v` 綠（含 import 4 個新 adapter 模組後 shape 不變）。
- `uv run pytest libs/cantus/tests/test_skill.py::test_spec_for_llm_shape_unchanged libs/cantus/tests/test_skill.py::test_spec_for_llm_shape_unchanged_with_hooks -v` 綠（v0.3.0 既有 contract 不破）。
- `uv run pytest libs/cantus/tests/ -v` 整體綠（v0.3.0 + v0.3.1 + v0.3.2 + v0.3.3 聯合通過）。
- `uv run ruff check libs/cantus/` 與 `uv run mypy libs/cantus/cantus/` 兩者皆零錯誤。
- `python -c "from cantus.adapters import expose_as_langchain_tool, import_langchain_tool, expose_as_dspy_tool, import_dspy_tool, expose_as_hf_tool, expose_as_openhands_action; print('ok')"` 通過。
- `python -c "import cantus; assert cantus.__version__ == '0.3.3'"` 通過；`grep '## \[0.3.3\]' libs/cantus/CHANGELOG.md` 命中。
- `uv pip install --dry-run 'cantus[langchain]'` 在 libs/cantus/ 目錄成功；同理 `cantus[dspy]` / `cantus[huggingface]` / `cantus[openhands]`。
- `uv pip install --dry-run 'cantus[providers]'` 仍成功且不解析 4 個新 framework 套件。
- `spectra validate cantus-adapter-layer-batch2` 與 `spectra analyze cantus-adapter-layer-batch2` 皆乾淨。

**Scope boundaries**

- **In scope**：
  - libs/cantus/cantus/adapters/_remote_skill.py（新；`_RemoteSkillBase` 共用基底）
  - libs/cantus/cantus/adapters/langchain.py（新；SDK gate + 2 callable）
  - libs/cantus/cantus/adapters/dspy.py（新；SDK gate + 2 callable）
  - libs/cantus/cantus/adapters/huggingface.py（新；SDK gate + 1 callable）
  - libs/cantus/cantus/adapters/openhands.py（新；SDK gate + 1 callable）
  - libs/cantus/cantus/adapters/mcp_client.py（修改；`_RemoteSkill` 改繼承 `_RemoteSkillBase`，行為 byte-identical）
  - libs/cantus/cantus/adapters/__init__.py（修改；lazy export 6 個新 callable）
  - libs/cantus/cantus/__init__.py（修改；bump `__version__`）
  - libs/cantus/pyproject.toml（修改；version bump + 4 個新 extras）
  - libs/cantus/CHANGELOG.md（修改；新增 `## [0.3.3]` 段）
  - libs/cantus/tests/adapters/test_remote_skill_base.py（新）
  - libs/cantus/tests/adapters/test_langchain.py（新）
  - libs/cantus/tests/adapters/test_dspy.py（新）
  - libs/cantus/tests/adapters/test_huggingface.py（新）
  - libs/cantus/tests/adapters/test_openhands.py（新）
  - libs/cantus/docs/protocols/adapters-batch2.md（新；4 段 + 共用 _RemoteSkillBase 段）
  - libs/cantus/MIGRATION_v0.3_to_v0.3.3.md（新；4 採用引導）
  - openspec/changes/cantus-adapter-layer-batch2/specs/adapter-layer-batch2/spec.md（新建 capability）
  - openspec/changes/cantus-adapter-layer-batch2/specs/cantus-distribution/spec.md（REMOVED + ADDED extras matrix delta）
- **Out of scope**：
  - libs/cantus/cantus/protocols/skill.py、cantus/hooks/、cantus/workflows/、cantus/identity/、cantus/protocols/memory*.py、cantus/core/event_stream*.py — 全部不動。
  - libs/cantus/cantus/adapters/mcp_server.py、mcp.py、anthropic_memory.py — v0.3.2 落地的對外行為完全不動（mcp_client.py 只允許 `_RemoteSkill` 內部繼承重組）。
  - libs/cantus/cantus/model/ 任何檔（multi-provider 是正交垂直線）。
  - colab-llm-agent 主 repo overlay。
  - `mcp_memory_server` / `openclaw_channel_compat` / `claude_agent_sdk_skill_export` / `soul_md` adapter — 全部留 v0.3.4 或更後。
  - HuggingFace / OpenHands 的 import 方向 — 留 v0.3.4 batch3 評估。
  - v0.4.0 `cantus-serve-core` 預期的 auth / TLS / rate limiting / graceful shutdown。

## Risks / Trade-offs

- **`langchain-core` SDK 升級可能引入 breaking change** → Mitigation：pin `langchain-core>=0.3,<1`；測試端用 mocked SDK 隔離；docs/protocols/adapters-batch2.md 明文「LangChain 0.4+ 需要評估再開 patch change」。
- **`dspy-ai` 3.x 變動可能破 adapter** → Mitigation：pin `dspy-ai>=2.5,<3`；3.x 出現時開獨立 patch change 評估介面變動。
- **`transformers` 5.x 變動可能破 `transformers.Tool`** → Mitigation：pin `transformers>=4.40,<5`；既有 `cantus[runtime]` 已 pin `>=4.53.0`，install 時 pip unify 取交集。
- **`openhands` 主套件未來重命名 / split** → Mitigation：pin `openhands>=1.16,<2`；如果未來 `openhands-core` 出現需重新評估，但 1.x 區間應穩定。
- **`_RemoteSkillBase` 抽離可能讓 v0.3.2 行為 drift** → Mitigation：`mcp_client.py` 修改純 inheritance refactor、行為 byte-identical；v0.3.2 既有 `test_mcp_client.py` 9 條測試在 v0.3.3 仍綠是必要條件，apply 階段強制驗。
- **LangChain Tool 的 `args_schema` 為 None 邊界** → Mitigation：`import_langchain_tool` 對 `args_schema is None` fall back 為 empty JSON Schema `{"type": "object", "properties": {}, "required": []}`。
- **DSPy Tool signature 對齊 Python typing 的精度** → Mitigation：design 明示用簡單 mapping（str / int / float / bool）；複雜 type（`list[str]` / `Optional[X]` / `Union[X, Y]`）→ fall back 為 `"string"` 並在 docstring 加 note；學生可在 docstring 改善。
- **HuggingFace `transformers.Tool` 自 4.40 後可能再變動** → Mitigation：mock SDK 測試覆蓋 expose round-trip 三個欄位（`name` / `description` / `inputs`），實際 SDK 變動由 patch change 處理。
- **OpenHands action 子類眾多（CmdRunAction / IPythonRunCellAction / FileEditAction / ...）** → Mitigation：`expose_as_openhands_action` 預設回傳通用 `openhands.events.Action` base instance（最低共識型別）；學生需要 type-specific action 可在 host code 端 manual cast；design.md 不嘗試涵蓋全部子類。
- **`Skill.spec_for_llm()` JSON shape 是 adapter 唯一仰賴的 contract，任何 v0.3.x 後續 change 不慎修改都會破** → Mitigation：v0.3.2 既有 `test_skill_spec_for_llm_invariant.py` 已守住；本 change apply 階段擴張該檔，import 4 個新 adapter 模組後仍驗。
- **本 change 4 個 framework 各自 SDK 依賴的 supply chain 風險** → Mitigation：每個 SDK 都是各 framework 官方 PyPI 套件；pin version range；本 change 不引入其他第三方；v0.2.0 LiteLLM 拒絕拍板沿用。
- **`agent-protocols` 不動，但若 batch3 引入跨 process timeout 等新 contract 會晚一輪** → Mitigation：design 明示 v0.3.4 batch3 評估時才補；本 change 不為假想需求做架構複雜化。

## Migration Plan

1. **Pre-flight**：在 propose 分支跑 `spectra validate cantus-adapter-layer-batch2` 與 `spectra analyze cantus-adapter-layer-batch2` 確認 spec delta 與 sharp-edge 皆乾淨；驗證 `openhands` 套件 PyPI 撰寫當下的最新版號落在 `>=1.16,<2` 內。
2. **實作順序**（對應 tasks.md，每 task 含 verification）：
   - 抽離 `_RemoteSkillBase` 共用基底 + 測試 →
   - `mcp_client._RemoteSkill` refactor 改繼承 `_RemoteSkillBase` + v0.3.2 既有測試仍綠驗證 →
   - 實作 `expose_as_langchain_tool` + `import_langchain_tool` + mocked LangChain SDK fixture + 測試 →
   - 實作 `expose_as_dspy_tool` + `import_dspy_tool` + mocked DSPy SDK fixture + 測試 →
   - 實作 `expose_as_hf_tool` + mocked `transformers.Tool` fixture + 測試 →
   - 實作 `expose_as_openhands_action` + mocked OpenHands SDK fixture + 測試 →
   - 更新 `cantus/adapters/__init__.py` lazy exports + 對 `test_skill_spec_for_llm_invariant.py` 擴張 →
   - bump version + CHANGELOG + docs（`docs/protocols/adapters-batch2.md` + `MIGRATION_v0.3_to_v0.3.3.md`） →
   - 整合驗證（ruff + mypy + pytest 全綠 + spectra validate / analyze clean）。
3. **發版**：完成 `spectra archive cantus-adapter-layer-batch2` 後 tag `v0.3.3` 並 push `schola-cantorum/cantus` GitHub（人類動作）。
4. **回退策略**：v0.3.3 為 MINOR additive（無 BREAKING），回退方式為把 `cantus` pin 鎖回 `v0.3.2`；舊 v0.3.2 程式碼在 v0.3.3 環境執行也應 byte-identical 行為。
5. **學生通訊**：GitHub release notes、wiki front page、Colab notebook 開頭 markdown cell 都標註「v0.3.3 為 additive，無破壞性更動；新功能：4 個跨框架 adapter — LangChain / DSPy / HuggingFace / OpenHands」；連到 `MIGRATION_v0.3_to_v0.3.3.md`。

## Open Questions

無未決問題。OpenHands PyPI 套件選擇、HuggingFace import 方向延後、LangChain / DSPy import schema 轉換策略、是否動 agent-protocols 四件已在 §Decisions 拍板。`mcp_memory_server` / `openclaw_channel_compat` / `claude_agent_sdk_skill_export` / `soul_md` 4 件確定延 v0.3.4 或更後，不留 Open Question。
