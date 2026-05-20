## 1. PyPI namespace 與 Trusted Publisher 前置設定

- [x] 1.1 確認 PyPI 上 `cantus-agent` distribution name 未被佔用、`cantus` 仍由 musicology 占位 release 佔住，把這項事實在 proposal Prerequisites 與 MIGRATION 文件互相 cross-reference；驗證：`python3 -c "import urllib.request; urllib.request.urlopen('https://pypi.org/pypi/cantus-agent/json')"` 回 HTTP 404，`python3 -c "import urllib.request,json; d=json.loads(urllib.request.urlopen('https://pypi.org/pypi/cantus/json').read()); assert d['info']['author_email'].endswith('uni-wuerzburg.de')"` 不報錯
- [x] 1.2 maintainer 在 PyPI 註冊 `cantus-agent` distribution name（先建立空 project），讓「Cantus framework is distributed as standalone GitHub repo」的 PyPI 端 binding 有對應落點；驗證：`https://pypi.org/project/cantus-agent/` 顯示 owner 為 maintainer 帳號（即使尚無 release）
- [x] 1.3 在 PyPI manage account publishing 頁面新增 Trusted Publisher binding（owner=`schola-cantorum`、repo=`cantus`、workflow=`release.yml`、environment=`pypi`），落實 "Adopt OIDC trusted publisher over static PyPI API token" 設計決策；驗證：PyPI 顯示一筆 cantus-agent 的 Trusted Publisher entry 並標為 enabled
- [x] 1.4 在 GitHub `schola-cantorum/cantus` repo Settings → Environments 建立 `pypi` environment（不開 required reviewers，per 開放決議）以及對應的 `testpypi` environment 用於 dry-run；驗證：repo Settings → Environments 列表內出現這兩個 environment

## 2. `libs/cantus/pyproject.toml` PyPI metadata 擴充

- [x] 2.1 把 `[project].name` 從 `cantus` 改為 `cantus-agent`，落實 "Pivot distribution name to `cantus-agent`, keep import name `cantus`" 並 unblocks「pyproject declares full PyPI publication metadata」；驗證：`grep '^name' libs/cantus/pyproject.toml` 顯示 `name = "cantus-agent"`，cantus repo 內 `git grep "^from cantus"` 與 `git grep "^import cantus"` 數量與 v0.4.1 一致
- [x] 2.2 把 `[project].version` bump 至 `"0.4.2"`，反映 "Choose v0.4.2 (PATCH) over v0.5.0 (MINOR)" 設計決策；驗證：`grep '^version' libs/cantus/pyproject.toml` 顯示 `version = "0.4.2"`
- [x] 2.3 新增 `[project.urls]` table 五條（Homepage / Documentation / Source / Issues / Changelog）皆指向 `github.com/schola-cantorum/cantus` 之下的 200 OK URL，使「pyproject declares full PyPI publication metadata」spec scenario "PyPI project page renders all declared URLs" 可通過；驗證：`python -c "import tomllib; print(tomllib.load(open('libs/cantus/pyproject.toml','rb'))['project']['urls'])"` 印出五條 entries 且 key 名稱正確
- [x] 2.4 新增 `[project].keywords` 非空 list 涵蓋 llm / agent / framework / education / colab / polyphonic，補完「pyproject declares full PyPI publication metadata」要求；驗證：`python -c "import tomllib; ks=tomllib.load(open('libs/cantus/pyproject.toml','rb'))['project']['keywords']; assert set(ks) >= {'llm','agent','framework','education','colab','polyphonic'}"` 不報錯
- [x] 2.5 在 `classifiers` list 加入 `Development Status :: 4 - Beta` 與 `Operating System :: OS Independent`，補完「pyproject declares full PyPI publication metadata」要求；驗證：`python -c "import tomllib; cs=tomllib.load(open('libs/cantus/pyproject.toml','rb'))['project']['classifiers']; assert 'Development Status :: 4 - Beta' in cs and 'Operating System :: OS Independent' in cs"` 不報錯
- [x] 2.6 把 license 宣告升 PEP 639 SPDX expression（`license = "ECL-2.0"`）加上 `license-files = ["LICENSE"]`，落實 "Modernize license declaration to PEP 639 SPDX expression" 並推動「Cantus is licensed under ECL 2.0」MODIFIED requirement；驗證：`python -c "import tomllib; p=tomllib.load(open('libs/cantus/pyproject.toml','rb'))['project']; assert p['license']=='ECL-2.0' and p['license-files']==['LICENSE']"` 不報錯，同時 `License :: OSI Approved :: Educational Community License, Version 2.0 (ECL-2.0)` classifier 仍保留
- [x] 2.7 確認 `pyproject.toml` 沒有 setuptools-scm 或其他 dynamic version source（沒有 `[tool.setuptools-scm]`、沒有 `[project.dynamic]` 含 `version`），落實 "Keep version as static `[project].version` string, not setuptools-scm"；驗證：`grep -n setuptools-scm libs/cantus/pyproject.toml` 無輸出、`python -c "import tomllib; p=tomllib.load(open('libs/cantus/pyproject.toml','rb'))['project']; assert isinstance(p['version'],str) and 'version' not in p.get('dynamic',[])"` 不報錯

