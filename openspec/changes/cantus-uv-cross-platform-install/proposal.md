## Why

cantus 在 v0.4.2 之後要走向「上線教學就緒」，學生筆電 OS 含 Win / macOS / Linux 三者。`cantus[runtime]` extras 中的 `bitsandbytes>=0.43.0` 是 4-bit 量化路徑的核心依賴，它在三 OS 上的實際處境（2026-05-21 重新核對 PyPI 上的 wheel 與 runtime 行為）如下：

- **Linux x86_64 / aarch64**：bnb 0.43.0 起 first-class wheel + CUDA backend；cantus 教學 baseline 一直以此為主場景
- **macOS arm64（Apple Silicon, macOS ≥14.0）**：bnb 0.49.0 起**有** `macosx_14_0_arm64` wheel，`uv pip install` 解析成功、`import bitsandbytes` 不爆；**但** bnb 的量化 kernel 只有 CUDA backend，Apple Silicon 沒有 CUDA → 即使 wheel 裝得起來，`bnb.nn.Linear4bit` 等型別在 runtime 是 non-functional
- **macOS x86_64（Intel）**：bnb 各版本皆**無**對應 wheel；`uv pip install cantus-agent[runtime]` 解析失敗 → install abort
- **Windows x86_64**：bnb 0.43.0 起官方 `win_amd64` wheel 已 ship（不再需要 community fork）；`uv pip install` 解析成功；runtime 上需要 CUDA-capable GPU 才能跑量化，學生筆電多為 integrated GPU 或 no GPU，實際非可用

換句話說，比 v0.4.2 提案時點更精確的事實是：`cantus[runtime]` 在 macOS arm64 / Windows 上**「裝得起來，但 4-bit 量化路徑在這兩個 OS 都是 non-functional」**；在 macOS Intel 上仍是「裝不起來」。三 OS 都不是 cantus 4-bit Gemma 教學的可用環境。當前 pyproject 把 bnb 無 marker 地拉進 runtime extras，會讓 macOS arm64 / Windows 學生多裝一個 ~50 MB 的 native package 而毫無實益，並且在 macOS Intel 直接 abort install。

同時 `README.zhTW.md` 第一段範例仍是 `mount_drive_and_load()`（Colab-only），桌面學生第一步就踩雷。`pyproject.toml` 已宣告 `[tool.uv]` conflicts 但沒有 platform marker 把 bnb 限制到 Linux，學生用 uv 跨平台安裝會（在 macOS Intel）失敗或（在 macOS arm64 / Windows）拉進非可用依賴。

這件 change 是 A 系列跨平台桌面 runtime 的起點，最小可裝、純 packaging + docs，不引入新 dependency。本身不解決「macOS 學生怎麼跑本機 LLM」（那是後續 A1 `cantus-local-llm-ollama-bridge` 負責）——A0 只負責讓 `cantus-agent[runtime]` 在三 OS 都能**乾淨 resolve 完成**（不論是否包含 bnb）、import 不爆，然後把 quickstart 第一頁改成「API key path 跨平台共用」的乾淨入口。

## What Changes

- `pyproject.toml` 的 `[project.optional-dependencies].runtime` extras：在 `bitsandbytes>=0.43.0` 上加 `; sys_platform == 'linux'` marker，使其僅在 Linux 拉入；macOS / Windows 安裝 `cantus-agent[runtime]` 時 extras 解析成功且不要求 bnb wheel
- `pyproject.toml` 的 `[tool.uv].conflicts` 不變（既有衝突宣告與 marker 加入正交）
- 新增 `docs/quickstart-desktop.md`：以 `uv pip install cantus-agent` + API key path（`load_chat_model("openai/gpt-4o-mini")` 為主範例）作為三 OS 共用 5 分鐘入門；明白標示 4-bit local Gemma 為 Linux + CUDA 路徑、Colab 為另一條路徑、本機 LLM（含 macOS / Windows）等 A1 的 Ollama bridge ship 後再開
- `docs/quickstart.md` 與 `README.md` / `README.zhTW.md` 的 Quickstart 段落：在「Install」與「30-second Quickstart」之間加入指向 `docs/quickstart-desktop.md` 的桌面學生 entry，**不**改 Colab 既有範例（保留 backward compat）
- 新增 CI smoke job（或腳本 `scripts/smoke_install.sh`）：在 Linux / macOS / Windows runners 各跑一次 `uv pip install cantus-agent` 純包驗證 + `python -c "from cantus import skill, Agent, load_chat_model"` import smoke。**不**測 `cantus-agent[runtime]` 在 macOS（已知 bnb 不可裝）；測 `cantus-agent` 純包與 `cantus-agent[serve]`、`cantus-agent[openai]` 等跨平台 extras
- `MIGRATION_v0.4.2_to_v0.4.3.md`：說明 `cantus-agent[runtime]` 在 macOS / Windows 行為變更（bnb 不再拉入，4-bit 量化路徑改為 Linux-only）

