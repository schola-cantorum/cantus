<!--
Behavior + verification convention:
- 每個 task 描述「完成後可觀察到什麼」與「用什麼動作驗證完成」
- 檔案路徑為 locator context，不能單獨作為 task
- TDD 順序：先建立 smoke harness 與基線（pre-marker 觀察值），再改 pyproject、再過綠燈
- `parallel_tasks: true`（per `.spectra.yaml`）：互不依賴、touch 不同檔案的 task 標 `[P]`
- 2026-05-21 重新核對 bnb wheel 狀態：bnb 0.49.x 有 `macosx_14_0_arm64` 與 `win_amd64` wheel；
  macOS arm64 / Windows 上 install 不會 abort，但 CUDA 量化 kernel 在這兩平台 runtime non-functional。
  marker 的目的是「刪掉非 Linux 上沒用的 native dependency」而非「修 install resolve」（除 macOS Intel 外）。
-->

## 1. Smoke harness baseline（落實 Requirement「Distribution SHALL ship a tri-platform install smoke matrix」、先寫測試 / 抓失敗）

- [x] 1.1 [P] 為「Distribution SHALL ship a tri-platform install smoke matrix」提供本機可重現的腳本：`scripts/smoke_install.sh` 在 Linux / macOS / Windows（via Git Bash 或 WSL）都跑得動，步驟為 `uv pip install --system cantus-agent`、`python -c "from cantus import skill, Agent, load_chat_model"`、`uv pip install --system cantus-agent[serve,openai]`；script 接受 optional `${1}` 為 cantus 版本，任一 step 非零即 exit 1；驗證：在開發者 macOS 上跑 `bash scripts/smoke_install.sh` 觀察 exit code 0
- [x] 1.2 [P] 為「Distribution SHALL ship a tri-platform install smoke matrix」建立 GitHub Actions matrix workflow `.github/workflows/cross-platform-install.yml`（`ubuntu-latest` / `macos-latest` / `windows-latest`），步驟對齊 1.1 的 sequence，trigger 為 push 到 `main` 與 release tag `v*.*.*`；驗證：開 PR 後 workflow 出現在 GitHub Actions 列表並在 main merge 後跑出三條 OS job
- [x] 1.3 在 marker 改動之前先跑一輪 CI 並錄下三 OS pre-marker baseline：`macos-latest` (arm64) 與 `windows-latest` job 上 `uv pip install --system .[runtime]` 會成功，`uv pip list | grep -i bitsandbytes` 應命中 `bitsandbytes` 0.49.x（這是 marker 要消去的非可用依賴）；`ubuntu-latest` 同樣命中 `bitsandbytes`（marker 後仍應命中，作為 backward compat baseline）；驗證：在 PR 描述列出三 OS pre-marker run URL 與每 job log 中 `bitsandbytes` 那一行，作為 task 2.2 的 before/after 對照（marker 後 macOS / Windows 不應再命中、Linux 仍命中）

## 2. PEP 508 marker 改動（落實 Requirement「pyproject runtime extras SHALL gate Linux-only native packages behind sys_platform markers」、呼應 Decisions「用 PEP 508 marker 而非分拆 extras」與「Marker 用 `sys_platform` 而非 `platform_system`」與「用 `sys_platform == 'linux'` 即可，不細分 macOS arm64 / Intel / Windows GPU 條件」與「Spec delta 用 ADDED 兩個新 Requirements，不 MODIFY 既有 Requirement」）

- [x] 2.1 落實 Requirement「pyproject runtime extras SHALL gate Linux-only native packages behind sys_platform markers」：在 `pyproject.toml` 的 `[project.optional-dependencies].runtime` 區段，把 `bitsandbytes>=0.43.0` 改為 `bitsandbytes>=0.43.0; sys_platform == 'linux'`；不改其他 runtime 條目；不改 `[tool.uv].conflicts` 區段；驗證：`grep -F "bitsandbytes>=0.43.0; sys_platform == 'linux'" pyproject.toml` 命中且既有 openhands marker 風格被保留
- [x] 2.2 為「pyproject runtime extras SHALL gate Linux-only native packages behind sys_platform markers」三個 Scenario 提供綠燈：`uv pip install cantus-agent[runtime]` 在 macOS 與 Windows 上 exit 0 且 resolved set 不含 `bitsandbytes`、Linux 上 resolved set 仍含 `bitsandbytes>=0.43.0`；驗證：三 OS CI matrix（1.2 的 workflow）全綠並在每個 job log 加一行 `uv pip list | grep -i bitsandbytes` assert

