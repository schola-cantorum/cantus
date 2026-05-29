## ADDED Requirements

### Requirement: TUI renders a tabbed dashboard shell

The TUI SHALL present its panes within a tabbed interface containing five tabs: Dashboard, Skills, Permissions, Dataflow, and Inspector. The Dashboard tab SHALL present a Sessions master list, a Queue pane, and a Health pane, and the Sessions master list SHALL be the focus target that drives the Inspector tab. The TUI SHALL provide keybindings that switch the active tab. The Sessions master list SHALL remain the single source of the currently selected run across all tabs.

#### Scenario: five tabs are present

- **WHEN** the TUI starts and connects to a reachable server
- **THEN** the Dashboard, Skills, Permissions, Dataflow, and Inspector tabs are all available
- **AND** the Dashboard tab shows the Sessions, Queue, and Health panes

#### Scenario: keybinding switches the active tab

- **WHEN** the user activates the keybinding for a tab other than the current one
- **THEN** that tab becomes the active tab and its content is shown

### Requirement: Skills tab lists registered skills and marks active runs

The Skills tab SHALL display the skills returned by the introspection skills slice, one row per skill, each showing the skill name, description, and an argument summary. A skill that has at least one session currently in the running state SHALL be marked as active in the Skills tab. The Skills tab SHALL derive the active marking from the sessions slice without issuing any additional request.

#### Scenario: registered skills are listed

- **WHEN** the TUI polls a reachable server that has registered skills
- **THEN** the Skills tab shows one row per registered skill with its name and description

#### Scenario: a skill with a running session is marked active

- **WHEN** a session whose source identifies a skill is in the running state
- **THEN** the Skills tab marks that skill as active

##### Example: active derivation from sessions

- **GIVEN** sessions: s1(source="skill:echo", status=running), s2(source="skill:sum", status=completed)
- **WHEN** the Skills tab refreshes
- **THEN** the skill "echo" is marked active and the skill "sum" is not

### Requirement: Permissions tab summarizes the auth posture

The Permissions tab SHALL display the effective authentication posture returned by the introspection permissions slice: the auth mode, whether the dashboard requires auth, whether introspection requires auth, and the list of gated routes. The Permissions tab SHALL NOT display, log, or otherwise reveal any token or secret value.

#### Scenario: auth posture is shown

- **WHEN** the TUI polls a reachable server
- **THEN** the Permissions tab shows the auth mode, the dashboard and introspection auth-required flags, and the gated routes

#### Scenario: no token value is revealed

- **WHEN** the TUI runs with a configured token
- **THEN** the token value does not appear anywhere in the Permissions tab

### Requirement: Dataflow tab renders the component topology

The Dataflow tab SHALL render the component topology returned by the introspection dataflow slice as a textual listing of nodes and the edges connecting them. When the dataflow slice reports no nodes and no edges, the Dataflow tab SHALL show a placeholder message rather than an empty pane.

#### Scenario: nodes and edges are shown

- **WHEN** the TUI polls a reachable server whose dataflow slice reports nodes and edges
- **THEN** the Dataflow tab shows each node and the edges connecting it to its targets

##### Example: adjacency rendering

- **GIVEN** nodes: serve(kind=app), event_stream(kind=event_stream); edges: serve→event_stream(label="emits")
- **WHEN** the Dataflow tab refreshes
- **THEN** the listing shows the serve node with an "emits" edge to the event_stream node

### Requirement: Inspector tab presents the selected run's workflow trace

The Inspector tab SHALL display the ordered Action/Observation steps of the run currently selected in the Dashboard Sessions master list, fetched from the workflow introspection endpoint for that run id, rendered in execution order with each step's full summary. The Inspector tab SHALL show a header that identifies the selected run. When no run is selected, or when the selected run has no recorded trace, the Inspector tab SHALL show a placeholder message rather than an error dialog.

#### Scenario: selecting a session shows its trace in the Inspector

- **WHEN** the user selects a session row whose run has a recorded trace and views the Inspector tab
- **THEN** the Inspector tab shows that run's steps in execution order
- **AND** shows a header identifying the selected run

#### Scenario: no selection shows a placeholder

- **WHEN** no session is selected
- **THEN** the Inspector tab shows a placeholder message and does not display an error dialog

#### Scenario: selected run without a trace shows a placeholder

- **WHEN** the selected run has no recorded trace
- **THEN** the Inspector tab shows a placeholder message and does not display an error dialog

## MODIFIED Requirements

### Requirement: TUI degrades gracefully when the server is unreachable

When a poll request fails due to a connection error or timeout, the TUI SHALL mark the server as unreachable in the Health pane and SHALL retain the most recently fetched data in the other panes without crashing. When connectivity is restored on a later poll tick, the TUI SHALL resume updating the panes. The Skills, Permissions, and Dataflow tabs SHALL retain their most recently fetched content during an outage and SHALL NOT blank or crash when a poll yields no snapshot data.

#### Scenario: unreachable server does not crash the TUI

- **WHEN** a poll request fails because the server is unreachable
- **THEN** the Health pane shows a down indicator and the TUI remains running

#### Scenario: recovery resumes updates

- **WHEN** connectivity is restored and a later poll tick succeeds
- **THEN** the panes resume reflecting current server data

#### Scenario: new tabs retain last-good data on outage

- **WHEN** a poll request fails because the server is unreachable after a successful poll has populated the tabs
- **THEN** the Skills, Permissions, and Dataflow tabs retain their most recently fetched content without blanking or crashing

## REMOVED Requirements

### Requirement: TUI renders a four-pane dashboard

**Reason**: Superseded by the tabbed dashboard shell; the single-screen four-pane layout no longer applies once panes are organized into tabs.
**Migration**: The Sessions, Queue, and Health panes now live in the Dashboard tab (see "TUI renders a tabbed dashboard shell"), and the Events drill-down is replaced by the Inspector tab (see "Inspector tab presents the selected run's workflow trace").

### Requirement: Events pane drills down into the selected session

**Reason**: Consolidated into the Inspector tab to avoid maintaining duplicate overlapping views of the same workflow trace.
**Migration**: Use the Inspector tab, which presents the selected run's full workflow trace in execution order with a run header (see "Inspector tab presents the selected run's workflow trace").
