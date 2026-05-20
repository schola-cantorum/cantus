## 1. 紅燈測試（先寫測試、後實作）

- [x] 1.1 在 `libs/cantus/tests/adapters/test_huggingface.py` 加 `test_import_returns_v030_shaped_skill`：用 `_FakeHfTool(inputs={"q": {"type": "string", "description": "Query string"}})` 餵 `import_hf_tool`，assert `spec_for_llm()` 三鍵 shape、`name/description` 對應、`args_schema.properties.q.type == "string"`、`required == ["q"]`，覆蓋 `import_hf_tool wraps HuggingFace transformers Tool as cantus Skill` Requirement 的「Imported HuggingFace tool surfaces v0.3.0 spec shape」scenario；驗證：執行 `pytest libs/cantus/tests/adapters/test_huggingface.py::test_import_returns_v030_shaped_skill -v` 應**紅燈**（功能尚未實作）。
- [x] 1.2 [P] 加 `test_imported_skill_is_remote_marker`：assert `skill.is_remote is True` 且 `"is_remote" not in skill.spec_for_llm()`，覆蓋 spec scenario「Imported HuggingFace skill carries is_remote marker without leaking into spec_for_llm」；驗證：執行對應 pytest 應紅燈。
- [x] 1.3 [P] 加 `test_imported_skill_dispatches_to_underlying_tool`：fake tool 的 `__call__` 回 `f"hit:{kwargs['q']}"`，assert `skill(q="cantus") == "hit:cantus"`，覆蓋 spec scenario「Imported HuggingFace skill dispatches to underlying tool」與設計決定 HF `run()` 直接呼叫 `tool(**kwargs)`；驗證：對應 pytest 應紅燈。
- [x] 1.4 [P] 加 `test_imported_skill_remote_error_wrapping`：fake tool 的 `__call__` 丟 `ValueError("kapow")`，assert 呼叫 imported skill 時丟 `RuntimeError` 且訊息含 `"huggingface_remote_error"`，覆蓋 spec scenario「Imported HuggingFace skill wraps invocation errors」與設計決定 `Handshake 失敗的錯誤命名`；驗證：對應 pytest 應紅燈。
- [x] 1.5 [P] 加 `test_import_handshake_failure`：餵 `inputs=None` / `inputs=["bad"]` / `inputs="bad"` 三種錯型，assert 丟 `RuntimeError` 且訊息含 `"huggingface_handshake_failed"`，覆蓋 spec scenario「import_hf_tool raises handshake_failed for unparseable inputs」；驗證：對應 pytest 應紅燈。
- [x] 1.6 [P] 加 `test_import_rejects_non_hf_tool`：餵 `"not a tool"` / `{"name": "fake"}` / `None` / `42`，assert 丟 `TypeError` 且訊息含 `"import_hf_tool expects transformers.Tool"`，覆蓋 spec scenario「import_hf_tool rejects non-Tool input」；驗證：對應 pytest 應紅燈。
- [x] 1.7 刪除 `tests/adapters/test_huggingface.py::test_import_hf_tool_not_exported`（v0.3.3 的防呆 case），驗收條件：`pytest -k "import_hf_tool_not_exported"` 顯示 0 collected，沒有殘留。
- [x] 1.8 修改 `tests/adapters/test_openhands.py::test_import_openhands_action_not_exported` 的 docstring，闡明該行為為「permanent design decision — Action is a declarative event record with no `__call__`」，覆蓋 `expose_as_openhands_action produces an OpenHands Action from a cantus Skill` Requirement 中改寫的 scenario；驗證：執行該 pytest 應綠燈（行為不變、只是 docstring 說明改變），並肉眼檢查 docstring 文字確實提及「permanent」與「declarative event record」。

## 2. 實作 import_hf_tool

- [x] 2.1 在 `libs/cantus/cantus/adapters/huggingface.py` 新增 `_HuggingFaceRemoteSkill(_RemoteSkillBase)` 內部子類別，`__init__(self, *, tool: Tool)` 內呼叫 module-private helper `_derive_args_schema_from_hf_inputs(tool.inputs)` 把 HF dict 轉成 `{"type": "object", "properties": {...}, "required": [<all field names>]}`，並把 `Tool` instance 存到 `self._tool`，落實設計決定 `import_hf_tool` 走 `_RemoteSkillBase` + dict-schema 直譯；驗證：執行 1.1 的 pytest 變綠。
- [x] 2.2 在同檔加 `_derive_args_schema_from_hf_inputs(inputs)` helper：input 非 dict 或任一 entry 非 dict 形狀 → 丟 `RuntimeError("huggingface_handshake_failed: ...")`；正常時回傳 v0.3.0 JSON Schema dict，落實設計決定 `Handshake 失敗的錯誤命名`；驗證：1.5 的 pytest 變綠。
- [x] 2.3 在同檔加 `_HuggingFaceRemoteSkill.run(self, **kwargs)`：HF `run()` 直接呼叫 `tool(**kwargs)`、包成 `RuntimeError("huggingface_remote_error: ...")` 以對齊 LangChain / DSPy 命名；驗證：1.3 與 1.4 的 pytest 變綠。
- [x] 2.4 在同檔加公開 `import_hf_tool(tool: Tool) -> Skill` callable：先做 `isinstance(tool, Tool)` 檢查丟 `TypeError("import_hf_tool expects transformers.Tool")`、再 `return _HuggingFaceRemoteSkill(tool=tool)`，落實 `import_hf_tool wraps HuggingFace transformers Tool as cantus Skill` Requirement 的型別契約；驗證：1.6 的 pytest 變綠 + 在 `__all__` 追加 `"import_hf_tool"`。
- [x] 2.5 改寫 `cantus/adapters/huggingface.py` module-level docstring：移除「intentionally deferred to v0.3.4 batch3」段落，落實 `expose_as_hf_tool produces a HuggingFace transformers Tool from a cantus Skill` Requirement 改寫後對 import 方向不再 deferred 的措辭，改述「v0.3.4 起雙向皆支援」並標明 `_RemoteSkillBase` 為 import 路徑共用底盤；驗證：肉眼檢查 docstring 不再出現「deferred」字樣，且 ruff/pyright 不抱怨。

