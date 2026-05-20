## Context

cantus v0.3.x 教學弧（v0.3.0 protocol-reorg → v0.3.4 adapter-layer-batch3a）以 release cadence 為主軸推進，五次 release 全部聚焦在 protocol surface（protocol-reorg）、capability 新增（memory-soul-twin-tier、adapter-layer 系列）。release 弧內未補齊三項 dev infrastructure：(a) `pytest-cov` 已在 `cantus[dev]` 安裝但 `pyproject.toml` 無 `[tool.coverage.*]` 設定也無 pytest `--cov` 觸發；(b) cantus 套件無 PEP 561 `py.typed` marker，下游使用 cantus 的 host code 開 strict mypy 一律當 `Any` 看不到 typed surface；(c) cantus 自身無 `[tool.mypy]` 設定，每個 dev 跑 mypy 結果不一致。

v0.3.4 batch3 收尾後也留下一個 cross-link 缺口：`docs/protocols/adapters-batch2.md` 內的 HF / OpenHands import 段落已 superseded by batch3，但讀者直接點 batch2 看到的仍是「deferred to v0.3.4 batch3」的舊措辭。

v0.3.5 是 v0.3.x 教學弧封口後的 maintenance release，目的為下個 feature 弧（v0.4.x 主題待定）打下基礎，使得後續 feature 弧開發時 coverage / mypy 可作為品質回饋訊號。

Stakeholders：cantus 框架維護者（dev workflow 改善 — 跑 `pytest` 看 cov 報告、跑 `mypy cantus` 有基準）、下游 host code 開發者（教學 repo、研究專案、第三方 demo 使用 cantus 時 strict mypy 可看到 typed surface）。

## Goals / Non-Goals

**Goals**

- cantus wheel 安裝後，下游 host code 開 strict mypy 可看到 cantus 公開 API 的 typed surface（不再一律當 `Any`）。
- cantus 開發者跑 `pytest`（不加任何 flag）即可看到 coverage 終端輸出與 `coverage.xml` artifact。
- cantus 開發者跑 `mypy cantus`（不指定任何 flag）使用統一的 baseline 設定，結果 reproducible across dev。
- `docs/protocols/adapters-batch2.md` 開頭明確標示為 batch3 之後的歷史快照，讀者一進來就知道要看 batch3。

**Non-Goals**

- 不啟用 mypy strict（v0.4.x 主題）。
- 不設 coverage fail-under 門檻（先收 baseline）。
- 不引入 ruff format / black 等 formatter 基準。
- 不重寫 cantus 既有 type annotation（只啟用 mypy baseline，annotation 補齊隨後續 PR 漸進）。
- 不新增 cantus public callable。
- 不在主 repo 動學生面 overlay（由 Change 3 處理）。

## Decisions

### Decision 1: `py.typed` 採用空檔 marker（PEP 561 標準作法）

cantus/py.typed 為 0 byte 空檔。PEP 561 規定 marker 內容 SHALL 為空（partial type stubs 用法另有 `py.typed` 內含 `partial\n` 字串的 convention，但 cantus 為完整 inline-typed package，採空檔即可）。`[tool.setuptools.package-data]` 段內加 `cantus = ["py.typed"]` 確保 wheel build 帶上該檔。

**Alternatives 拒絕**：
- 用 `[tool.setuptools.include-package-data] = true` 一次性包含所有非 `.py` 檔：拒絕，會把 `__pycache__` 之外的所有 dotfile / 文件意外打包進 wheel。
- 用 `MANIFEST.in` 設定：拒絕，cantus 目前無 `MANIFEST.in`，引入 sdist 專用機制 fragile。

### Decision 2: mypy 採 `strict = false` 起步，僅啟用 4 個 warning flag

四個啟用：`warn_unused_ignores`、`warn_redundant_casts`、`check_untyped_defs`、`disallow_untyped_defs = false`。`ignore_missing_imports = false` 為全域預設（不要 silent ignore），但對 optional adapter SDK 透過 `[[tool.mypy.overrides]]` 細項放行（`mcp.*` / `langchain_core.*` / `dspy.*` / `transformers.*` / `openhands.*` / `anthropic.*` / `openai.*` / `google.genai.*` / `groq.*`）。

理由：strict=true 在 cantus 既有程式碼會產生大量 warning（特別是 Protocol class 與 `getattr` 動態 attribute access），啟用前需 audit + 補 annotation。v0.3.5 只引入「不破壞既有 dev workflow 但提供 baseline」的最小設定，strict 啟用排到 v0.4.x。

**Alternatives 拒絕**：
- `strict = true`：拒絕，理由如上。
- `strict = true` + 大量 `# type: ignore`：拒絕，會留下難維護的 ignore 噪音。
- 不啟用 `check_untyped_defs`：拒絕，會放棄 type checker 對已標 annotation 函式內部的檢查能力。

