## Why

Cantus 主要使用者是中文授課場景的學生與老師（從 README 第 17 行已自陳「The Chinese-speaking LLM community refers to prompt engineering as *詠唱*」即可看出）。目前 `libs/cantus/README.md` 只有英文版，第一次接觸的學生需要同時讀懂英文敘事、英文五協定名詞與安裝步驟，理解成本明顯偏高；中文版 README 可作為英文 README 的對等入口，降低初次評估與安裝的門檻。

## What Changes

- 在 `libs/cantus/` 新增 `README.zhTW.md`，內容以台灣慣用繁體中文撰寫，與 `README.md` 章節結構一一對應（hero banner、badge bar、Open in Colab、Install、30-second Quickstart、protocols banner、五協定一句話介紹、Documentation、License）。
- 在 `libs/cantus/README.md` 的開頭區塊（hero banner 之後、badge bar 區域內或正下方）加入指向 `README.zhTW.md` 的純文字語言切換連結（顯示為「繁體中文」），讓英文讀者可從 GitHub web rendering 直接切換到中文版。
- 在 `libs/cantus/README.zhTW.md` 也回放一條指向 `README.md` 的「English」連結，形成雙向對等切換。
- 中文版的 hero banner、protocols banner 影像路徑與英文版相同（`assets/banner_hero.jpeg`、`assets/banner_protocols.jpeg`），Open in Colab CTA 指向同一個 `<current-tag>` 對應的 task_template notebook URL。
- 中文版的 Install、Quickstart 程式區塊與英文版的指令文字逐字相同（pip 指令、Python import、變數名都不翻譯），只翻譯說明文字，避免出現指令分歧。

## Non-Goals (optional)

- 本變更不翻譯 `libs/cantus/docs/` 下任何 API 文件、cookbook 或 protocols 個別頁面 — 中文化 docs 是後續另案。
- 本變更不翻譯 `libs/cantus/notebooks/` 內的 notebook 內容、cell markdown 或 NotebookLM 來源檔。
- 本變更不引入任何 i18n 工具鏈、locale 設定檔或 README 自動產生機制；中文版以純手寫單檔形式存在。
- 本變更不更動 `README.md` 既有英文敘事內容、章節順序、badge URL 或 banner 影像路徑；唯一新增僅為「繁體中文」語言切換連結。
- 本變更不新增除 `README.zhTW.md` 之外的語言變體（簡體中文、日文、韓文等不在此案範圍）。

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `cantus-distribution`: 在既有「Cantus README presents hero banner, badge bar, and Open-in-Colab call-to-action」之外新增一項 Requirement，規範繁體中文 README 變體（`README.zhTW.md`）的存在、章節對等與雙向語言切換連結契約。

## Impact

- Affected specs: `cantus-distribution`（新增一條 README zhTW Requirement）
- Affected code:
  - New: libs/cantus/README.zhTW.md
  - Modified: libs/cantus/README.md
