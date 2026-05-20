## Context

cantus v0.4.1 已在 GitHub `schola-cantorum/cantus` 公開發行（commit `9573b24`），但 distribution surface 仍停在「git+ 安裝唯一路徑」狀態：`libs/cantus/pyproject.toml` 缺 `[project.urls]` / `keywords` / `Development Status` classifier，`libs/cantus/.github/workflows/` 不存在，PyPI 上的 `cantus` 名字被 University of Würzburg 的 musicology 占位 release（Tim Eipert、2024-05-04 上傳 `0.0.0`「Coming soon」）佔走。

Phase 0 `cantus-docs-i18n-baseline` 已於 2026-05-20 archive，建立雙語 doc tree 並過了 Phase 0 兩道 audit gate；`cantus-i18n-docs` spec Requirement「Two-stage audit gate before PyPI publish」對任何影響 PyPI publish 的 change archive 仍持續綁定。`libs/cantus/.gitignore` 已涵蓋 `dist/` / `build/` / `*.egg-info/` / `coverage.xml` / `.coverage`，但 working tree 上仍有 stale 殘留（`libs/cantus/dist/cantus-0.3.6-py3-none-any.whl` 等），sdist build 前需要清。

Build backend 是 `setuptools.build_meta`，套件發現透過 `[tool.setuptools.packages.find] include = ["cantus*"]`；PEP 561 `cantus/py.typed` marker 在 v0.3.5 已 ship 並於 v0.4.0 升 strict mypy。`requires-python = ">=3.10"`，因 `cantus[openhands]` 有 `python_version >= '3.12' and python_version < '3.13'` marker，CI matrix 上限到 py3.12。

stakeholders：Phoenix（maintainer、唯一 release operator）、Colab 學員（下游 install consumer）、未來 OSS contributor（PyPI project page 與 README 是第一接觸點）。

## Goals / Non-Goals

**Goals：**

- 把 cantus v0.4.2 推上 PyPI 為 `cantus-agent`，學員與下游 `requirements.txt` 可用 `pip install cantus-agent==0.4.2` 安裝。
- 建立 GitHub Actions release pipeline，採 OIDC trusted publisher（無 static API token）。
- 建立 CI test matrix（py3.10 / 3.11 / 3.12），push to main 與 PR 自動跑。
- 為 PyPI project page 提供完整 metadata：URLs、keywords、Development Status、OS classifier、SPDX license expression、licenses 檔案打包。
- 維持 `import cantus` 不變，現有所有 source code、docs、學員 notebook 的 import 行皆不需修改。
- 把「coding 即詠唱、agent 即被駕馭者」的 brand framing 透過 README intro 一句話顯化，讓 PyPI project page 渲染時直接帶到。

**Non-Goals：**

- 不移除 git+ 安裝路徑（保留 `main` 與 SHA snapshot 用）。
- 不把 framework spec 搬到 cantus repo（屬 Phase 2 `cantus-spec-self-hosting`）。
- 不嘗試 PEP 541 取得 `cantus` PyPI 名字（成功率低、且 publish 不能等）。
- 不擴 CI matrix 到 py3.13（受 `cantus[openhands]` interpreter window 限制）。
- 不在本支 change 內 bump 主 repo `libs/cantus/` submodule pin（另一支 `bump-cantus-pin-to-v0-4-2`）。
- 不新增 `CHANGELOG.zhTW.md`（cantus-i18n-docs spec 把它列為 Optional companion，promote 是另一支 change）。

## Decisions

### Adopt OIDC trusted publisher over static PyPI API token

PyPI 自 2023 年起支援 OpenID Connect 的 Trusted Publisher 機制——release workflow 從 GitHub 取短期 OIDC token、再向 PyPI 換上傳憑證；整段流程不需在 GitHub repo secrets 內存任何 PyPI long-lived token。對比 static API token 方案，OIDC 避免 secret rotation、避免 token 外洩風險、且能配合 GitHub `environment: pypi` 加 required reviewers 做防護。本 change 採 OIDC 為唯一驗證方式；release workflow 不讀 `PYPI_API_TOKEN` 或同義 env var，repo secrets 也不允許保留。

### Pivot distribution name to `cantus-agent`, keep import name `cantus`

