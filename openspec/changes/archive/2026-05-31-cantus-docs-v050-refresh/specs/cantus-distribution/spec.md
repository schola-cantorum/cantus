## MODIFIED Requirements

### Requirement: Cantus README presents hero banner, badge bar, and Open-in-Colab call-to-action

The `schola-cantorum/cantus` repository `README.md` SHALL render, in this order at the top of the document, (a) the hero banner image, (b) a badge bar that displays at minimum a version badge and the ECL-2.0 license, where the version badge SHALL be a dynamic PyPI version badge for the `cantus-agent` distribution (an `<img>` whose source URL references `img.shields.io/pypi/v/cantus-agent`) rather than a hardcoded release-tag version literal, and (c) an Open-in-Colab call-to-action that links to `https://colab.research.google.com/github/schola-cantorum/cantus/blob/<current-tag>/notebooks/task_template.ipynb` where `<current-tag>` is the current published release tag. The README SHALL also render the protocols banner image immediately above the section that introduces the five Cantus protocols. The README SHALL retain the existing one-sentence-per-protocol introductions (Skill, Analyzer, Validator, Workflow, Memory) and the existing License section.

#### Scenario: README opens with hero banner, badge bar, and Open-in-Colab CTA

- **WHEN** a reader opens the cantus repo `README.md` source and inspects the first 30 lines
- **THEN** those lines contain a Markdown image reference whose path is `assets/banner_hero.jpeg`
- **AND** those lines contain a dynamic PyPI version badge whose `<img>` source URL contains the literal substring `img.shields.io/pypi/v/cantus-agent`
- **AND** those lines contain at least one badge whose displayed label includes the literal substring `ECL-2.0`
- **AND** those lines contain a hyperlink whose URL contains both the literal substring `colab.research.google.com/github/schola-cantorum/cantus/blob/` and the literal substring `/notebooks/task_template.ipynb`
- **AND** those lines do NOT contain a hardcoded release-tag version badge (no `<img>` whose source URL contains the literal substring `img.shields.io/badge/release-`)

#### Scenario: protocols banner appears above the five-protocol introductions

- **WHEN** a reader scrolls the cantus README to the section that introduces the five protocols
- **THEN** an `assets/banner_protocols.jpeg` image reference appears in the README source on a line strictly before the first one-sentence Skill / Analyzer / Validator / Workflow / Memory introduction line
- **AND** all five protocol introductions remain present in the README

### Requirement: Cantus README ships a Traditional Chinese variant with bidirectional language switch

The `schola-cantorum/cantus` repository SHALL ship a Traditional Chinese (Taiwan) variant of the README at the repo-root path `README.zhTW.md`, alongside the existing English `README.md`. The `README.zhTW.md` file SHALL mirror the `README.md` section structure: a hero banner that references `assets/banner_hero.jpeg`, a badge bar that displays at minimum a version badge and the ECL-2.0 license, where the version badge SHALL be a dynamic PyPI version badge for the `cantus-agent` distribution (an `<img>` whose source URL references `img.shields.io/pypi/v/cantus-agent`) rather than a hardcoded release-tag version literal, an Open-in-Colab call-to-action whose hyperlink contains the literal substring `colab.research.google.com/github/schola-cantorum/cantus/blob/<current-tag>/notebooks/task_template.ipynb` for the same `<current-tag>` referenced by `README.md`, a 30-second Quickstart code block, a protocols banner image reference that resolves to `assets/banner_protocols.jpeg`, the one-sentence-per-protocol introductions for Skill / Analyzer / Validator / Workflow / Memory, a Documentation section, and a License section. The `README.zhTW.md` narrative prose SHALL be written in Traditional Chinese (Taiwan) vocabulary; the Install commands, Python import statement, and any other executable code blocks SHALL be byte-identical to the corresponding commands and code in `README.md` so that copy-paste produces identical behavior across the two README variants.

