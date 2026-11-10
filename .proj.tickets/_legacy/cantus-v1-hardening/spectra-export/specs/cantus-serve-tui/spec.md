## MODIFIED Requirements

### Requirement: Inspector tab presents the selected run's workflow trace

The Inspector tab SHALL display the ordered Action/Observation steps of the run currently selected in the Dashboard Sessions master list, fetched from the workflow introspection endpoint for that run id, rendered in execution order with each step's full summary. The Inspector tab SHALL show a header that identifies the selected run. When no run is selected, the Inspector tab SHALL show a placeholder message rather than an error dialog.

The Inspector tab SHALL distinguish two distinct "nothing to show" cases for a selected run and SHALL render a different placeholder message for each: (a) when the workflow introspection endpoint reports that the run is not found or has been evicted (HTTP 404, surfaced to the widget as an absent data payload), the Inspector SHALL show a placeholder indicating the run was not found or has been evicted; (b) when the endpoint returns a payload whose step list is empty (the run is recorded but has no steps yet), the Inspector SHALL show a placeholder indicating the run is recorded but has no steps. The two placeholder messages SHALL NOT be identical. In neither case SHALL the Inspector display an error dialog.

#### Scenario: selecting a session shows its trace in the Inspector

- **WHEN** the user selects a session row whose run has a recorded trace and views the Inspector tab
- **THEN** the Inspector tab shows that run's steps in execution order
- **AND** shows a header identifying the selected run

#### Scenario: no selection shows a placeholder

- **WHEN** no session is selected
- **THEN** the Inspector tab shows a placeholder message and does not display an error dialog

#### Scenario: evicted or unknown run (404) shows a not-found placeholder

- **WHEN** the selected run's workflow endpoint returns HTTP 404 (surfaced as an absent data payload)
- **THEN** the Inspector tab shows a placeholder indicating the run was not found or has been evicted
- **AND** does not display an error dialog

#### Scenario: recorded run with empty steps (200) shows a distinct no-steps placeholder

- **WHEN** the selected run's workflow endpoint returns a payload whose step list is empty
- **THEN** the Inspector tab shows a placeholder indicating the run is recorded but has no steps
- **AND** that placeholder message differs from the not-found / evicted placeholder
- **AND** does not display an error dialog
