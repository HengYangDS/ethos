## MODIFIED Requirements

### Requirement: Campaign-terminal protected publication admission

When a campaign manifest declares `publication.mode = "campaign_terminal"`,
ETHOS SHALL report the campaign's structural publication validity separately
from its terminal-progress advisory state. A malformed or unbound publication
contract SHALL remain a protected-push blocker. Active campaign state,
unretired steps, terminal source-budget non-attainment, active temporary debt,
and source-budget progress SHALL remain explicit advisory state; they SHALL NOT
block an ordinary non-force protected remote update after executed local proof
and governed candidate/accepted closeout. Receiving-plane branch protection
remains authoritative and is not replaced by this local gate.

#### Scenario: Non-terminal compression campaign blocks protected push

- **GIVEN** an active `campaign_terminal` campaign has planned, active, or
  non-retired steps, unmet terminal source budget, or active temporary debt
- **AND** the pushed `dev` or `main` head has executed local proof and governed
  candidate/accepted closeout
- **WHEN** pre-push admission evaluates a configured protected destination
- **THEN** campaign progress SHALL appear in `campaign_publication.advisory_gaps`
- **AND** it SHALL add no campaign-progress item to pre-push `required_gaps`
- **AND** pushes to `work/*` remain governed by ordinary remote branch policy.

#### Scenario: Terminal campaign admits ordinary protected-push checks

- **GIVEN** every active `campaign_terminal` campaign is closed, every step is
  archive-complete and retired, terminal source-budget targets are met, and no
  temporary debt record remains active
- **WHEN** pre-push admission evaluates a protected destination
- **THEN** the campaign publication report SHALL add no required or advisory gap
- **AND** identity, executed-proof, candidate-topology, reconciliation, and
  provider-specific checks SHALL remain independently enforced.

#### Scenario: Per-Change temporary debt does not block local progression

- **GIVEN** a `campaign_terminal` campaign is active and source-budget
  enforcement is `campaign_terminal` with declared unexpired temporary debt
- **WHEN** a bounded Change completes its local proof and closeout lifecycle
- **THEN** campaign reporting SHALL expose the debt as terminal-progress advice
- **AND** it SHALL not classify the Change or an ordinary protected push as
  blocked solely because the campaign terminal target is not yet met.

#### Scenario: Campaign terminal budget keeps debt lifecycle local

- **GIVEN** source-budget enforcement is `campaign_terminal`
- **WHEN** a local Change increases effective source while declared debt remains
  within its maximum and active lifecycle
- **THEN** source-budget validation SHALL not block that local Change solely for
  current-size or terminal-target non-attainment
- **AND** invalid policy, debt-cap overflow, expired debt, and stale debt SHALL
  remain local blocking gaps
- **AND** full proof and terminal compression closeout SHALL still require
  terminal targets and no active debt.

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
  structural publication admission or terminal-progress advice.

#### Scenario: Hook evaluates the named remote

- **WHEN** the Git pre-push hook receives `github` as its remote name
- **THEN** both its base and enriched push-admission evaluations SHALL receive
  `remote_name = "github"`
- **AND** emitted remote diagnostics and branch admission SHALL describe GitHub,
  not the default `origin`.
