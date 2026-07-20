## ADDED Requirements

### Requirement: Campaign Lifecycle Truth Is Carrier-Bound

ETHOS SHALL derive a campaign execution step's lifecycle legality from its
declared state, OpenSpec carrier home, and closeout record.  An `active`,
`in_progress`, or `landed` step SHALL reference an active carrier under
`openspec/changes/<id>` and SHALL NOT report a `closed` or `retired` closeout.
A `closed` or `retired` step SHALL reference an archived carrier and SHALL
carry terminal closeout state, accepted and candidate heads, and dated
evidence.  A campaign MAY remain `active` with no execution step while its next
step remains `planned`; the reader SHALL expose that next planned step rather
than fabricate an active lane.

#### Scenario: archived carrier is presented as active

- **WHEN** campaign validation reads an execution step whose only carrier is
  under `openspec/changes/archive`
- **THEN** it reports a required
  `campaign_step_active_openspec_archived:<campaign>:<step>` gap
- **AND** it does not treat the campaign topology as a valid active lane

#### Scenario: terminal step lacks archived carrier

- **WHEN** campaign validation reads a `closed` or `retired` step whose carrier
  remains only under `openspec/changes/<id>`
- **THEN** it reports a required
  `campaign_step_terminal_openspec_not_archived:<campaign>:<step>` gap

#### Scenario: campaign awaits a planned successor

- **WHEN** every completed predecessor has terminal closeout and the immediate
  successor remains `planned`
- **THEN** campaign validation accepts the absence of an active execution step
- **AND** `lane_topology.next_planned_step` identifies that successor
- **AND** no active Work Lane is inferred until its carrier and lane exist
