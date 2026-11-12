# 協作流程文件導覽

第一次使用，先讀[協作指南](../guide.md)，了解如何啟動工作、使用 skills 與交接。這些文件來自 harness-agile 範本，規範開發助理的協作流程；產品文件的導覽在 [docs/README.md](../README.md)。

## 依工作找文件

| 你遇到的問題 | 文件 |
| --- | --- |
| 開發助理需要遵守哪些共用規則？ | [AGENTS.md](../../AGENTS.md) |
| 從需求到交付，每一步何時可以往下走？ | [交付流程](workflow.md) |
| Spec 與 tickets 放哪裡？狀態怎麼判定？ | [Issue tracker](issue-tracker.md) |
| 四軸 review 與安全審查如何進行？ | [審查規則](review.md) |
| Claude Code 與 Codex 如何共用 skills、交接？ | [Runtime adapters](runtime.md) |
| Claude 各角色用哪個模型？何時委派？ | [Claude 模型分工](claude-orchestration.md) |
| Codex 如何區分 prompt、skill 與宿主能力？ | [Codex 執行指引](codex.md) |
| 哪些文件用英文？中英文規格如何同步？ | [語言規則](language.md) |
| 探索程式碼前，如何閱讀領域模型？ | [領域文件指引](domain.md) |
| 如何顯式檢查文件與實作的差異？ | [文件漂移診斷契約](drift-report.md) |

本資料夾內的英文文件供開發助理執行流程，也可用來查核工作是否符合規範。面向使用者的說明採台灣繁體中文。

## 設計決策

ADR 保存已採用的決策與理由，方便後續修改時判斷影響。

- [ADR-0005](../adr/0005-walking-skeleton-then-epic-loop.md)：先建立 walking skeleton，再以 epic 交付。
- [ADR-0006](../adr/0006-ticket-status-in-frontmatter.md)：ticket 狀態存於 frontmatter。
- [ADR-0007](../adr/0007-adversarial-review-fixed-axes-two-rounds.md)：規格審查使用固定四軸，最多兩輪。
- [ADR-0008](../adr/0008-fresh-context-spec-review.md)：每軸、每輪使用全新對話；缺少獨立上下文時，規格審查 gate 維持未完成。
- [ADR-0009](../adr/0009-drift-diagnosis-native-host-verification.md)：文件漂移診斷以原生宿主與實際報告／檔案邊界驗證，分開回報結構檢查與模型行為。

cantus 導入 harness-agile 時新增的決策：

- [ADR-0010](../adr/0010-existing-codebase-satisfies-round-zero.md)：既有的 v0.6.0 程式碼視同 round 0 已完成，不另建 walking skeleton。
- [ADR-0011](../adr/0011-remove-spectra-and-openspec.md)：移除 Spectra 與 openspec；舊契約保存在 tag `pre-harness-migration`。
- [ADR-0012](../adr/0012-lightweight-path.md)：不改執行行為、也不動公開 API 的變更走輕量路徑；workflow、依賴與 guard 的變更仍要做 security review。
- [ADR-0013](../adr/0013-release-gate.md)：發版前的 release gate（人工把關）。
- [ADR-0014](../adr/0014-commit-and-landing-authority.md)：agent 可以在 ticket branch 上 commit，合併進 main 每次都要使用者核准（人工把關）。

cantus 原有的 ADR-0001～0004 屬於產品決策，見 [ADR 目錄](../adr/)。2026-11-12 新增三份產品架構決策（目前都是 proposed）：

- [ADR-0015](../adr/0015-seams-with-mainstream-defaults.md)：harness 行為透過 seam 擴充，每個 seam 都附一個對齊主流做法的預設實作；並定下生命週期事件清單。
- [ADR-0016](../adr/0016-async-core-with-sync-run-wrapper.md)：agent 核心改成 async，同步的 `run()` 交給單一常駐背景 loop 執行，不依賴 nest_asyncio。
- [ADR-0017](../adr/0017-rename-skill-to-tool.md)：可呼叫的 Skill 分兩階段改名為 Tool，把 Skill 這個名字留給 Agent Skill。