### Decision 3: coverage 設定不設 fail-under，預設輸出 term-missing + xml 雙報告

`[tool.coverage.run]` 啟用 `branch = true`（涵蓋分支覆蓋而不只是行覆蓋）。`[tool.coverage.report]` 設 `show_missing = true`、`skip_covered = false`、`exclude_lines = ["pragma: no cover", "if TYPE_CHECKING:", "raise NotImplementedError"]`。`pytest.ini_options.addopts` 觸發 `--cov=cantus --cov-report=term-missing --cov-report=xml`。

理由：
- 不設 fail-under：首次引入 coverage，未知 baseline；強設門檻會落入「太高 CI 紅燈、太低未來難拉」雙輸。
- `branch = true`：分支覆蓋是 path-level 信號，比純行覆蓋更有資訊量。
- `--cov-report=xml`：未來若接 GitHub Actions + codecov / coverlay 服務需要 xml。
- `--cov-report=term-missing`：dev 本地跑 pytest 就能看到具體哪幾行沒覆蓋。

**Alternatives 拒絕**：
- 設 `fail_under = 80`：拒絕，理由如上。
- 不啟用 `branch = true`：拒絕，行覆蓋資訊量不足以引導 refactor。
- 只輸出 term：拒絕，未來接 CI 需要 xml。

### Decision 4: `adapters-batch2.md` 加 supersede note 但保留全文

batch2.md 開頭第一個 H1 之後（或現有 frontmatter 之後）新增一段標題 `**Status:**` 的 supersede 標示，內文 byte-identical 保留。

理由：batch2.md 為 v0.3.3 的 spec snapshot，是 cantus 教學弧的歷史紀錄，刪除會失去 audit trail。加 supersede note 可同時滿足「警示讀者 batch3 才是當前狀態」與「保留歷史完整性」。

**Alternatives 拒絕**：
- 刪除 batch2.md，把內文 merge 進 batch3.md：拒絕，會失去 v0.3.3 與 v0.3.4 的 release 分界 audit trail。
- 改寫 batch2.md 內文反映 v0.3.4 狀態：拒絕，破壞 historical snapshot 的本質。

### Decision 5: Spec 變更走 cantus-distribution Modified Capability

新增的 Requirement「Cantus ships PEP 561 py.typed marker and baseline tool configuration」加入既有 `cantus-distribution` capability，而非新建獨立的 `quality-baseline` capability。

理由：py.typed / mypy / coverage 都屬「cantus 如何被 distribute、如何被 audit、如何被 host 使用」的範疇，與 cantus-distribution 既有 Requirement（「distributed as standalone GitHub repo」、「licensed under ECL 2.0」、「follows SemVer Git tags」、「pre-publication security audit gate」）一脈相承。獨立 capability 會造成 spec 過度分裂、給未來 maintainer 增加 mental overhead。

## Implementation Contract

**In scope**：

1. `libs/cantus/pyproject.toml` 至少包含以下五項變更（順序不限）：
   - `[project] version` 字串為 `0.3.5`。
   - 存在 `[tool.coverage.run]` 段，含 `source = ["cantus"]` 與 `branch = true`。
   - 存在 `[tool.coverage.report]` 段，含 `show_missing = true` 與 `exclude_lines` 至少含 `"pragma: no cover"`、`"if TYPE_CHECKING:"` 兩條。
   - 存在 `[tool.mypy]` 段，含 `python_version = "3.10"`、`warn_unused_ignores = true`、`check_untyped_defs = true`，並對 optional adapter SDK 透過 `[[tool.mypy.overrides]]` 設 `ignore_missing_imports = true`。
   - 存在 `[tool.setuptools.package-data]` 段，含 `cantus = ["py.typed"]`。
   - `[tool.pytest.ini_options].addopts` 字串包含 `"--cov=cantus"` 與 `"--cov-report=term-missing"` 兩個 substring。

2. `libs/cantus/cantus/py.typed` 存在為 0 byte 空檔。

3. `libs/cantus/docs/protocols/adapters-batch2.md` 在 first H1 之後（或檔頭）含一段以 `**Status:` 開頭的 markdown 段，內含字串「Superseded」與「adapters-batch3.md」與 cantus 版本 `v0.3.4` 或 `0.3.4`，cross-link 指向 `adapters-batch3.md`。原 batch2 內文 byte-identical 保留。

4. `libs/cantus/CHANGELOG.md` 含 v0.3.5 entry，列出 py.typed marker、mypy baseline config、coverage config、adapters-batch2 supersede note 四項。