PyPI 上 `cantus` 名字被 musicology 占位 release 佔住，PEP 541 取得機率低。PyPI distribution name 與 Python package 目錄名互相獨立（先例：`python-dateutil` → `import dateutil`、`pillow` → `import PIL`、`beautifulsoup4` → `import bs4`），所以可在不動 `cantus/` 目錄、不動任何 source code import 行的前提下，把 PyPI 套件名改為 `cantus-agent`。

選 `-agent` 而非 `-harness`：cantus（拉丁文「歌」）+「詠唱」（zh-TW prompt engineering 慣用詞）本身就內含 harness 的隱喻——詠唱即駕馭。所以套件名只需點出被駕馭的對象（agent），harness 概念由名字本身承擔；coding 即詠唱、agent 即被駕馭者，是本框架想傳達的核心 brand framing。這層意思在 README intro 段落補一句直接點出，讓 PyPI project page 渲染時讀者就能看到「為何叫 cantus-agent」。

影響面收斂於：`libs/cantus/pyproject.toml [project].name`、README PyPI badge URL、`[project.urls]` 中對 PyPI project 頁面的指向、MIGRATION 文件 install 範例、CHANGELOG 條目、cantus-distribution spec 內所有 PyPI install scenario。

### Choose v0.4.2 (PATCH) over v0.5.0 (MINOR)

v0.4.2 反映 distribution lifecycle 升級、零 capability 新增（Python public API surface 與 v0.4.1 byte-identical）。v0.5.0 留給下一個 capability 弧（spec self-hosting 或新 protocol）。不能重用 v0.4.1：tag 已存在（commit `9573b24`）且 pyproject metadata 缺漏；PyPI 也不允許同版本檔案 re-upload。

### Make TestPyPI dry-run a required step, not optional

PyPI 不允許 delete-and-republish 同版本檔案，yanking 也只是隱藏、檔名永久燒掉。第一次 publish 失敗（README 渲染壞、metadata 不完整、wheel 內容物錯誤）會把 `cantus-agent==0.4.2` 永久卡死，被迫立即發 v0.4.3 收拾。TestPyPI dry-run 一次的成本（一次 workflow run、一次 fresh venv install）與第一次正式 publish 失敗的成本（強制 PATCH bump + 兩支 change）相差兩個量級。本 change 把 TestPyPI dry-run 列為 tag v0.4.2 前的必要 gate，acceptance criterion：fresh venv 從 TestPyPI install `cantus-agent==0.4.2`、`import cantus` 成功、`cantus.__version__ == "0.4.2"`、TestPyPI project page 確認 README 完整渲染。

實作上採同一個 `release.yml` workflow 用 `workflow_dispatch` 加 `inputs.target = testpypi | pypi` 切換 upstream repository_url；不另開獨立 `release-testpypi.yml`，減少檔案數與 workflow drift 風險。

### Modernize license declaration to PEP 639 SPDX expression

舊宣告 `license = { text = "ECL-2.0" }` 是 PEP 621 legacy table form，setuptools >=77 與 twine >=6 都會 warn。改為 PEP 639 SPDX expression 形式 `license = "ECL-2.0"`，並顯式 `license-files = ["LICENSE"]` 確保 sdist 與 wheel 都打包 LICENSE 檔案。ECL-2.0 是 SPDX 標準 identifier，所以此次純粹是宣告語法升級、license 本體不變。`cantus-distribution` spec 內既有 ECL-2.0 license requirement 同步 MODIFIED：把舊的「`license = { text = "ECL-2.0" }` or include the corresponding SPDX classifier」改為「PEP 639 SPDX expression 加 `license-files`」。

### Bundle CI test matrix into the same change as the release pipeline

`libs/cantus/.github/workflows/` 從零建起、所有 workflow YAML 與 PyPI publish 共享同一條 GitHub Actions 設定路徑（環境、actions 版本、Python 版本選擇邏輯）；分兩支 change 搬運會重複很多上下文。但 spec 層面把 release pipeline 與 CI test matrix 拆成兩條獨立 ADDED Requirement，讓未來可獨立演化（之後加 py3.13 不會影響 release.yml 的 reviewer rule 或 OIDC binding）。

### Verify sdist contents via local build dry-run