## 3. Python `__version__` 升 v0.4.2

- [x] 3.1 把 `libs/cantus/cantus/__init__.py` 的 `__version__` 字串從 `"0.4.1"` 改為 `"0.4.2"`，使 `cantus.__version__` 與 pyproject `[project].version` 對齊，落實 "Choose v0.4.2 (PATCH) over v0.5.0 (MINOR)"；驗證：`grep '^__version__' libs/cantus/cantus/__init__.py` 印 `__version__ = "0.4.2"`

## 4. GitHub Actions workflows 從零建起

- [x] 4.1 [P] 新建 `libs/cantus/.github/workflows/release.yml`：`on: release: types: [published]` 與 `workflow_dispatch`（含 `inputs.target` 為 `testpypi`/`pypi`）、`permissions: id-token: write`、`environment: pypi`、build sdist+wheel、`twine check --strict dist/*`、用 `pypa/gh-action-pypi-publish` 完成 OIDC publish，落實「PyPI release pipeline uses OIDC trusted publisher」spec 要求；驗證：`yamllint libs/cantus/.github/workflows/release.yml` 無 error、`grep -c "id-token: write" libs/cantus/.github/workflows/release.yml` 等於 1、`grep -c "twine check --strict" libs/cantus/.github/workflows/release.yml` ≥ 1
- [x] 4.2 [P] 新建 `libs/cantus/.github/workflows/test.yml`：`on: push: branches: [main]` 與 `pull_request`、matrix 涵蓋 Python `["3.10", "3.11", "3.12"]`、每個 job 跑 `pip install -e ".[dev]"` 與 `pytest`，落實「CI test matrix runs pytest on supported Python versions」spec 要求並完成 "Bundle CI test matrix into the same change as the release pipeline" 設計決策；驗證：`yamllint libs/cantus/.github/workflows/test.yml` 無 error、`python -c "import yaml; y=yaml.safe_load(open('libs/cantus/.github/workflows/test.yml')); v=y['jobs']['test']['strategy']['matrix']['python-version']; assert set(v) == {'3.10','3.11','3.12'}"` 不報錯

## 5. Working tree 殘留清理

- [x] 5.1 刪除 `libs/cantus/build/`、`libs/cantus/dist/`、`libs/cantus/cantus.egg-info/`、`libs/cantus/coverage.xml`、`libs/cantus/.coverage` 等 stale artifact，落實「Pre-publish working-tree hygiene」spec 要求；驗證：`find libs/cantus -maxdepth 2 \( -name build -o -name dist -o -name '*.egg-info' -o -name coverage.xml -o -name .coverage \)` 無輸出

## 6. Local dry-run build 與 sdist 內容物 audit

- [x] 6.1 在 `libs/cantus/` 跑 `python -m build`，產出 `dist/cantus_agent-0.4.2.tar.gz` 與 `dist/cantus_agent-0.4.2-py3-none-any.whl`，落實 "Verify sdist contents via local build dry-run"；驗證：`ls libs/cantus/dist/cantus_agent-0.4.2*` 列出兩個檔
- [x] 6.2 跑 `twine check --strict libs/cantus/dist/cantus_agent-0.4.2*` zero warning，確保 README long-description 與 metadata 能被 PyPI 渲染；驗證：command exit code 為 0、輸出末行為 `Passed`
- [x] 6.3 跑 `tar tzf libs/cantus/dist/cantus_agent-0.4.2.tar.gz | sort` 人工 spot-check sdist 內容物：SHALL 含 `cantus/`（含 `py.typed`）、`README.md`、`LICENSE`、`pyproject.toml`、`CHANGELOG.md`、`MIGRATION_*.md`；SHALL NOT 含 `tests/`、`notebooks/`、`docs/`、`assets/`、`scripts/`、`temp/`、`build/`、`dist/`、`*.egg-info/`；驗證：`tar tzf` 輸出符合上述黑白名單
- [x] 6.4 在 `/tmp/cantus-venv` fresh venv 安裝 wheel 並驗證 import 與版號對齊，落實 "Cross-verify `cantus.__version__` against `importlib.metadata.version("cantus-agent")`"；驗證：`python -m venv /tmp/cantus-venv && /tmp/cantus-venv/bin/pip install libs/cantus/dist/cantus_agent-0.4.2-py3-none-any.whl && /tmp/cantus-venv/bin/python -c "import cantus, importlib.metadata as m; assert cantus.__version__ == '0.4.2' == m.version('cantus-agent')"` 不報錯

