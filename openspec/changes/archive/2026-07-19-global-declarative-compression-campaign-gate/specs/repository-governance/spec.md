## ADDED Requirements

### Requirement: Campaign-terminal protected publication admission

When a campaign manifest declares `publication.mode = "campaign_terminal"`,
ETHOS SHALL treat that campaign as the local protected-publication admission
boundary.
Each contained OpenSpec Change MAY complete its normal local Work Lane,
candidate, accepted-root, and archive lifecycle while the campaign remains
non-terminal. ETHOS SHALL make its pre-push client block protected destinations
until every such active campaign is terminal. Receiving-plane branch protection
remains authoritative and is not replaced by this local gate.

#### Scenario: Non-terminal compression campaign blocks protected push

- **GIVEN** an active `campaign_terminal` campaign has planned, active, or
  non-retired steps, unmet terminal source budget, or active temporary debt
- **WHEN** pre-push admission evaluates `dev`, `main`, `candidate/dev`, or a
  `submit/*` destination
- **THEN** the admission SHALL be blocked with the campaign publication gap
- **AND** Work Lane-local proof and local candidate/accepted closeout remain
  governed by their existing reducers
- **AND** pushes to `work/*` remain outside this campaign publication gate.

#### Scenario: Terminal campaign admits ordinary protected-push checks

- **GIVEN** every active `campaign_terminal` campaign is closed, every step is
  archive-complete and retired, terminal source-budget targets are met, and no
  temporary debt record remains active
- **WHEN** pre-push admission evaluates a protected destination
- **THEN** the campaign publication gate SHALL add no required gap
- **AND** identity, executed-proof, candidate-topology, reconciliation, and
  provider-specific checks SHALL remain independently enforced.

#### Scenario: Per-Change temporary debt does not block local progression

- **GIVEN** a `campaign_terminal` campaign is active and source-budget
  enforcement is `campaign_terminal` with declared unexpired temporary debt
- **WHEN** a bounded Change completes its local proof and closeout lifecycle
- **THEN** campaign reporting SHALL state that remote publication is deferred
  until terminal readiness
- **AND** it SHALL not classify the Change as locally blocked solely because
  the campaign terminal target is not yet met.

#### Scenario: Campaign terminal budget keeps debt lifecycle local

- **GIVEN** source-budget enforcement is `campaign_terminal`
- **WHEN** a local Change increases effective source while declared debt remains
  within its maximum and active lifecycle
- **THEN** source-budget validation SHALL not block that local Change solely for
  current-size or terminal-target non-attainment
- **AND** invalid policy, debt-cap overflow, expired debt, and stale debt SHALL
  remain local blocking gaps
- **AND** campaign terminal publication SHALL still require terminal targets and
  no active debt.

#### Scenario: Invalid Campaign declaration fails closed

- **GIVEN** a Campaign TOML file exists but violates
  `system/schemas/kernel/campaign.schema.json`
- **WHEN** Campaign status or protected-publication admission reads the manifest
- **THEN** the reader SHALL expose a `campaign_manifest_schema_invalid` gap
- **AND** protected publication SHALL be blocked instead of treating the
  Campaign as unconfigured.

#### Scenario: Campaign action commands remain external

- **WHEN** Campaign publication projection selects local continuation or
  protected publication
- **THEN** the domain projection SHALL return a stable action identifier
- **AND** CLI command text SHALL be resolved through `system/commands.toml`
- **AND** Python SHALL NOT encode a Campaign name, provider topology, or parallel
  action vocabulary.

#### Scenario: Filtered Campaign status preserves repository scope

- **WHEN** `ethos campaign status --campaign <id> --json` selects one Campaign
- **THEN** `data.campaigns` SHALL contain the selected Campaign view
- **AND** `data.publication.scope` SHALL remain `repository`
- **AND** filtering SHALL NOT omit another Campaign or source-budget binding from
  protected-publication admission.

## MODIFIED Requirements

### Requirement: Campaign Lifecycle Truth Is Carrier-Bound

ETHOS SHALL derive a campaign execution step's lifecycle legality from its
declared state, OpenSpec carrier home, and closeout record. An `active` or
`in_progress` step SHALL reference an active carrier under
`openspec/changes/<id>` and SHALL NOT report terminal closeout. An `archive_ready` or
`landed` step SHALL reference an archived carrier while closeout remains
non-terminal. A `closed` or `retired` step SHALL reference an archived carrier
and SHALL carry terminal closeout state, accepted and candidate heads, and dated
evidence. A campaign MAY remain `active` with no execution step while its next
step remains `planned`; the reader SHALL expose that next planned step rather
than fabricate an active lane.

#### Scenario: archived carrier is presented as active

- **WHEN** campaign validation reads an `active` or `in_progress` step whose only
  carrier is under `openspec/changes/archive`
- **THEN** it reports a required
  `campaign_step_active_openspec_archived:<campaign>:<step>` gap
- **AND** it does not treat the campaign topology as a valid active lane.

#### Scenario: archived carrier awaits land

- **GIVEN** the official OpenSpec archive operation has moved the current Change
  under `openspec/changes/archive`
- **WHEN** its Campaign step declares `state = "archive_ready"` with non-terminal
  closeout
- **THEN** Campaign validation SHALL accept the truthful archive-before-land
  intermediate state
- **AND** the step SHALL remain non-terminal until candidate and accepted
  closeout facts exist.

#### Scenario: pre-land state still references an active carrier

- **WHEN** an `archive_ready` or `landed` step still resolves only under
  `openspec/changes/<id>`
- **THEN** Campaign validation SHALL report
  `campaign_step_preland_openspec_not_archived:<campaign>:<step>`.

#### Scenario: terminal step lacks archived carrier

- **WHEN** campaign validation reads a `closed` or `retired` step whose carrier
  remains only under `openspec/changes/<id>`
- **THEN** it reports a required
  `campaign_step_terminal_openspec_not_archived:<campaign>:<step>` gap.

#### Scenario: campaign awaits a planned successor

- **WHEN** every completed predecessor has terminal closeout and the immediate
  successor remains `planned`
- **THEN** campaign validation SHALL accept the absence of an active execution
  step
- **AND** `lane_topology.next_planned_step` SHALL identify that successor
- **AND** no active Work Lane SHALL be inferred until its carrier and lane exist.