## 3. quickstart-desktop docs 落地（落實 Requirement「Cross-platform desktop quickstart doc SHALL classify as Required English canonical with Optional zh-TW companion」、呼應 Decision「`quickstart-desktop.md` 為 Required English canonical（zh-TW 列 Optional）」）

- [x] 3.1 [P] 為「Cross-platform desktop quickstart doc SHALL classify as Required English canonical with Optional zh-TW companion」寫主文 `docs/quickstart-desktop.md`：5 分鐘從零到 first `Agent.run(...)` 的 walkthrough、開頭 `uv pip install cantus-agent`、API key 路徑（建議 `load_chat_model("openai/gpt-4o-mini")`）、明白標示 4-bit local Gemma 為 Linux + CUDA 路徑、本機 LLM 在 macOS / Windows 等 A1（Ollama bridge）ship、最後 link 回 `docs/quickstart.md`（Colab 路徑）；文件 English-only；驗證：人工 review 五 cell sequence 可在 Mac mini 上純手動跑通
- [x] 3.2 [P] 在 `README.md` 與 `README.zhTW.md` 的 Install 與 30-second Quickstart 之間插入「Desktop（Win / macOS / Linux）」段落，內含一行指向 `docs/quickstart-desktop.md` 的連結；既有 Colab 範例與 30-second Quickstart 文字維持不變；驗證：`git diff README.md README.zhTW.md` 只見新增段落、無刪除既有 Colab 內容
- [x] 3.3 [P] 在 `docs/quickstart.md` 頂部加一行「Desktop 使用者請改讀 `docs/quickstart-desktop.md`」連結，保留其餘 Colab 內容；驗證：`git diff docs/quickstart.md` 只見新增該行
- [x] 3.4 [P] **附加**至既有 `MIGRATION_v0.4.2_to_v0.4.3.md`（既有檔案已存在、目前說明 Spectra spec self-hosting；不要覆蓋既有內容）一段「Cross-platform runtime extras 行為變更」，列出：(a)「macOS Intel：install 從 abort 轉為成功（resolved set 不含 bnb）」、(b)「macOS arm64 / Windows：install 仍成功，但 resolved set 從含 `bitsandbytes` 0.49.x 變為不含，呼應 bnb 在 non-CUDA 環境 runtime non-functional 的事實」、(c)「Linux 行為與 v0.4.2 byte-identical」、(d)「macOS / Windows 學生改用 API key path（呼應「Cross-platform desktop quickstart doc SHALL classify as Required English canonical with Optional zh-TW companion」的 API key path 設計）」；驗證：手動 review 涵蓋 Risks / Trade-offs 段提到的三項風險回應、新增段落以 `## ` heading 起始且未動到既有 spec self-hosting 區段的文字

## 4. Spec contract 覆蓋驗證（落實 ADDED Requirements 全部 Scenario 都被 1.x ~ 3.x 覆蓋）

- [x] 4.1 確認「pyproject runtime extras SHALL gate Linux-only native packages behind sys_platform markers」與「Distribution SHALL ship a tri-platform install smoke matrix」與「Cross-platform desktop quickstart doc SHALL classify as Required English canonical with Optional zh-TW companion」三個 ADDED Requirements 的 Scenario 全部由 1.x / 2.x / 3.x task 的驗證動作覆蓋；驗證：在 PR 描述列出 Scenario 對 CI job log / 本機 smoke run / 文件 review 的對應
- [x] 4.2 `spectra analyze cantus-uv-cross-platform-install --json` 無 Critical / Warning finding；驗證：CLI 輸出 `findings: []` 或 severity 全為 Suggestion

## 5. 收尾驗證（不是 audit gate；audit 在 Gate A 階段跑）

- [x] 5.1 三 OS CI matrix（1.2 的 workflow）在 PR branch push 後跑綠；驗證：PR 頁面顯示 `cross-platform-install / ubuntu-latest`、`cross-platform-install / macos-latest`、`cross-platform-install / windows-latest` 三個 check 皆通過
- [x] 5.2 `spectra validate cantus-uv-cross-platform-install` 通過；驗證：CLI 輸出無 error
- [x] 5.3 在 PR 描述列出對應 Gate A（A 系列三件全 ship 後跑）的驗收項目，方便日後 `/spectra-audit` 與 `/humane-prose-audit` 一次性 review；驗證：PR description 含「Gate A 必過：spectra-audit + humane-prose-audit（對 quickstart-desktop / MIGRATION）」段