## 7. TestPyPI dry-run（required gate per design §"Make TestPyPI dry-run a required step, not optional"）

- [x] 7.1 push 暫存 commit 到 cantus repo（含 release.yml 與 metadata 變更）到 feature branch，然後 manual workflow_dispatch 觸發 `release.yml` 並選 `target=testpypi`；驗證：workflow run 在 GitHub Actions 顯示綠燈、`twine check` 與 OIDC publish step 全綠
- [x] 7.2 從 TestPyPI 在 fresh venv 安裝 cantus-agent==0.4.2，確認 cross-repo dependency resolution；驗證：`python -m venv /tmp/cantus-testpypi-venv && /tmp/cantus-testpypi-venv/bin/pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ cantus-agent==0.4.2` 不報錯
- [x] 7.3 驗證 TestPyPI 安裝的版本與 import name 對齊；驗證：`/tmp/cantus-testpypi-venv/bin/python -c "import cantus, importlib.metadata as m; assert cantus.__version__ == '0.4.2' == m.version('cantus-agent')"` 不報錯
- [x] 7.4 訪問 `https://test.pypi.org/project/cantus-agent/0.4.2/` 人工檢查 README 完整渲染（沒有空白 long-description、表格與 code block 都正確渲染、PyPI badge 圖示正常），確認「PyPI release pipeline uses OIDC trusted publisher」 scenario "twine check --strict blocks broken metadata" 的正向案例通過；驗證：頁面截圖確認 PyPI sidebar 五條 URL 都點得進去、README 內容渲染正常

## 8. MIGRATION 文件與 CHANGELOG 條目

- [x] 8.1 [P] 新建 `libs/cantus/MIGRATION_v0.4.1_to_v0.4.2.md`（English canonical），描述 v0.4.2 為 distribution-lifecycle change、零 code-level migration、PyPI distribution name 為 `cantus-agent`、`import cantus` 不變、git+ 路徑保留為 escape hatch，使「Cantus framework is distributed as standalone GitHub repo」MODIFIED requirement 的 v0.4.2 install scenario 在 OSS user 視角有對應文件；驗證：檔案存在、`grep -c "cantus-agent" libs/cantus/MIGRATION_v0.4.1_to_v0.4.2.md` ≥ 3、`grep -c "import cantus" libs/cantus/MIGRATION_v0.4.1_to_v0.4.2.md` ≥ 1
- [x] 8.2 [P] 在 `libs/cantus/CHANGELOG.md` 開 v0.4.2 區段、含 custom `### Distribution` 子段列 PyPI publish / metadata 擴充 / release pipeline / CI matrix；驗證：`grep -n '^## \[0.4.2\]' libs/cantus/CHANGELOG.md` 印 1 行、`grep -n '^### Distribution' libs/cantus/CHANGELOG.md` ≥ 1 行

## 9. README brand-framing 與 PyPI badge 同步

- [x] 9.1 修改 `libs/cantus/README.md` 的 PyPI badge URL（從 `shields.io/pypi/v/cantus.svg` 改為 `shields.io/pypi/v/cantus-agent.svg`、PyPI link 改為 `https://pypi.org/project/cantus-agent/`）、Install 段補 `pip install cantus-agent==0.4.2` 並保留 git+ 區段；驗證：`grep -n "cantus-agent" libs/cantus/README.md` ≥ 3 行（badge URL、PyPI link、install command 各一）
- [x] 9.2 在 `libs/cantus/README.md` 既有 etymology paragraph 之後、`## Open in Colab` 區段之前插入 brand-framing 句（「In Cantus, your code IS the chant — every `Skill`, `Memory`, and `Agent` is a verse that wields the LLM. The PyPI name `cantus-agent` makes the relationship explicit: you chant, the agent answers.」），把「Pivot distribution name to `cantus-agent`, keep import name `cantus`」設計決策的 brand framing 顯化；驗證：`python3 -c "import re; t=open('libs/cantus/README.md').read(); assert 'your code IS the chant' in t and 'cantus-agent' in t.split('## Open in Colab')[0]"` 不報錯
- [x] 9.3 [P] 同步修改 `libs/cantus/README.zhTW.md`：PyPI badge URL、Install 段、與 brand-framing 句的繁中對應版（「在 Cantus 裡，你寫的 code 就是詠唱本身——每一個 `Skill`、`Memory`、`Agent` 都是一段詠唱詞，駕馭著 LLM。套件名 `cantus-agent` 把這層意思點出來：你詠唱，agent 回應。」）；驗證：`grep -c "cantus-agent" libs/cantus/README.zhTW.md` ≥ 3、`grep -c "你詠唱" libs/cantus/README.zhTW.md` ≥ 1

