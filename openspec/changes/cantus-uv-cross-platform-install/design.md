## Context

`cantus-distribution` 已 ship PyPI 套件名 `cantus-agent`、`requires-python = ">=3.10"`、`[tool.uv].conflicts` 三組 extras 衝突宣告（v0.4.0 加入），但**沒有**任何 OS-specific marker。`cantus-agent[runtime]` extras 包含 `bitsandbytes>=0.43.0`，這個套件在 2026-05-21 重新核對的 wheel + runtime 狀態如下：

- **Linux x86_64 / aarch64 + CUDA**：first-class wheel + working CUDA backend，cantus 4-bit Gemma 教學 baseline
- **macOS arm64（Apple Silicon, macOS ≥14.0）**：bnb 0.49.0 起**有** `macosx_14_0_arm64` wheel，`uv pip install` 解析成功、`import bitsandbytes` 不爆；但量化 kernel 只有 CUDA backend，Apple Silicon 無 CUDA → `bnb.nn.Linear4bit` 等型別在 runtime 是 non-functional
- **macOS x86_64（Intel）**：bnb 各版本皆**無**對應 wheel；`uv pip install cantus-agent[runtime]` 解析失敗 → install abort
- **Windows x86_64**：bnb 0.43.0 起官方 `win_amd64` wheel 已 ship（不再需要 community fork）；解析成功；runtime 需 CUDA-capable GPU，學生筆電多無此條件

結論：`cantus[runtime]` 在 macOS arm64 / Windows 上「即使裝得起來，4-bit 量化路徑也是 non-functional」；只有 macOS Intel 是純粹的 install-time 失敗。把 bnb 限制到 Linux 不是「修 install resolve」而是「**刪掉非 Linux 上沒用的 native dependency**」，順便讓 macOS Intel 的 install 解析成功。

過去 v0.1.x ~ v0.4.2 假設 Colab 為主場景，所有 runtime 跑在 Linux GPU runtime；現在使用者 fhsh.tp.edu.tw 的教學情境（見 `/Users/phoenix/.claude/projects/-Users-phoenix-dev-edu-projects-cantus/memory/project_teaching_context.md`）要求三 OS 都能 install，且 uv 必須可用。

`docs/quickstart.md` 與 `README.zhTW.md` 第一個範例仍是 `mount_drive_and_load()`（Colab-only），桌面學生第一次接觸 framework 會直接踩雷。Stakeholder：

- **教學使用者（fhsh.tp.edu.tw）**：要求三 OS install 不踩雷、uv 可用、API key path 為跨平台共用入口
- **既有 Linux + GPU 教學使用者**：不能因為這次 change 而改變 `cantus-agent[runtime]` 在 Linux 的安裝行為（backward compat）
- **PyPI 下游使用者**：透過 `pip install cantus-agent` 期待 PEP 508 標準 marker 解析

## Goals / Non-Goals

**Goals：**

1. `uv pip install cantus-agent` 在 macOS / Windows / Linux 三 OS 全部 `exit 0`
2. `uv pip install cantus-agent[runtime]` 在 macOS / Windows 不嘗試解析 bnb wheel，仍 `exit 0`
3. `python -c "from cantus import skill, Agent, load_chat_model"` 在三 OS 都不爆 `ImportError`
4. 新增 `docs/quickstart-desktop.md` 作為桌面學生 5 分鐘共用入口；Colab path 維持不變
5. `cantus-agent[runtime]` 在 Linux 行為與 v0.4.2 完全相同（bitsandbytes 仍會拉入）
6. CI 在每次 push 到 `main` 與 release tag 跑三 OS install smoke

**Non-Goals：**（與 proposal Non-Goals 一致，此處不重複）

## Decisions

### 用 PEP 508 marker 而非分拆 extras

選 `bitsandbytes>=0.43.0; sys_platform == 'linux'` 而非把 `runtime` 拆成 `runtime-linux` / `runtime-mac` / `runtime-windows` 三個 extras。