Both README variants SHALL provide a visible language switch hyperlink near the top of the document (above or within the badge bar region, in the first 30 lines): `README.md` SHALL link to `README.zhTW.md` via a hyperlink whose visible link text contains the literal substring `繁體中文`, and `README.zhTW.md` SHALL link back to `README.md` via a hyperlink whose visible link text contains the literal substring `English`. Both language-switch hyperlinks SHALL resolve via repo-relative paths so that GitHub web rendering and Colab notebook rendering both follow them without external network calls.

#### Scenario: README.zhTW.md exists with the mandated section structure

- **WHEN** a reader opens the cantus repo `README.zhTW.md` file
- **THEN** the file exists at repo-root path `README.zhTW.md`
- **AND** the file contains a Markdown image reference whose path is `assets/banner_hero.jpeg`
- **AND** the file contains a dynamic PyPI version badge whose `<img>` source URL contains the literal substring `img.shields.io/pypi/v/cantus-agent`
- **AND** the file does NOT contain a hardcoded release-tag version badge (no `<img>` whose source URL contains the literal substring `img.shields.io/badge/release-`)
- **AND** the file contains at least one badge whose displayed label includes the literal substring `ECL-2.0`
- **AND** the file contains a hyperlink whose URL contains the literal substring `colab.research.google.com/github/schola-cantorum/cantus/blob/`
- **AND** the file contains a Markdown image reference whose path is `assets/banner_protocols.jpeg`
- **AND** the file contains the one-sentence-per-protocol introductions for Skill, Analyzer, Validator, Workflow, and Memory (in Traditional Chinese)
- **AND** the file contains a License section that references `ECL-2.0`

#### Scenario: Install and Quickstart code blocks are byte-identical to README.md

- **WHEN** the executable code blocks (pip install commands and the Python Quickstart import-through-print snippet) are extracted from `README.zhTW.md`
- **THEN** each such code block is byte-identical to the corresponding code block in `README.md`

##### Example: byte-identical code blocks

| Block | README.md content | README.zhTW.md content | Required relationship |
| ----- | ----------------- | ---------------------- | --------------------- |
| pip install (tag) | `pip install git+https://github.com/schola-cantorum/cantus@v0.5.0` | `pip install git+https://github.com/schola-cantorum/cantus@v0.5.0` | byte-identical |
| Python Quickstart | `from cantus import skill, Agent, mount_drive_and_load` ... `print(result.final_answer)` | same lines verbatim | byte-identical |
| Open-in-Colab URL fragment | `colab.research.google.com/github/schola-cantorum/cantus/blob/v0.5.0/notebooks/task_template.ipynb` | same URL fragment | byte-identical |

#### Scenario: bidirectional language-switch hyperlinks resolve via repo-relative paths

- **WHEN** a reader inspects the first 30 lines of `README.md`
- **THEN** those lines contain a hyperlink whose visible link text contains the literal substring `繁體中文` and whose href is the repo-relative path `README.zhTW.md` (no `http://`, `https://`, or absolute leading slash)
- **AND when** a reader inspects the first 30 lines of `README.zhTW.md`
- **THEN** those lines contain a hyperlink whose visible link text contains the literal substring `English` and whose href is the repo-relative path `README.md` (no `http://`, `https://`, or absolute leading slash)

#### Scenario: README.md non-localized content is unchanged except for the language-switch link and the release-tag version string

- **WHEN** the `README.md` file is diffed against its v0.1.3 release content
- **THEN** the only changed content is the language-switch hyperlink line(s) pointing to `README.zhTW.md`, the release-tag badge version string moving from `v0.1.3` to `v0.1.4`, the Open-in-Colab URL fragment moving from `blob/v0.1.3/` to `blob/v0.1.4/`, and the Documentation section gaining a single new hyperlink to `docs/llm_wiki/index.md`
- **AND** no existing banner image reference, install command other than the version-string change, Quickstart code line other than the version-string change, protocol introduction sentence, or License section is modified or removed