## 10. Two-stage audit gates（archive 前置，落實 design §"Bind two-stage audit gate as archive precondition"）

- [x] 10.1 [P] 跑 `/spectra-audit cantus-pypi-publish` zero blocking finding，確認 cantus-i18n-docs spec Requirement「Two-stage audit gate before PyPI publish」Gate 1 通過；驗證：audit 報告全綠、無 Critical/Warning
- [x] 10.2 [P] 跑 `/humane-prose-audit` 對 `libs/cantus/README.md`、`libs/cantus/CHANGELOG.md`、`libs/cantus/CONTRIBUTING.md`、`libs/cantus/MIGRATION_v0.4.1_to_v0.4.2.md`，落實 Gate 2 prose quality；驗證：四份檔皆 band=high、score ≥ 90、zero Critical/Warning

## 11. cantus repo commit 與 push

- [x] 11.1 用 `/tw-emoji-commit` 產生 commit message 並 commit 所有 cantus repo 變更（pyproject、`__init__.py`、workflows、CHANGELOG、MIGRATION、README、README.zhTW）；驗證：`cd libs/cantus && git log -1 --oneline` 顯示 cantus-pypi-publish 主 commit、`git status` 乾淨
- [x] 11.2 `git push origin main` 把 commit 送上 GitHub `schola-cantorum/cantus`；驗證：`gh api repos/schola-cantorum/cantus/commits/main --jq .sha` 印的 SHA 與 local `git rev-parse main` 一致

## 12. Tag v0.4.2 與 GitHub release

- [x] 12.1 在 cantus repo 建 annotated tag `git tag -a v0.4.2 -m "v0.4.2 — cantus-pypi-publish"`、`git push origin v0.4.2`；驗證：`git ls-remote --tags origin | grep -q v0.4.2`
- [x] 12.2 用 `/tw-emoji-release-note` 產生 release note Markdown 到暫存檔；驗證：暫存檔內容含 v0.4.2 標題、Distribution section、PyPI install command 範例
- [x] 12.3 跑 `gh release create v0.4.2 --notes-file <tmpfile>`（從 draft 轉 published）觸發 `release.yml` 的 `release.published` event，落實「Cantus framework is distributed as standalone GitHub repo」MODIFIED requirement v0.4.2 行為；驗證：GitHub release page 顯示 v0.4.2 為 published、`gh run list --workflow=release.yml --limit 1 --json status,conclusion` 在 ~3 分鐘後顯示 `completed/success`

## 13. Post-publish PyPI 驗證

- [x] 13.1 等 ~30 秒 PyPI propagation，然後在 fresh venv 跑 `pip install cantus-agent==0.4.2`，確認「Cantus framework is distributed as standalone GitHub repo」spec scenario "Install from PyPI exposes the v0.4.2 surface" 通過；驗證：`python -m venv /tmp/cantus-pypi-venv && /tmp/cantus-pypi-venv/bin/pip install cantus-agent==0.4.2` 不報錯
- [x] 13.2 [P] 對 fresh PyPI 安裝再跑一次 cross-verify `cantus.__version__` 與 `importlib.metadata.version("cantus-agent")`；驗證：`/tmp/cantus-pypi-venv/bin/python -c "import cantus, importlib.metadata as m; assert cantus.__version__ == '0.4.2' == m.version('cantus-agent')"` 不報錯
- [x] 13.3 [P] 訪問 `https://pypi.org/project/cantus-agent/0.4.2/` 人工檢查：README 完整渲染、sidebar 五條 URL（Homepage / Documentation / Source / Issues / Changelog）皆 200 OK、License 欄顯示 `ECL-2.0`、Development Status 欄顯示 `Beta`；驗證：頁面截圖確認上述四點皆成立，覆蓋「Cantus is licensed under ECL 2.0」MODIFIED requirement scenario "PyPI surfaces the license correctly"
- [x] 13.4 [P] 驗證 `pip install git+https://github.com/schola-cantorum/cantus@v0.4.2` 在 fresh venv 仍成功（escape hatch 保留），覆蓋「Cantus framework is distributed as standalone GitHub repo」spec scenario "PyPI and git+ install paths coexist"；驗證：`python -m venv /tmp/cantus-git-venv && /tmp/cantus-git-venv/bin/pip install git+https://github.com/schola-cantorum/cantus@v0.4.2 && /tmp/cantus-git-venv/bin/python -c "import cantus; assert cantus.__version__ == '0.4.2'"` 不報錯