**理由：**

- 既有 `cantus-agent[runtime]` 已被 zh-TW README 多處引用（v0.1.4 起），改 extras 名是 SemVer breaking；marker 只縮小該 extras 在 macOS / Windows 上的依賴集，不破壞名稱契約
- pyproject 已有 marker 慣例：`openhands>=1.16,<2; python_version >= '3.12' and python_version < '3.13'`（`pyproject.toml` runtime extras 鄰近區塊）——marker 風格一致
- uv 與 pip 都支援 PEP 508 marker；無需 uv-only 特性

**Alternative 考慮：** 分拆三個 extras。**否決理由：** 增加學生記憶負擔（要記 `runtime-mac` vs `runtime`），且 macOS / Windows 上的 `runtime-*` extras 內容子集——zero 個套件——是空 extras，意義不大。

### 用 `sys_platform == 'linux'` 即可，不細分 macOS arm64 / Intel / Windows GPU 條件

雖然 bnb 在 macOS arm64 與 Windows 上有 wheel，但其 4-bit 量化 kernel 只有 CUDA backend。cantus 4-bit Gemma 教學路徑等於 Linux + CUDA。把 marker 限制到 `sys_platform == 'linux'` 是把「實際可用」與「extras resolve 結果」對齊的最簡單方式。

**理由：**

- PEP 508 沒有「is CUDA available」marker；用 `sys_platform == 'linux'` 是「Linux 為 cantus 4-bit 量化的唯一支援平台」的契約宣告
- 若改成更精細的 `sys_platform == 'linux' or (sys_platform == 'darwin' and platform_machine == 'arm64')`，會把 bnb 拉進 Apple Silicon——但其 runtime non-functional 不變，徒增 50 MB 依賴
- Linux 內若沒有 CUDA（如 CPU-only Linux runner），bnb 一樣可以裝得起來但無作用——這條 marker 不解決該層級的問題，但和 v0.4.2 行為一致，**不**做新增約束（Out of scope，留給後續 change）

**Alternative 考慮：** 用 `extra == 'cuda'` 或環境變數 gate。**否決理由：** PEP 508 marker 規格無此選項；後續若需要可在 `cantus-agent[runtime-cuda]` 等新 extras 處理（A0 不開）。

### Marker 用 `sys_platform` 而非 `platform_system`

選 `sys_platform == 'linux'` 而非 `platform_system == 'Linux'`。

**理由：** 兩者 PEP 508 都支援；`sys_platform` 字串短、慣用、與 Python `sys.platform` 一致（小寫 `linux` / `darwin` / `win32`）。pyproject 既有 marker 走 `python_version` 形式，OS 平台則無前例；採 `sys_platform` 與 setuptools 文件對齊。

### Spec delta 用 ADDED 兩個新 Requirements，不 MODIFY 既有 Requirement

`cantus-distribution` 已有的 install / extras 既存 Requirements（含「Cantus framework is distributed as standalone GitHub repo」、「Distribution extras matrix exposes ... groups」）涵蓋目前 extras 命名與 `[tool.uv].conflicts`；A0 的 marker 約束與 CI smoke matrix 屬於新規範，與既有 Requirement 條文沒有直接覆蓋衝突。因此 spec delta 採 ADDED 兩個新 Requirements——「pyproject runtime extras SHALL gate Linux-only native packages behind sys_platform markers」與「Distribution SHALL ship a tri-platform install smoke matrix」——而非 MODIFY 既有 Requirement。

**理由：** ADDED 比 MODIFY 在 archive 階段對既有 spec 衝擊小，避免無謂改寫既有 Scenario；兩個新 Requirements 各自獨立，後續若要再加（例如 `cantus-agent[memory]` 也加 marker）也只需追加 Scenario。

### `quickstart-desktop.md` 為 Required English canonical（zh-TW 列 Optional）

