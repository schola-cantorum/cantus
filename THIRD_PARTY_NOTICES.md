# Third-party notices

cantus is licensed under the Educational Community License 2.0 (root LICENSE).
The collaboration scaffolding copied from the harness-agile template (shared rules in
`docs/agents/`, `scripts/verify-project.py`, runtime roles and project-authored skills)
is MIT-licensed by CXPhoenix; the full text is in
[docs/agents/harness-agile.LICENSE](docs/agents/harness-agile.LICENSE).
That grant covers rights held by CXPhoenix; it does not replace third-party
copyright, font, artwork, or trademark terms. Preserve applicable notices when
copying a skill or distributing a generated project.

## Matt Pocock skills — MIT

Copyright (c) 2026 Matt Pocock. Each of the following project skill directories
contains the complete upstream MIT text in its own LICENSE so an individually
copied skill retains the notice:

- [code-review](.agents/skills/code-review/LICENSE)
- [codebase-design](.agents/skills/codebase-design/LICENSE)
- [diagnosing-bugs](.agents/skills/diagnosing-bugs/LICENSE)
- [domain-modeling](.agents/skills/domain-modeling/LICENSE)
- [grill-me](.agents/skills/grill-me/LICENSE)
- [grill-with-docs](.agents/skills/grill-with-docs/LICENSE)
- [grilling](.agents/skills/grilling/LICENSE)
- [handoff](.agents/skills/handoff/LICENSE)
- [implement](.agents/skills/implement/LICENSE)
- [improve-codebase-architecture](.agents/skills/improve-codebase-architecture/LICENSE)
- [prototype](.agents/skills/prototype/LICENSE)
- [research](.agents/skills/research/LICENSE)
- [resolving-merge-conflicts](.agents/skills/resolving-merge-conflicts/LICENSE)
- [setup-matt-pocock-skills](.agents/skills/setup-matt-pocock-skills/LICENSE)
- [tdd](.agents/skills/tdd/LICENSE)
- [teach](.agents/skills/teach/LICENSE)
- [to-questionnaire](.agents/skills/to-questionnaire/LICENSE)
- [to-spec](.agents/skills/to-spec/LICENSE)
- [to-tickets](.agents/skills/to-tickets/LICENSE)
- [wait-what](.agents/skills/wait-what/LICENSE)
- [wayfinder](.agents/skills/wayfinder/LICENSE)
- [wizard](.agents/skills/wizard/LICENSE)
- [writing-for-agents](.agents/skills/writing-for-agents/LICENSE)

Source: https://github.com/mattpocock/skills . The license verification revision and SHA-256 are recorded in
docs/agents/skill-sources.json. Verification revisions do not imply that locally
adapted skill instructions match upstream HEAD byte for byte.

## agent-browser — Apache-2.0

Source: https://github.com/vercel-labs/agent-browser . The bundled discovery
guidance is an adapted upstream skill, not the browser executable. The full
[Apache-2.0 license](.agents/skills/agent-browser/LICENSE) is included; the modified
SKILL.md carries a change notice. No root NOTICE file was present at the verified
upstream revision. Installing the external CLI separately also subjects that
installation to its own distribution notices.

## i-have-adhd — MIT

Copyright (c) 2026 Ayoub Ghriss. Source: https://github.com/ayghri/i-have-adhd .
The complete [MIT license](.agents/skills/i-have-adhd/LICENSE) is included.
The project retains its existing metadata and instruction differences.

## security-review

- [security-review MIT license](.agents/skills/security-review/LICENSE):
  Copyright (c) 2025 Anthropic; source and pinned revision are in skill-sources.json.

## evidence-report — project adaptation with design-source attribution

Created by the maintainer using Claude Code and copied into this template.
The original session records maintainer approval to embed concise design
principles from local phoenix-design, which identifies
[alchaincyf/huashu-design](https://github.com/alchaincyf/huashu-design) as its source.
Design-source attribution: Copyright (c) 2026 alchaincyf (花叔 · 花生).
The complete upstream [MIT notice](.agents/skills/evidence-report/LICENSE) is
preserved with the skill. Project-authored additions are covered by the harness-agile MIT license.

The session also invoked artifact-design; invocation alone is not recorded as
proof of copying an independently identified external package. No unrelated
same-name repository is attributed as the direct source. Source verification
revisions identify the license checked, not the original local installation.

## Project-authored skills — MIT

On 2026-09-13 the maintainer confirmed that tw-emoji-commit, tw-emoji-pr-note,
tw-emoji-release-note, and init-template were authored by the maintainer using
Claude Code. They are recorded as project-authored material under the harness-agile MIT
license. This provenance record is based on the maintainer's explicit confirmation.

## egm-drift-report — Apache-2.0 local adaptation

Source: google/elephant-goldfish-model, revision
403d8881d62022490637d740657b33f01e321ea8. The drift workflow was adapted for
harness-agile on 2026-11-01: local runtime entries, evidence/status handling,
report placement, write boundaries and existing delivery gates replace upstream
plugin conventions. This is not a complete EGM plugin installation or an
upstream-supported integration.

The complete Apache-2.0 text is retained in both
[Codex](.agents/skills/egm-drift-report/LICENSE) and
[Claude](.claude/skills/egm-drift-report/LICENSE) copies. The shared adapted contract
is [docs/agents/drift-report.md](docs/agents/drift-report.md).
No NOTICE file was present in the pinned upstream tree. Neither the cantus nor the harness-agile license replaces these third-party terms. Source verification and hashes are recorded in
docs/agents/skill-sources.json.

## eli5 — license not verified

Source: https://github.com/dreambigou/eli5 (`skills/eli5/SKILL.md`), installed in
cantus before the harness-agile migration. The installed copy carried no license file
and the upstream license has not been verified; see docs/agents/skill-sources.json.
