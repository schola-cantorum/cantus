## 1. 純函式 helpers（先落地，解鎖後續）

- [x] 1.1 [P] 以 TDD 新增四個純函式 helper（`active_skill_names` / `format_dataflow` / `format_replay` / `format_inspector_header`）與 `NO_DATAFLOW_TEXT` 常數於 widgets 模組，對應決策「Active Skills 由 sessions 在 client 端推導」與「Dataflow 以 pure helper 文字鄰接呈現」。行為：`active_skill_names` 取 `status=="running"` 且 `source` 以 `skill:` 開頭者解析技能名、其餘來源略過不爆；`format_dataflow` 依 source 分組鄰接、孤立節點仍印標頭、空圖回 `NO_DATAFLOW_TEXT`；`format_replay` 依序印未截斷 summary；`format_inspector_header` 產生精簡 run 標頭。驗證：各 helper 單元測試全綠（含 active 推導 example、空 dataflow、孤立節點）。

## 2. 分頁式 shell

- [x] 2.1 撰寫分頁 shell 的 `textual.pilot.Pilot` 測試，對應需求「TUI renders a tabbed dashboard shell」：斷言 App 組出 `TabbedContent` 含 Dashboard / Skills / Permissions / Dataflow / Inspector 五個 `TabPane`，數字鍵 1-5 切換 `TabbedContent.active`。驗證：新測試先紅。
- [x] 2.2 實作分頁式 shell，對應決策「分頁式 shell（TabbedContent）取代單畫面版面」：`compose()` 改 `TabbedContent`、加 1-5 `BINDINGS` 與 `action_tab`，把 Sessions / Queue / Health 移入 Dashboard `TabPane`，移除原本「TUI renders a four-pane dashboard」的單畫面版面並清理 `#events` CSS。行為：啟動後五分頁可用、數字鍵切換、Dashboard 顯示三 pane、既有 r / p / q 仍作用。驗證：2.1 測試轉綠。

## 3. Skills 分頁

- [x] 3.1 撰寫 `SkillsPane` 的 Pilot 測試，對應需求「Skills tab lists registered skills and marks active runs」：斷言列出註冊技能 name / description，且有 running session 的技能標 active。驗證：新測試先紅。
- [x] 3.2 實作 `SkillsPane`（`DataTable`、`cursor_type="none"`）並在 `_fetch` 接 `snapshot.skills` + `active_skill_names(sessions)`，落實決策「Active Skills 由 sessions 在 client 端推導」。行為：Skills 分頁顯示技能列與 active 標記，且僅在 `snap.ok and snap.data is not None` 時 repaint。驗證：3.1 測試轉綠。

## 4. Permissions 分頁

- [x] 4.1 撰寫 `PermissionsPane` 的 Pilot 測試，對應需求「Permissions tab summarizes the auth posture」：斷言顯示 `auth_mode`、兩個 requires_auth 旗標、`gated_routes`，且 render body 不含 token-like 值、只含已知 keys。驗證：新測試先紅。
- [x] 4.2 實作 `PermissionsPane`（`Static`）並接 `snapshot.permissions`。行為：Permissions 分頁顯示 auth posture、永不顯示 token，且僅在有 snapshot 時 repaint。驗證：4.1 測試轉綠（含不洩 token 正向斷言）。

## 5. Dataflow 分頁

- [x] 5.1 撰寫 `DataflowPane` 的 Pilot 測試，對應需求「Dataflow tab renders the component topology」：斷言以文字鄰接呈現 nodes / edges、空圖顯示 placeholder。驗證：新測試先紅。
- [x] 5.2 實作 `DataflowPane`（`Static` + `format_dataflow`）並接 `snapshot.dataflow`，落實決策「Dataflow 以 pure helper 文字鄰接呈現」。行為：Dataflow 分頁顯示拓樸鄰接清單，且僅在有 snapshot 時 repaint。驗證：5.1 測試轉綠。

## 6. Inspector 分頁

- [x] 6.1 撰寫 `InspectorPane` 的 Pilot 測試，對應需求「Inspector tab presents the selected run's workflow trace」：斷言顯示所選 run 的完整時間軸 trace + run 標頭、無選取或無 trace 顯示 placeholder、選取跟隨 Dashboard Sessions。驗證：新測試先紅。
- [x] 6.2 實作 `InspectorPane`，落實決策「Inspector 分頁整併 Events drill-down，不做假展開」與「跨分頁選取沿用單一 Sessions cursor 與精簡 run 標頭」：把原「Events pane drills down into the selected session」的 `EventsPane.show_workflow` 邏輯吸收成 `InspectorPane`（run 標頭 + `format_replay`），`_refresh_events` 改名 `_refresh_inspector`，移除 `EventsPane`，Sessions 綁 `enter` 跳 Inspector。行為：選取 run 後 Inspector 顯示完整 trace 與標頭。驗證：6.1 測試轉綠。

## 7. 整合與回歸

- [x] 7.1 整合與回歸掃描，涵蓋需求「TUI degrades gracefully when the server is unreachable」並維持決策「維持純 UI，不更動 introspection 後端」：斷言 outage 時 Skills / Permissions / Dataflow 分頁保留前次內容不空白不崩潰、pause 在非 Dashboard 分頁仍生效；確認 `cantus/tui/client.py` 與後端零變更；更新因重構而刻意失效的 four-pane / `EventsPane` 既有測試。驗證：`uv run pytest tests/tui/ tests/serve/` 全綠、既有 10 條 requirement 不回歸、`uv run mypy cantus/` 與 `uv run ruff check` delta 為 0、real-server smoke 確認 skills/permissions/dataflow 三 slice 有料且 Inspector trace 正確。
