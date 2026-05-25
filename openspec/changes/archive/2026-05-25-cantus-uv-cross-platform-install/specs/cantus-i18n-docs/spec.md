## ADDED Requirements

### Requirement: Cross-platform desktop quickstart doc SHALL classify as Required English canonical with Optional zh-TW companion

The cantus repository SHALL ship `docs/quickstart-desktop.md` as a Required English canonical document in the four-layer i18n classification. The document SHALL contain English-only prose (no Traditional Chinese paragraphs) and SHALL serve as the authoritative cross-platform desktop entry point (Windows / macOS / Linux) for first-time framework users who are not running inside Google Colab.

The document SHALL open with a `uv pip install cantus-agent` install instruction valid on all three desktop operating systems, SHALL present a 5-minute "API key path" walkthrough as its first executable example (using `load_chat_model("openai/...")` or equivalent provider), and SHALL clearly state that 4-bit local Gemma loading is only supported on Linux with CUDA in v0.4.3. The document SHALL link back to `docs/quickstart.md` (the Colab-oriented quickstart) for users who prefer the Colab path.

The corresponding zh-TW file `docs/quickstart-desktop.zhTW.md` SHALL classify as an Optional zh-TW companion (per the existing `Optional zh-TW companion docs require per-document decision` Requirement). Its absence in v0.4.3 SHALL NOT be treated as a defect by `/spectra-audit cantus-docs-i18n-baseline`. Any future change that adds `docs/quickstart-desktop.zhTW.md` SHALL update the Optional zh-TW companion enumeration to promote the document into the Required Traditional Chinese companion layer.

`docs/quickstart-desktop.md` SHALL be subject to the existing two-stage audit gate (`/spectra-audit cantus-docs-i18n-baseline` for structural completeness, `/humane-prose-audit` for English prose quality) before any PyPI release that depends on it.

#### Scenario: Required English canonical layer includes quickstart-desktop

- **WHEN** a contributor reads the i18n classification enumeration
- **THEN** `docs/quickstart-desktop.md` SHALL appear among the Required English canonical documents
- **AND** the document SHALL exist in the cantus repository working tree

#### Scenario: PyPI long-description ecosystem does not break when quickstart-desktop ships

- **WHEN** the PyPI publishing pipeline reads `README.md` as the long-description source
- **THEN** the rendered output SHALL still contain no Traditional Chinese paragraphs
- **AND** the `README.md` SHALL link to `docs/quickstart-desktop.md` as the cross-platform entry without inlining the desktop quickstart content

#### Scenario: Optional zh-TW companion absence is not a defect

- **WHEN** `/spectra-audit cantus-docs-i18n-baseline` runs against a working tree where `docs/quickstart-desktop.zhTW.md` does not exist but `docs/quickstart-desktop.md` does
- **THEN** the audit SHALL NOT report the absence of `docs/quickstart-desktop.zhTW.md` as a finding

#### Scenario: Two-stage audit gate covers quickstart-desktop

- **WHEN** a change that touches `docs/quickstart-desktop.md` is prepared for release
- **THEN** `/spectra-audit cantus-docs-i18n-baseline` SHALL execute and pass on the structural classification
- **AND** `/humane-prose-audit` SHALL execute and pass on the English prose quality of `docs/quickstart-desktop.md`
- **AND** both audits SHALL pass before the PyPI publish workflow is allowed to proceed