build backend = `setuptools.build_meta`，`[tool.setuptools.packages.find] include = ["cantus*"]` 只抓 `cantus/`，但 sdist 預設會把 repo root 的所有 top-level 檔案塞進來（README.md、CHANGELOG.md、LICENSE、pyproject.toml、MIGRATION_*.md）。需要在 tag v0.4.2 前跑 `python -m build` + `tar tzf dist/*.tar.gz` 人工 spot-check：sdist SHALL 含 `cantus/`（含 `py.typed`）、`README.md`、`LICENSE`、`pyproject.toml`、`CHANGELOG.md`、`MIGRATION_*.md`；SHALL NOT 含 `tests/`、`notebooks/`、`docs/`、`assets/`、`scripts/`、`temp/`、`build/`、`dist/`、`*.egg-info/`。

MIGRATION 檔系列建議「進 sdist」，OSS user `pip download` 後可在本地看升級指南——這是 setuptools 預設行為（top-level `.md` 會被收），不需另寫 `MANIFEST.in`。

### Keep version as static `[project].version` string, not setuptools-scm

目前 `[project].version` 是 hardcoded `"0.4.1"` 字串。維持靜態源頭：好處是 `actions/checkout@v4` 不需要 `fetch-depth: 0`（不需完整 git history 算版號），且 `__version__` 與 PyPI metadata 兩處字串對齊是顯式人工動作、不會被 dynamic version 制度誤判。spec 加一條 ADDED 子聲明：「版本源頭 SHALL 為 static `[project].version` 字串，SHALL NOT 來自 setuptools-scm 或其他 dynamic source」。

### Cross-verify `cantus.__version__` against `importlib.metadata.version("cantus-agent")`

PyPI bump 最常見 regression 是 `__version__` 字串與 wheel metadata 版號 drift——人工改了 pyproject.toml 但忘了改 `cantus/__init__.py`（或反過來）。在 task 6.4（local dry-run）與 task 15.3（post-publish）加交叉驗證：`python -c "import cantus, importlib.metadata; assert cantus.__version__ == '0.4.2' == importlib.metadata.version('cantus-agent')"`。注意 `importlib.metadata.version` 的查詢 key 是 **PyPI distribution name**（`cantus-agent`），不是 Python import name（`cantus`）——這個非對稱對下游診斷工具很重要。

### Bind two-stage audit gate as archive precondition

`cantus-i18n-docs` spec Requirement「Two-stage audit gate before PyPI publish」已宣告：任何影響 PyPI publish 的 change 在 archive 前需要過 Gate 1（`/spectra-audit`）與 Gate 2（`/humane-prose-audit` 對 README.md / CHANGELOG.md / CONTRIBUTING.md）兩道審核、皆要 zero Critical/Warning。tasks.md 把這兩道 gate 寫成 tag v0.4.2 前的明確 task；本 change 新增的 `MIGRATION_v0.4.1_to_v0.4.2.md` 與 README brand-framing 句也納入 Gate 2 audit 範圍。

## Implementation Contract

**Observable behavior after this change ships：**

- `pip install cantus-agent==0.4.2` 在任意 Python 3.10–3.12 fresh venv 成功安裝；安裝後 `import cantus` 成功、`cantus.__version__ == "0.4.2"`、`importlib.metadata.version("cantus-agent") == "0.4.2"`。
- `pip install git+https://github.com/schola-cantorum/cantus@v0.4.2` 仍然成功（escape hatch 保留）。
- `https://pypi.org/project/cantus-agent/0.4.2/` 頁面顯示完整 README 渲染、ECL-2.0 license 欄、Homepage / Documentation / Source / Issues / Changelog 五條 sidebar 連結皆可點。
- GitHub release `v0.4.2` 被 publish（從 draft 變 published）後，`.github/workflows/release.yml` 在 `environment: pypi` 內自動執行：build sdist + wheel、`twine check --strict dist/*` 過、OIDC 換 PyPI 上傳憑證、upload 成功；不讀任何 `PYPI_API_TOKEN`。
- 任何 PR 對 `main` 觸發 `.github/workflows/test.yml` 並產生三個獨立 job（py3.10 / 3.11 / 3.12）；三個 job 全綠才能 merge。

**Interface / data shape：**