`cantus-i18n-docs` 四層分類中，把 `docs/quickstart-desktop.md` 列為 Required English canonical（與 `docs/quickstart.md` 同層）；zh-TW companion `docs/quickstart-desktop.zhTW.md` 列 Optional，A0 不附。

**理由：** quickstart 文件是 PyPI long-description 參照面，英文 canonical 是硬需求；zh-TW 由教學使用者後續手動補（未來改 change），不阻塞 A0 ship。

## Implementation Contract

**Behavior（A0 ship 後三 OS 各自可觀察到）：**

- Linux x86_64 / aarch64：`uv pip install cantus-agent[runtime]` 結果與 v0.4.2 byte-identical，含 `bitsandbytes`、`torch`、`transformers`、`accelerate`、`outlines`
- macOS arm64（Apple Silicon, macOS ≥14.0）：`uv pip install cantus-agent[runtime]` 成功，resolved set **不**含 `bitsandbytes`；拉入 `torch`、`transformers`、`accelerate`、`outlines`。先前 v0.4.2 在此平台會把 bnb 0.49.x 拉進來（runtime non-functional），v0.4.3 移除
- macOS Intel（x86_64）：`uv pip install cantus-agent[runtime]` 從 v0.4.2 的 install abort 轉為**成功**，resolved set 不含 bnb；其他套件同 macOS arm64
- Windows x86_64：`uv pip install cantus-agent[runtime]` 成功，resolved set **不**含 `bitsandbytes`。先前 v0.4.2 在此平台會把 bnb 0.49.x 拉進來（runtime 多無 CUDA 可用），v0.4.3 移除
- 三 OS：`uv pip install cantus-agent`（無 extras）安裝行為一致，僅核心 `pydantic>=2.0`
- 三 OS：`uv pip install cantus-agent[serve,openai]` 全部 `exit 0`
- 三 OS：`python -c "from cantus import skill, Agent, load_chat_model"` 全部 `exit 0`

**Interface / 資料形狀：**

- `pyproject.toml` 的 `[project.optional-dependencies].runtime` 區段內 `bitsandbytes` 條目附加 PEP 508 marker `; sys_platform == 'linux'`
- 其他 runtime extras 條目（transformers / torch / accelerate / outlines）**不**加 marker——這些套件三 OS 都有 wheel
- 新增 GitHub Actions workflow `.github/workflows/cross-platform-install.yml`（或在既有 CI workflow 加 matrix job），matrix `os: [ubuntu-latest, macos-latest, windows-latest]`，job 步驟僅做 `uv pip install` 與 `python -c "from cantus import ..."` import smoke
- 新增 `scripts/smoke_install.sh`：把 CI 步驟以 shell script 形式存盤，學生 / 貢獻者可本機重現

**失敗模式：**

- macOS / Windows 上呼叫 `LocalEnvironment.prepare_model(...)` 走進 `_load_with_quant_config` 時，因為 `bitsandbytes` 未安裝會在 `import bitsandbytes` 時拋 `RuntimeError`，訊息保持既有「Loader requires the `runtime` extras. Install with: pip install 'cantus[runtime]'」內容——A0 **不**改錯誤訊息（A1 ship Ollama bridge 時會更新訊息指向 Ollama 路徑）
- CI smoke job 任何一 OS 失敗 → workflow 整體 fail，阻擋 release tag

**Acceptance Criteria：**

- `.github/workflows/cross-platform-install.yml` 三 OS matrix 全綠
- `scripts/smoke_install.sh` 在本機 macOS（Apple Silicon）跑通 → `exit 0`
- `docs/quickstart-desktop.md` 存在且通過 `/humane-prose-audit`（在 Gate A 階段）
- `MIGRATION_v0.4.2_to_v0.4.3.md` 含「macOS / Windows runtime extras 行為變更」段落
- `spectra validate cantus-uv-cross-platform-install` 通過

