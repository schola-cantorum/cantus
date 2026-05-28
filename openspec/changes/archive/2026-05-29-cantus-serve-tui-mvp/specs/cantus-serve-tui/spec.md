## ADDED Requirements

### Requirement: cantus tui command launches the dashboard client

The cantus CLI SHALL provide a `tui` subcommand that starts a standalone terminal dashboard client connecting over HTTP to a running cantus serve instance. The subcommand SHALL accept a `--url` option defaulting to `http://127.0.0.1:8765`, an `--auth-mode` option whose choices match the serve subcommand (none, bearer, api-key), and a `--poll-interval` option in seconds defaulting to 2.0. When the `cantus[tui]` optional dependencies are not installed, the subcommand SHALL print an actionable message naming the `cantus-agent[tui]` install target and exit with a non-zero status instead of raising a traceback.

#### Scenario: tui subcommand is registered

- **WHEN** `cantus tui --help` is invoked
- **THEN** the process prints usage for the tui subcommand including the --url, --auth-mode, and --poll-interval options

#### Scenario: missing tui extra fails gracefully

- **WHEN** `cantus tui` runs in an environment without the tui optional dependencies installed
- **THEN** the process prints a message naming the cantus-agent[tui] install target
- **AND** exits with a non-zero status without raising a traceback

### Requirement: TUI renders a four-pane dashboard

The TUI SHALL present four panes: a Sessions master list, an Events pane, a Queue pane, and a Health pane. The Sessions master list SHALL be the focus target that drives the contents of the Events pane.

#### Scenario: four panes are present

- **WHEN** the TUI starts and connects to a reachable server
- **THEN** the Sessions, Events, Queue, and Health panes are all rendered

### Requirement: Sessions pane lists recent runs

The Sessions pane SHALL display the runs returned by the introspection sessions slice, one row per run, each showing the run id, source, status, started-at timestamp, and event count. The pane SHALL refresh its rows on each poll tick.

#### Scenario: dispatched run appears in the sessions pane

- **WHEN** a run has been dispatched on the connected server and a poll tick occurs
- **THEN** the Sessions pane shows a row whose source identifies the invoked skill and whose status reflects the run outcome

### Requirement: Events pane drills down into the selected session

The Events pane SHALL display the ordered Action/Observation steps of the run currently selected in the Sessions pane, fetched from the workflow introspection endpoint for that run id. When the selected run has no recorded trace, the Events pane SHALL show a placeholder message rather than an error dialog.

#### Scenario: selecting a session shows its steps

- **WHEN** the user selects a session row whose run has a recorded trace
- **THEN** the Events pane shows that run's steps in execution order

#### Scenario: selected run without a trace shows a placeholder

- **WHEN** the user selects a session row whose run has no recorded trace
- **THEN** the Events pane shows a placeholder message and does not display an error dialog

### Requirement: Queue pane reports per-channel depth

The Queue pane SHALL display the per-channel entries returned by the introspection queues slice, one row per channel, each showing the channel name, kind, and depth. When a channel's depth is null, the pane SHALL render a placeholder marker in place of a number.

#### Scenario: channel depth is shown

- **WHEN** the connected server has an attached channel reporting a depth of two
- **THEN** the Queue pane shows a row for that channel with depth 2

#### Scenario: null depth renders a placeholder

- **WHEN** the connected server has an attached channel whose depth is null
- **THEN** the Queue pane shows a row for that channel with a placeholder marker in place of a number

### Requirement: Health pane summarizes server status

The Health pane SHALL synthesize a status summary from the health endpoint and the introspection roll-up, containing a reachable-or-unreachable indicator, the reported cantus version, the total run count with the per-status counts for running, completed, and error, the maximum observed queue depth, and the effective auth mode. The summary SHALL NOT contain any token or secret value.

#### Scenario: healthy server summary

- **WHEN** the connected server is reachable and reports its version
- **THEN** the Health pane shows an up indicator and the reported cantus version

##### Example: run counts

- **GIVEN** sessions r1(status=completed), r2(status=running), r3(status=error)
- **WHEN** a poll tick refreshes the Health pane
- **THEN** the Health pane shows a total of 3 with running 1, completed 1, and error 1

### Requirement: TUI polls on a configurable interval with manual refresh and pause

The TUI SHALL refresh its data automatically at the configured poll interval. It SHALL provide a keybinding to refresh immediately, a keybinding to toggle pausing and resuming automatic refresh, and a keybinding to quit. While paused, the TUI SHALL NOT issue automatic poll requests until the user resumes.

#### Scenario: pause halts automatic polling

- **WHEN** the user activates the pause keybinding
- **THEN** the TUI stops issuing automatic poll requests until the user resumes

#### Scenario: manual refresh fetches immediately

- **WHEN** the user activates the refresh keybinding
- **THEN** the TUI fetches current data once regardless of the poll-interval timer

### Requirement: TUI authenticates with credentials from the environment

When `--auth-mode` is bearer, the TUI SHALL read the token from the CANTUS_SERVE_BEARER_TOKEN environment variable and send it as an Authorization bearer header. When `--auth-mode` is api-key, the TUI SHALL read the token from the CANTUS_SERVE_API_KEY environment variable and send it as an X-API-Key header. The TUI SHALL NOT display, log, or otherwise reveal the token value.

#### Scenario: bearer token is sent from the environment

- **WHEN** --auth-mode is bearer and CANTUS_SERVE_BEARER_TOKEN is set
- **THEN** each introspection request carries an Authorization bearer header bearing that token

#### Scenario: token value is never rendered

- **WHEN** the TUI runs with a configured token
- **THEN** the token value does not appear in any pane, status line, or error message

### Requirement: TUI degrades gracefully when the server is unreachable

When a poll request fails due to a connection error or timeout, the TUI SHALL mark the server as unreachable in the Health pane and SHALL retain the most recently fetched data in the other panes without crashing. When connectivity is restored on a later poll tick, the TUI SHALL resume updating the panes.

#### Scenario: unreachable server does not crash the TUI

- **WHEN** a poll request fails because the server is unreachable
- **THEN** the Health pane shows a down indicator and the TUI remains running

#### Scenario: recovery resumes updates

- **WHEN** connectivity is restored and a later poll tick succeeds
- **THEN** the panes resume reflecting current server data

### Requirement: TUI issues only read-only requests

The TUI SHALL interact with the server exclusively through HTTP GET requests against the introspection and health endpoints. It SHALL NOT issue any request that mutates server, registry, session, channel, or event-stream state.

#### Scenario: only GET requests are issued

- **WHEN** the TUI performs any data fetch
- **THEN** the issued HTTP request uses the GET method
