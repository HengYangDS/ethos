## MODIFIED Requirements

### Requirement: Official OpenSpec Lifecycle Adapter

The official OpenSpec CLI SHALL own validation and archival for the selected
OpenSpec profile. ETHOS SHALL consume its native observations and distinguish
source acceptance from whole-Change completion. An active Change SHALL remain
the sole tracked intent and progress carrier during integration and delivery.

#### Scenario: official active state is malformed or ambiguous

- **WHEN** official `list --json` has an invalid shape, an absent requested Change
  or several implicitly selectable Changes
- **THEN** ETHOS blocks with the precise missing or ambiguous fact
- **AND** it does not select by timestamp, directory order or a private task parser.

#### Scenario: source is ready while delivery tasks remain

- **WHEN** one valid active Change has exact source proof and current integration
  authority, but its delivery tasks remain incomplete
- **THEN** source integration and accepted closeout may proceed
- **AND** those tasks remain incomplete in the same active Change.

#### Scenario: a completed Change remains active

- **WHEN** official progress reports all declared tasks complete before archive
- **THEN** source acceptance remains valid and archive is eligible
- **AND** only the native archive effect moves the active carrier into history.

#### Scenario: archive is requested before obligations are complete

- **WHEN** an author requests archive with remaining official Change tasks
- **THEN** ETHOS rejects archive with `openspec_change_incomplete:<change>`
- **AND** neither task progress nor Git refs is rewritten to manufacture completion.

#### Scenario: historical archives use an older shape

- **WHEN** a historical archive contains obsolete names, metadata or task layout
- **THEN** ETHOS preserves it as non-authorizing history
- **AND** current admission does not replay its historical workflow.

#### Scenario: archive updates a declared projection input

- **WHEN** official archive changes canonical source bytes used by a declared
  source-binding projection
- **THEN** the same Git effect includes only the exact derived binding update
- **AND** the authored graph meaning and unrelated files remain unchanged.

#### Scenario: archive projection is stale or altered

- **WHEN** the declared projection does not match its preimage source or the
  proposed postimage changes more than the exact derived bindings
- **THEN** ETHOS rejects the effect before CAS
- **AND** native-operation changes are compensated without erasing a supplied
  authoring overlay.