## 3. 對外 lazy stub 與 OpenHands 文件變更

- [x] 3.1 在 `libs/cantus/cantus/adapters/__init__.py` 加 `import_hf_tool` 的 lazy-load stub（仿 batch2 LangChain/DSPy 寫法），並把 `"import_hf_tool"` 補進 `__all__`，呼應 `import_hf_tool wraps HuggingFace transformers Tool as cantus Skill` Requirement 中對外暴露第七個 callable 的設計；驗證：`python -c "from cantus.adapters import import_hf_tool; print(callable(import_hf_tool))"` 印 `True`，並執行新測試 1.1–1.6 全綠。
- [x] 3.2 改寫 `cantus/adapters/openhands.py` module-level docstring：把「intentionally deferred to v0.3.4 batch3」改成「import direction is permanently not applicable — `openhands.events.Action` is a declarative event record dispatched by host runtime, no `__call__` to delegate `Skill.run` to」，落實 `expose_as_openhands_action produces an OpenHands Action from a cantus Skill` Requirement 改寫後對 OpenHands import 永久 not-applicable 的措辭；驗證：肉眼檢查 docstring 與 spec 措辭一致，並執行 `pytest libs/cantus/tests/adapters/test_openhands.py -v` 仍綠（既有 export 行為不動）。
- [x] 3.3 改寫 `cantus/adapters/__init__.py` module-level docstring：把 batch3 段落由「6 callables + HF/OpenHands import 待 v0.3.4」更新為「7 callables，HF 雙向、OpenHands export-only because Action is non-callable」，落實設計決定 `batch3a 降級：HF only，OpenHands 永久放棄`；驗證：肉眼檢查 docstring 與 `__all__` 列表一致。

## 4. 文件與版本

- [x] 4.1 新增 `libs/cantus/docs/protocols/adapters-batch3.md`：闡述 v0.3.4 收尾，含 4 框架雙向矩陣表（LangChain ✅✅ / DSPy ✅✅ / HuggingFace ✅✅ / OpenHands ✅—）、HF inputs dict → JSON Schema 對應規則、OpenHands import not-applicable 理由（呼應設計決定 `batch3a 降級：HF only，OpenHands 永久放棄`）；驗證：肉眼確認文件包含矩陣表與 not-applicable 理由段落，並透過 markdown lint（若可用）無錯誤。
- [x] 4.2 [P] 在 `libs/cantus/docs/protocols/adapters-batch2.md` 文件開頭加 supersede note：「Superseded for HF / OpenHands import direction by adapters-batch3.md (v0.3.4)」；驗證：肉眼檢查兩份文件 cross-link 一致。
- [x] 4.3 [P] 新增 `libs/cantus/MIGRATION_v0.3.3_to_v0.3.4.md`：說明 ADDITIVE 升級、`import_hf_tool` 用法範例、OpenHands import 永久不做的理由與替代方案（直接用 `expose_as_openhands_action` 把 cantus Skill 註冊給 OpenHands runtime）；驗證：肉眼檢查包含 import_hf_tool 範例與 OpenHands 替代路徑說明。
- [x] 4.4 在 `libs/cantus/CHANGELOG.md` 加 v0.3.4 章節：列出「Added: `import_hf_tool`」、「Changed: spec language for OpenHands import is now permanently not applicable」、「Removed: deferred-to-v0.3.4 wording in HF/OpenHands docstrings」；驗證：肉眼檢查格式與 v0.3.3 章節對齊（Keep a Changelog 風格）。
- [x] 4.5 把 `libs/cantus/pyproject.toml` 的 `version` 由 `0.3.3` 改為 `0.3.4`，並同步 `libs/cantus/cantus/__init__.py` 的 `__version__`；驗證：`python -c "import cantus; print(cantus.__version__)"` 印 `0.3.4`，`grep -n "^version" libs/cantus/pyproject.toml` 印 `0.3.4`。

## 5. 整合驗證

- [x] 5.1 `cd libs/cantus && pytest tests/adapters/ -v` 全綠，特別確認 `test_huggingface.py` / `test_openhands.py` / `test_remote_skill_base.py` / `test_langchain.py` / `test_dspy.py` / `test_mcp_client.py` 都不 regress；驗證：pytest exit code 0。
- [x] 5.2 `cd libs/cantus && pytest -v` 全綠（含非 adapter 測試）；驗證：pytest exit code 0、無 warnings 升級成 errors。
- [x] 5.3 `spectra validate cantus-adapter-layer-batch3 --strict` 通過；驗證：CLI 印 `validation passed` 或同等訊息、exit code 0。
- [x] 5.4 手動 smoke：`python -c "from cantus.adapters import import_hf_tool, expose_as_hf_tool, expose_as_openhands_action, import_langchain_tool, import_dspy_tool; print('seven callables ok')"` 成功印出訊息；驗證：exit code 0。