5. `libs/cantus/MIGRATION_v0.3.4_to_v0.3.5.md` 存在，內含 ADDITIVE release 聲明、`from cantus import ...` 與 `from cantus.adapters import ...` 既有 import 路徑全部 byte-identical 的明示聲明、dev workflow 改善摘要（pytest 帶 cov、mypy baseline）、以及一行 `mypy cantus` 範例命令。

**Observable behavior after apply**：

- 在 cantus venv 內（已安裝 `cantus[dev]`）執行 `pytest tests/` 不加任何 flag，stdout 輸出末段含 `---------- coverage` 或 `Name              Stmts   Miss Cover` 表頭，且工作目錄產生 `coverage.xml`。
- 在 cantus venv 內執行 `mypy cantus`，命令以 exit code 0 或 1 結束（允許有 warning，但不允許 mypy 內部 crash 或 config 解析失敗）。
- 在乾淨環境執行 `pip install <wheel> && python -c "from importlib.resources import files; print(files('cantus').joinpath('py.typed').read_text())"`（wheel 由 `python -m build` 從 cantus repo 產出），預期不拋例外、印出空字串。
- 在 cantus venv 執行 `python -c "import cantus; print(cantus.__version__)"` 輸出 `0.3.5`。
- 用瀏覽器或 markdown viewer 開 `libs/cantus/docs/protocols/adapters-batch2.md`，第一螢幕看到 `**Status:** Superseded by ...` 段。

**Out of scope**：

- 任何 cantus 公開 callable 的新增、移除、修改。
- 任何 cantus 既有 type annotation 的補齊或重寫。
- mypy strict 模式啟用。
- coverage fail-under 門檻設定。
- ruff format / black formatter 啟用。
- `cantus.adapters.mcp.py` 的測試補齊。
- `docs/llm_wiki/synthesis.md` 的內容 backfill。
- 主 repo 學生面 overlay 變更（由 Change 3 處理）。
- cantus 上游 git tag `v0.3.5` 的建立與 push（由人工執行）。

## Risks / Trade-offs

- [pyproject 設定區塊 duplication 風險] → Mitigation：apply 階段透過 `python -c "import tomllib; tomllib.load(open('libs/cantus/pyproject.toml','rb'))"` parse 一次確認 TOML 語法合法、所有預期 section 都存在；同時用 `grep -c` 統計各區段標頭只出現一次。
- [coverage `--cov-report=xml` 在無權寫 `coverage.xml` 的環境（例如某些 CI sandbox）會失敗] → Mitigation：term-missing 仍為主要 report；xml 失敗不影響 pytest exit code（pytest-cov 對 xml 寫入失敗會 warn 不會 fail）。文件提及若需 xml 請確保工作目錄可寫。
- [mypy override 列表未涵蓋未來新增 optional adapter] → Mitigation：MIGRATION 文件提到「新增 optional adapter SDK 時需同步 `[[tool.mypy.overrides]]` 列表」，並把這條註明在 `pyproject.toml` 對應段的 comment。
- [下游 host 開 strict mypy 後可能在 cantus 既有非 strict 程式碼上看到新 warning（雖然啟用 py.typed 是為了讓 typed surface 可見）] → Mitigation：v0.3.5 cantus 自身仍非 strict，下游可繼續用 baseline mypy；strict 模式由下游自選風險。MIGRATION 文件提示「若下游已開 strict、且 cantus 既有 annotation 不完整，預期會看到新 warning，視需要加 `# type: ignore` 或 wait v0.4.x cantus strict-ready」。
- [adapters-batch2.md 加 supersede note 後可能與既有 wiki manifest 的內容雜湊不符] → Mitigation：若 cantus 有 `.wiki.manifest.yaml` 內含該檔的 hash，apply 階段需執行 `wiki-master --regen-manifest` 或 `wiki-validator` 確認 hash 同步。實作前先檢查 `libs/cantus/.wiki.manifest.yaml` 是否含 `adapters-batch2.md` 的 ingest 紀錄。

## Migration Plan

本 release ADDITIVE，無 caller migration 步驟。dev workflow migration 為：

1. cantus 開發者：拉 v0.3.5 後，`pip install -e .[dev]` 重新解析（pytest-cov 與 mypy 已存在，無新增）。日常工作流不變，但 `pytest` 現在會多印 coverage 區段、`mypy cantus` 現在會用 baseline 設定。
2. 下游 host 開 strict mypy 者：升級到 cantus v0.3.5 後，原本一律 `Any` 的 cantus import 會開始看到 typed surface；可能有新 warning 浮現（若下游 type 與 cantus typed surface 不對齊），視需要逐條處理或加 `# type: ignore`。
3. 主 repo 學生面 overlay：由 Change 3 `bump-cantus-pin-to-v0-3-5` 獨立處理，不在本 release 範圍。