- `libs/cantus/pyproject.toml` 公開 schema：`[project].name = "cantus-agent"`、`[project].version = "0.4.2"`、`[project.urls]` 包含 Homepage / Documentation / Source / Issues / Changelog 五個 key、`[project].keywords` 為非空 list、`classifiers` 包含 `Development Status :: 4 - Beta` 與 `Operating System :: OS Independent`、`license = "ECL-2.0"` SPDX 字串、`license-files = ["LICENSE"]`。
- `libs/cantus/cantus/__init__.py`：`__version__ = "0.4.2"`。
- `libs/cantus/.github/workflows/release.yml`：`on: release: types: [published]` 與 `workflow_dispatch`（後者帶 `inputs.target` 為 `testpypi` 或 `pypi`）；job 在 `environment: pypi`（或 testpypi）內、`permissions: id-token: write`；先跑 build、再跑 `twine check --strict`、最後跑 `pypa/gh-action-pypi-publish`。
- `libs/cantus/.github/workflows/test.yml`：`on: push: branches: [main]` 與 `pull_request`；`strategy.matrix.python-version` 包含 `["3.10", "3.11", "3.12"]`；job step 跑 `pip install -e ".[dev]"` 與 `pytest`。
- `libs/cantus/MIGRATION_v0.4.1_to_v0.4.2.md`：英文 canonical；說明 zero code-level migration、PyPI 套件名為 `cantus-agent`、`import cantus` 不變、git+ 路徑仍可用。
- `libs/cantus/CHANGELOG.md`：v0.4.2 區段含 `### Distribution` 子段、列 PyPI publish / metadata 擴充 / release pipeline / CI matrix。

**Failure modes：**

- 若 PyPI 對 `cantus-agent` 還沒註冊或 Trusted Publisher 未綁，release.yml 上傳階段會回 403/404；workflow 失敗、release 仍在 published 狀態但 PyPI 上沒檔案——maintainer 手動補設定後重跑 workflow。
- 若 `twine check --strict` 偵測到 README 渲染問題、metadata 缺漏，workflow 在 upload 前 fail；PyPI 上不會出現損壞的 v0.4.2 release。
- 若 `cantus.__version__` 與 `importlib.metadata.version("cantus-agent")` 不一致，post-publish 驗證 task 失敗；要立即發 v0.4.3 修字串對齊，因為 v0.4.2 已不可改。
- 若 CI test matrix 在新版 Python 上 fail，PR 卡住 status check；不影響既有 release（release.yml 與 test.yml 互不觸發）。
- 若 working tree 殘留 `libs/cantus/dist/` 等 stale artifact，本地 dry-run sdist 內容物可能被污染、人工 spot-check 抓到後清。release.yml 在 CI runner 上跑時 workspace 是乾淨 checkout、不會受本地污染。

**Acceptance criteria：**

- `spectra validate cantus-pypi-publish` 全綠。
- `spectra analyze cantus-pypi-publish --json` zero Critical/Warning。
- `/spectra-audit cantus-pypi-publish` zero finding。
- `/humane-prose-audit` 對 README.md / CHANGELOG.md / CONTRIBUTING.md / MIGRATION_v0.4.1_to_v0.4.2.md 結果為 band=high、zero Critical/Warning。
- 本地 `python -m build` 與 `twine check --strict dist/*` zero warning；fresh venv 安裝 wheel 後 import + version 驗證通過。
- TestPyPI dry-run 通過：workflow run 成功、TestPyPI project page 渲染正常、fresh venv 從 TestPyPI install 成功。
- 正式 PyPI publish 後：`pip install cantus-agent==0.4.2` 在任意外部 fresh venv 成功；`https://pypi.org/project/cantus-agent/0.4.2/` 渲染完整。

**Scope boundaries：**

- 在 scope：cantus repo（submodule）內 pyproject.toml metadata 擴充、`.github/workflows/{release.yml,test.yml}` 新建、版本 bump 0.4.1 → 0.4.2、CHANGELOG / MIGRATION / README 對齊、`openspec/specs/cantus-distribution/spec.md` MODIFIED + ADDED。
- 不在 scope：主 repo submodule pin bump（另一支）、framework spec 搬遷（Phase 2）、cantus 物理位置搬遷（Phase 3）、PEP 541 名字爭取、CHANGELOG zh-TW companion 新建、Python 3.13 matrix 擴充、readthedocs 申請、任何 cantus Python source code 變更（`cantus/__init__.py` 的 `__version__` 字串以外）。