**BREAKING**：macOS / Windows 上 `cantus-agent[runtime]` 安裝後不再包含 `bitsandbytes`。對學生使用者實際的觀察結果分三層：

- **macOS Intel**：先前 install abort，現在 install 成功（resolved set 不含 bnb）——**改善**
- **macOS arm64 / Windows**：先前 install 成功且會帶進 bnb wheel（即便 runtime 上 CUDA 量化路徑無作用），現在 resolved set 不含 bnb——**移除了一個非可用的依賴**，但對曾把 bnb 當「workspace 內可 import 的型別 stub」使用的下游程式碼是 breaking
- **Linux**：行為與 v0.4.2 byte-identical（bnb 仍會拉入）

`LocalEnvironment.prepare_model(...)` 在 macOS / Windows 觸發 `_load_with_quant_config` 時若無 bnb，仍會在 import 階段拋 `RuntimeError`（既有行為，未來 A1 接管錯誤訊息指引到 Ollama bridge）。

## Non-Goals

- **不**修 `LocalEnvironment` 本身的 macOS / Windows 跑得動性——這是 A1 `cantus-local-llm-ollama-bridge` 的工作
- **不**引入 Ollama / MLX / 任何新 model backend——A0 純 packaging + docs
- **不**移除既有 `bitsandbytes` 依賴在 Linux 上的 default 行為（保留 backward compat）
- **不**改 PyPI 套件名、版號規則、license（沿用 cantus-distribution 既定 Requirement）
- **不**改 `[tool.uv].conflicts` 內容（既有 openhands ↔ google/openai 衝突宣告維持）
- **不**新增 zh-TW 翻譯到 `docs/quickstart-desktop.md`（依 cantus-i18n-docs 分類，列為 Optional zh-TW companion，先英文）

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `cantus-distribution`：新增 Requirement「`pyproject runtime extras SHALL gate bitsandbytes behind a Linux-only platform marker`」；新增 Requirement「`pyproject SHALL ship a tri-platform install smoke matrix (Linux / macOS / Windows)`」
- `cantus-i18n-docs`：在「Required English canonical」layer 新增 `docs/quickstart-desktop.md` 條目；明確記 `docs/quickstart-desktop.zhTW.md` 為 Optional zh-TW companion（A0 不附）

## Impact

- Affected specs：`cantus-distribution`、`cantus-i18n-docs`（兩者皆 modified，需各補 delta spec）
- Affected code：
  - Modified：`pyproject.toml`、`docs/quickstart.md`、`README.md`、`README.zhTW.md`
  - New：`docs/quickstart-desktop.md`、`scripts/smoke_install.sh`、`MIGRATION_v0.4.2_to_v0.4.3.md`、`.github/workflows/cross-platform-install.yml`（或併入既有 CI workflow）
  - Removed：（無）
- Dependencies：不新增任何 third-party package
- Supply chain：bnb 改為 Linux-only marker 縮小 macOS / Windows 安裝表面，無新攻擊面
- 下游 PyPI consumer：`pip install cantus-agent[runtime]` 在 macOS arm64 / Windows 從「裝得起來、bnb 含在 resolved set 但 4-bit kernel 無 CUDA backend 可用」改為「裝得起來、resolved set 不含 bnb、4-bit 路徑變成顯式 `RuntimeError`（既有訊息），A1 ship 後再改寫指引到 Ollama bridge」；macOS Intel 從「install abort」改為「install 成功且 resolved set 不含 bnb」
