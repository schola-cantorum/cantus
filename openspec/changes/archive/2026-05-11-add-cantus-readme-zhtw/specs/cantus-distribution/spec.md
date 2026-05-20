## ADDED Requirements

### Requirement: Cantus README ships a Traditional Chinese variant with bidirectional language switch

The `schola-cantorum/cantus` repository SHALL ship a Traditional Chinese (Taiwan) variant of the README at the repo-root path `README.zhTW.md`, alongside the existing English `README.md`. The `README.zhTW.md` file SHALL mirror the `README.md` section structure: a hero banner that references `assets/banner_hero.jpeg`, a badge bar that displays at minimum the current GitHub release tag and the ECL-2.0 license, an Open-in-Colab call-to-action whose hyperlink contains the literal substring `colab.research.google.com/github/schola-cantorum/cantus/blob/<current-tag>/notebooks/task_template.ipynb` for the same `<current-tag>` referenced by the `README.md` release-tag badge, a 30-second Quickstart code block, a protocols banner image reference that resolves to `assets/banner_protocols.jpeg`, the one-sentence-per-protocol introductions for Skill / Analyzer / Validator / Workflow / Memory, a Documentation section, and a License section. The `README.zhTW.md` narrative prose SHALL be written in Traditional Chinese (Taiwan) vocabulary; the Install commands, Python import statement, and any other executable code blocks SHALL be byte-identical to the corresponding commands and code in `README.md` so that copy-paste produces identical behavior across the two README variants.

Both README variants SHALL provide a visible language switch hyperlink near the top of the document (above or within the badge bar region, in the first 30 lines): `README.md` SHALL link to `README.zhTW.md` via a hyperlink whose visible link text contains the literal substring `繁體中文`, and `README.zhTW.md` SHALL link back to `README.md` via a hyperlink whose visible link text contains the literal substring `English`. Both language-switch hyperlinks SHALL resolve via repo-relative paths so that GitHub web rendering and Colab notebook rendering both follow them without external network calls.

#### Scenario: README.zhTW.md exists with the mandated section structure

- **WHEN** a reader opens the cantus repo `README.zhTW.md` file
- **THEN** the file exists at repo-root path `README.zhTW.md`
- **AND** the file contains a Markdown image reference whose path is `assets/banner_hero.jpeg`
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
| pip install (tag) | `pip install git+https://github.com/schola-cantorum/cantus@v0.1.3` | `pip install git+https://github.com/schola-cantorum/cantus@v0.1.3` | byte-identical |
| Python Quickstart | `from cantus import skill, Agent, mount_drive_and_load` ... `print(result.final_answer)` | same lines verbatim | byte-identical |
| Open-in-Colab URL fragment | `colab.research.google.com/github/schola-cantorum/cantus/blob/v0.1.3/notebooks/task_template.ipynb` | same URL fragment | byte-identical |

#### Scenario: bidirectional language-switch hyperlinks resolve via repo-relative paths

- **WHEN** a reader inspects the first 30 lines of `README.md`
- **THEN** those lines contain a hyperlink whose visible link text contains the literal substring `繁體中文` and whose href is the repo-relative path `README.zhTW.md` (no `http://`, `https://`, or absolute leading slash)
- **AND when** a reader inspects the first 30 lines of `README.zhTW.md`
- **THEN** those lines contain a hyperlink whose visible link text contains the literal substring `English` and whose href is the repo-relative path `README.md` (no `http://`, `https://`, or absolute leading slash)

#### Scenario: README.md non-localized content is unchanged except for the language-switch link

- **WHEN** the `README.md` file is diffed against its pre-change content
- **THEN** the only added content is the language-switch hyperlink line(s) pointing to `README.zhTW.md`
- **AND** no existing badge URL, banner image reference, install command, Quickstart code line, protocol introduction sentence, Documentation link, or License section is modified or removed