## Risks / Trade-offs

- **第一次 PyPI publish 不可逆**：PyPI 不允許同版本 re-upload，yanking 只隱藏不刪除檔名。→ Mitigation：強制 TestPyPI dry-run、`twine check --strict` 上傳前驗、local sdist content audit；release.yml 在 `release.published` 才觸發（draft 不觸發），保留人工最終確認點。
- **OIDC Trusted Publisher 設定錯**：owner/repo/workflow/environment 任一不對都會 publish 失敗。→ Mitigation：proposal 段落把 4 個欄位明示列入 Prerequisites；tasks.md task 0 包含 PyPI web UI 設定步驟與驗證；GitHub `environment: pypi` 由 maintainer 在 repo Settings 內手動建立。
- **下游 install 路徑改變的學員衝擊**：學員 notebook setup cell 寫死 `pip install git+...`，PyPI publish 後若不更新仍會 work（git+ 路徑保留），但失去 PyPI metadata pin 的優勢。→ Mitigation：主 repo 後續 `bump-cantus-pin-to-v0-4-2` change 內把 notebook setup cell 同步切到 `pip install cantus-agent==0.4.2`，並在 README 雙語段註明「PyPI 為主、git+ 為 escape hatch」。
- **`__version__` 與 wheel metadata drift**：人工字串對齊容易漏改一邊。→ Mitigation：local dry-run 與 post-publish 兩個 task 強制跑 cross-verification assert（design 段「Cross-verify `cantus.__version__`」）。
- **PyPI 名字與框架名稱不一致的長期 confusion**：下游 user 看到 `pip install cantus-agent` 但 `import cantus`，初次接觸需要解釋。→ Mitigation：README intro 加 brand-framing 句直接點出來；MIGRATION 文件提供「為什麼 PyPI 名是 cantus-agent」段落；PyPI project page description 開頭即說明 import name。
- **License 宣告升 PEP 639 後與既有 classifier 重複**：classifiers 仍有 `License :: OSI Approved :: Educational Community License, Version 2.0 (ECL-2.0)`，與新的 `license = "ECL-2.0"` SPDX 字串並存。→ Mitigation：保留 classifier（向後相容老 PyPI 客戶端）；spec 段 MODIFIED 文字明示「兩者並存皆合法」。
- **TestPyPI 與 PyPI dependency resolution 不對等**：TestPyPI 可能缺某些 dependency（fastapi、uvicorn 等），需用 `--extra-index-url https://pypi.org/simple/` 補。→ Mitigation：TestPyPI install command 內含這個 flag；MIGRATION 文件不會記錄這條（只是 testing artifact）。

## Migration Plan

- **Deploy**：tag v0.4.2 → push tag → `gh release create v0.4.2 --notes-file <release-note>` → release.yml 觸發 → PyPI publish。
- **Rollback**：v0.4.2 一旦 publish 不可刪。若發現嚴重 metadata 錯誤，立即 `pip yank cantus-agent==0.4.2` 並發 v0.4.3 修復；v0.4.2 wheel 留在 PyPI 但被標 yanked，新 pip 預設不會選到。
- **Downstream impact**：學員 Colab notebook setup cell 不需立即改（git+ 路徑保留）；主 repo `bump-cantus-pin-to-v0-4-2` change 內逐步切到 `pip install cantus-agent==0.4.2`。

## Open Questions

- TestPyPI 與 PyPI 共用同一 OIDC trusted publisher，還是分兩個 binding？目前計畫共用一個 workflow + `inputs.target` 切換 repository_url；TestPyPI 端也需要對應的 Trusted Publisher 設定（target = `cantus-agent` on test.pypi.org）。實作階段確認。
- MIGRATION 檔案是否要保留 zh-TW 翻譯（mirror `libs/cantus/MIGRATION_v0.4.1_to_v0.4.2.zhTW.md`）？cantus-i18n-docs spec 沒把 MIGRATION 列入 Required zh-TW companion；目前計畫只 ship 英文 canonical。實作階段確認。