**Scope 邊界：**

- **In scope：** pyproject marker、quickstart-desktop docs、CI smoke matrix、migration doc、cantus-distribution + cantus-i18n-docs 兩 spec delta
- **Out of scope：** 任何 model loader 程式碼變動、任何新 provider（Ollama / MLX 留給 A1）、任何 channel / serve 行為變動、zh-TW 翻譯 quickstart-desktop（後續 change）

## Risks / Trade-offs

- **Risk：** macOS Intel 學生原本 `pip install cantus-agent[runtime]` 因 bnb resolve 失敗而 abort，A0 後 install 成功——錯誤從「安裝期 abort」推遲到「`LocalEnvironment.prepare_model(...)` 走進 `_load_with_quant_config` 時的 runtime `RuntimeError`」。
  → **Mitigation：** `MIGRATION_v0.4.2_to_v0.4.3.md` 明確說明此改變；`docs/quickstart-desktop.md` 把 macOS 學生引導到 API key path；既有 ImportError 訊息維持指向 `cantus[runtime]` 不誤導（A1 ship 後再更新）

- **Risk：** macOS arm64 / Windows 學生原本在 v0.4.2 上 `pip install cantus-agent[runtime]` 會把 `bitsandbytes` 0.49.x 拉進來（即便 4-bit kernel 無 CUDA backend），有人可能將其當作「可 import 的型別 stub」使用。A0 移除這層 import availability 對下游程式碼是 silent breaking。
  → **Mitigation：** MIGRATION 文件明列「macOS arm64 / Windows runtime extras 不再含 bnb」；對 cantus 教學使用者預設沒有自寫 `import bitsandbytes` 邏輯，影響面有限；若下游確有需求可顯式 `pip install bitsandbytes`

- **Risk：** GitHub Actions windows-latest runner 啟動慢、payload 大，CI 時間延長。
  → **Mitigation：** smoke job 僅做 `uv pip install` 不執行 model；matrix 限定在 `main` push 與 release tag，PR 預設只跑 Linux（沿用既有 CI 模式）

- **Risk：** `[tool.uv].conflicts` 與 marker 互動未知（例如 `cantus-agent[all,openhands]` 在 macOS 是否仍正確報衝突）。
  → **Mitigation：** smoke matrix 增加一個 step 跑 `uv pip install cantus-agent[all]` 確認 `[tool.uv].conflicts` 在三 OS 行為一致；若觸發未預期失敗，A0 propose 加入修正

- **Trade-off：** 不分拆 `runtime` extras → 學生在 macOS / Windows 上看 `cantus[runtime]` 套件列表會少了 bnb，需透過 docs 解釋；分拆 extras 雖 explicit 但 SemVer breaking。A0 選 marker 路徑，trade UX cohesion off against backward compat。

- **Trade-off：** marker 只 gate Linux 而非「has CUDA」——CPU-only Linux runner 上仍會拉 bnb（v0.4.2 行為一致），但 4-bit 量化 runtime 失敗。PEP 508 marker 規格無 CUDA 條件可用；如要更精細 gate，後續可開 `cantus-agent[runtime-cuda]` 等新 extras（A0 不開）。

## Migration Plan

- v0.4.2 → v0.4.3 升版指南 `MIGRATION_v0.4.2_to_v0.4.3.md`：
  1. 列出 macOS / Windows 上 `cantus-agent[runtime]` 不再含 bnb
  2. 指引使用者：本機 LLM 在 macOS / Windows 等 A1（Ollama bridge）ship，現階段請改用 API key path（`load_chat_model("openai/...")`）
  3. Linux 使用者無需任何 action
- Release flow：A0 ship 為 v0.4.3 patch release；CI smoke 加入 release tag pipeline 後再開 v0.4.3 tag
- Rollback：若三 OS smoke 任何 OS 失敗，revert `pyproject.toml` marker 變動即可，pure data change 風險低
