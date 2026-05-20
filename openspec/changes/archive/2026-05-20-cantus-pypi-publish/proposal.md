## Prerequisites

- **PyPI namespace pivot**：PyPI 上的 `cantus` 名字被一個 musicology 占位 release 佔走（Tim Eipert / University of Würzburg、2024-05-04 上傳的 `0.0.0` "Coming soon"）。本支 change 改以 `cantus-agent` 為 PyPI distribution name；Python import name 仍是 `cantus`（PyPI 套件名與 Python 套件目錄名互相獨立、先例如 `python-dateutil` → `import dateutil`、`pillow` → `import PIL`）。
- **PyPI Trusted Publisher 一次性設定**：在 tag v0.4.2 之前，maintainer SHALL 先在 PyPI 註冊 `cantus-agent` 套件名，再加上 Trusted Publisher 設定指向 owner `schola-cantorum` / repo `cantus` / workflow file `release.yml` / GitHub environment `pypi`。

## Why

Cantus v0.4.1 目前只能透過 `pip install git+https://github.com/schola-cantorum/cantus@v0.4.1` 取得——對 Colab 學員來說慢、依賴 GitHub availability、無法在下游 `requirements.txt` 內以 PyPI metadata pin 版本。Phase 0 `cantus-docs-i18n-baseline` 已於 2026-05-20 archive，建立雙語 doc baseline 並過了兩道 audit gate，正式 PyPI publish 的前置條件全數解除。本支 change 把 cantus 推上 PyPI，distribution name 採 `cantus-agent`、版本 v0.4.2（PATCH bump，distribution lifecycle change；v0.5.0 留給下一個 capability 弧），同時保留 git+ 安裝路徑作為 `main` 與 commit-SHA snapshot 的 escape hatch。

## What Changes

1. **Pivot distribution name** to `cantus-agent`：把 `libs/cantus/pyproject.toml` 的 `[project].name` 從 `cantus` 改為 `cantus-agent`；Python import path `cantus` 不變，學員 notebook 的 `import cantus` 行不必動。
2. **Bump version** 0.4.1 → 0.4.2：同步更新 `libs/cantus/pyproject.toml` 的 `[project].version` 與 `libs/cantus/cantus/__init__.py` 的 `__version__`。
3. **Add PyPI metadata** to `libs/cantus/pyproject.toml`：
   - 新增 `[project.urls]` table（Homepage / Documentation / Source / Issues / Changelog 五條，皆指向 `github.com/schola-cantorum/cantus` 之下的公開 URL）
   - 新增 `[project].keywords` 非空清單（llm / agent / framework / education / colab / polyphonic）
   - 加入 `Development Status :: 4 - Beta` 與 `Operating System :: OS Independent` classifier
   - License 升 PEP 639 SPDX expression：`license = "ECL-2.0"`（取代既有 `{ text = "ECL-2.0" }` legacy table form）、加上 `license-files = ["LICENSE"]`
4. **Add release workflow**：新增 `libs/cantus/.github/workflows/release.yml`，透過 OIDC trusted publisher publish 到 PyPI；trigger 為 `release.published` event；建 sdist + wheel；上傳前跑 `twine check --strict`；使用 GitHub `environment: pypi` 做保護層。
5. **Add CI test matrix workflow**：新增 `libs/cantus/.github/workflows/test.yml`，在 push to `main` 與 pull_request 觸發 pytest matrix，涵蓋 Python 3.10 / 3.11 / 3.12。
6. **Wipe working-tree residue**：清掉 `libs/cantus/build/`、`libs/cantus/dist/`、`libs/cantus/cantus.egg-info/`、`libs/cantus/coverage.xml`、`libs/cantus/.coverage`（皆 gitignored 但 stale on disk），確保 sdist build 從乾淨樹起算。
7. **Add MIGRATION**：新增 `libs/cantus/MIGRATION_v0.4.1_to_v0.4.2.md`（英文 canonical），聲明 v0.4.2 是 distribution-lifecycle change、零 code-level migration；建議安裝指令從 `pip install git+https://github.com/schola-cantorum/cantus@v0.4.2` 升級為 `pip install cantus-agent==0.4.2`（git+ 路徑仍可用）。
8. **Add CHANGELOG v0.4.2 entry**：在 `libs/cantus/CHANGELOG.md` 開 v0.4.2 區段，使用 custom `### Distribution` 子段（Keep-a-Changelog 允許自訂 section）記錄 PyPI publish、metadata 擴充、release pipeline、CI matrix。
9. **README brand-framing sync**：把 `libs/cantus/README.md` 與 `libs/cantus/README.zhTW.md` 的 PyPI badge URL 與 install snippet 切到 `cantus-agent`；在既有 etymology paragraph 之後、`## Open in Colab` 區段之前各插入一句點出套件名與框架隱喻的關聯（coding 即詠唱、agent 即被駕馭者）。
10. **Modify cantus-distribution spec**：把 `openspec/specs/cantus-distribution/spec.md` 內「SHALL NOT be published to PyPI」prohibition 拿掉；新增三條 ADDED requirement（PyPI metadata、OIDC release pipeline、CI test matrix）；既有 ECL-2.0 license requirement MODIFIED 為要求 SPDX expression form；加入 v0.4.2 Effective Version 段落與新的 install scenario。

## Non-Goals

- 不搬 framework spec 到 cantus repo（Phase 2 `cantus-spec-self-hosting` 另開）。
- 不移除 `pip install git+https://github.com/schola-cantorum/cantus@<ref>` 路徑；保留作為 `main` 與 arbitrary-SHA 安裝 escape hatch。
- 不把 cantus 物理搬到 `/Users/phoenix/dev/edu-projects/cantus/`（Phase 3 另開）。
- 不在本支變更主 repo `libs/cantus/` submodule pin；follow-up `bump-cantus-pin-to-v0-4-2` 另開。
- 不新增 CHANGELOG zh-TW companion 檔案。`cantus-i18n-docs` spec 把它列為 Optional companion；要 promote 為 Required 是另一支 change 的事。
- 不加 Python 3.13 進 CI matrix。`cantus[openhands]` 既有 `python_version >= '3.12' and python_version < '3.13'` marker；擴 matrix 是獨立議題。
- 不申請 readthedocs（roadmap 後續）。
- 不嘗試 PEP 541 取得 `cantus` PyPI 名字。若日後要做，是 `cantus-rename-distribution` 另一支 change。

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `cantus-distribution`：distribution channel 與 license declaration form 兩條 MODIFIED Requirement；PyPI metadata、OIDC release pipeline、CI test matrix、pre-publish working-tree hygiene 四條 ADDED Requirement。

## Impact

- Affected specs：`cantus-distribution`（MODIFIED + ADDED requirements）。
- Affected code：
  - New：
    - libs/cantus/.github/workflows/release.yml
    - libs/cantus/.github/workflows/test.yml
    - libs/cantus/MIGRATION_v0.4.1_to_v0.4.2.md
  - Modified：
    - libs/cantus/pyproject.toml
    - libs/cantus/cantus/__init__.py
    - libs/cantus/CHANGELOG.md
    - libs/cantus/README.md
    - libs/cantus/README.zhTW.md
    - openspec/specs/cantus-distribution/spec.md
  - Removed（working-tree cleanup、gitignored，不是 git 刪除）：
    - libs/cantus/build/
    - libs/cantus/dist/
    - libs/cantus/cantus.egg-info/
    - libs/cantus/coverage.xml
    - libs/cantus/.coverage
