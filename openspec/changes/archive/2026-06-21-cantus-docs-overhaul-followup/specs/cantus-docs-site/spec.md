## ADDED Requirements

### Requirement: Superseded legacy documentation pages SHALL NOT duplicate site content

The documentation site under `docs/site/` SHALL be the single canonical human-facing source for the pages it covers. A legacy top-level documentation page that has been superseded by a `docs/site/` page SHALL NOT retain a duplicate copy of that page's body. Such a legacy page SHALL either be removed, or be reduced to a redirect stub whose content is a short notice plus a repository-relative Markdown link to the corresponding `docs/site/` source file. A redirect stub SHALL NOT hardcode a deployed site domain, and SHALL retain the page's original top-level heading so heading-only inbound links still land on a titled page. Legacy pages that have no `docs/site/` counterpart, and pages pinned by another capability, are outside this Requirement and SHALL remain unchanged.

#### Scenario: Superseded page carries no duplicated body

- **WHEN** a legacy top-level documentation page that has a `docs/site/` counterpart is inspected after this Requirement is satisfied
- **THEN** the page is either absent from the working tree, or its content is only a redirect stub linking to its `docs/site/` counterpart
- **AND** the page does not contain a second copy of the corresponding site page's body

#### Scenario: Redirect stub keeps inbound links resolving

- **WHEN** an existing reference from a migration guide, the desktop quickstart, a runtime docstring, or a contributor file points at a redirected legacy page
- **THEN** that reference resolves to an existing file
- **AND** the file forwards the reader to the `docs/site/` counterpart

#### Scenario: Pages without a site twin are left intact

- **WHEN** a legacy page that has no `docs/site/` counterpart, such as `docs/protocols/adapters-batch2.md`, is inspected after this Requirement is satisfied
- **THEN** the page retains its original content and is neither removed nor reduced to a stub
