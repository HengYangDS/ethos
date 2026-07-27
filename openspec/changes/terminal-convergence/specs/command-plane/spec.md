## ADDED Requirements

### Requirement: Compact Truthful Output
Default command JSON MUST include verdict, summary, gaps, next actions, and artifact references only; status MUST be at most 16 KiB and plan at most 32 KiB for the reference repository fixtures.

#### Scenario: Diagnostic detail exceeds the payload budget
- **WHEN** a command has verbose facts larger than its default payload limit
- **THEN** it writes or identifies a digest-bound artifact and returns a reference instead of embedding the detail

### Requirement: Hard Gaps Cannot Be Green
A hard policy gap MUST force `ok=false`, a blocking or unknown verdict, and non-ready lifecycle summaries.

#### Scenario: Source budget is above the terminal maximum
- **WHEN** current measurement exceeds a hard source budget
- **THEN** status, prove, land, and publish cannot report ready, closed-loop, perfect, or successful states

### Requirement: Status Separates Assurance Planes
Status MUST compactly project required gaps, non-blocking advisories, local proof,
and each profile-declared provider's observation and publication state from
fresh RepositoryFacts and current Attestations. All states MUST use the shared
`pass | block | unknown` algebra, and the projection MUST NOT create a status
ledger or infer one plane from another.

#### Scenario: Local proof passes while hosted evidence is absent
- **WHEN** exact-head local proof is valid but a declared provider has no current
  external-assurance Attestation
- **THEN** status reports local proof as `pass`
- **AND** reports that provider's observation and publication state as `unknown`
- **AND** does not demote missing required hosted evidence to an advisory

#### Scenario: Coordination advice does not block
- **WHEN** a fresh coordination observation is advisory under the active policy
- **THEN** status exposes it separately from `required_gaps`
- **AND** the advisory cannot change a blocking or unknown verdict into `pass`

### Requirement: PlanIR Owns Transition Projection
Plan and proof MUST bind one explicitly selected ChangeContract whenever more
than one active contract exists. External node requirements MUST be present in
repository facts or block the PlanIR.

#### Scenario: Multiple active ChangeContracts exist
- **WHEN** planning or proof is requested without an explicit Change selector
- **THEN** the operation reports `change_contract_ambiguous`
- **AND** `ethos plan --change <id>` and `ethos prove --change <id>` bind the
  selected base ChangeContract digest into PlanIR

### Requirement: OpenSpec Carrier Observation
Public commands SHALL consume owner-native OpenSpec validation and archive
observations and SHALL validate only the terminal carrier set: proposal, design,
tasks, delta specs, ChangeContract, accepted spec identity, proposal intent,
scope, evidence refs, and archiveability. They SHALL NOT inspect a parallel
capability metadata plane or re-export OpenSpec as an ETHOS command root.

#### Scenario: OpenSpec lifecycle is audited
- **WHEN** status or prove evaluates OpenSpec lifecycle state
- **THEN** the result reports owner-native validation and ETHOS carrier readiness

#### Scenario: OpenSpec adapter composes official and ETHOS checks
- **WHEN** prove evaluates the admitted OpenSpec lifecycle gate
- **THEN** the payload includes owner-native status and strict validation
- **AND** it reviews proposal, design, tasks, delta specs, ChangeContract
  validity, accepted `spec.md` identity, exact `subject`, `reuse`, and `change`
  intent, scope, evidence refs, and live-spec diff guards

#### Scenario: OpenSpec adapter does not become a second public command plane
- **WHEN** ETHOS reports an OpenSpec governance gap
- **THEN** the next action uses one of the six public roots or names the exact
  owner-native OpenSpec operation
- **AND** no `ethos openspec` root, alias, wrapper, or fallback is created

#### Scenario: Lifecycle semantics use OpenSpec as carrier
- **WHEN** lifecycle or transition semantics change
- **THEN** an OpenSpec Change records the intent and capability deltas
- **AND** owner-native validation remains carrier validation rather than runtime
  authority

### Requirement: Invalid-State Diagnostic Projection
Status, plan, and prove SHALL explain blocking gaps and advisory signals without
registering a separate explain command or converting diagnostics into lifecycle
state.

#### Scenario: Explain accepts advisory signals without required-gap overclaim
- **WHEN** a public reader receives a non-blocking advisory signal
- **THEN** the payload preserves the original signal and stable gap-or-signal
  field
- **AND** the payload exposes the original advisory separately
- **AND** it classifies the signal into an invalid-state category
- **AND** its wording does not call every explained signal a required gap
- **AND** the taxonomy projection does not become a lifecycle command

#### Scenario: Explain help and docs use gap-or-signal language
- **WHEN** a human or agent reads public command help or the command-plane
  reference
- **THEN** diagnostics are described as governance gaps or advisory signals
- **AND** examples use gap-or-signal language rather than required-gap-only
  wording
- **AND** diagnostic projection remains read-only, not a lifecycle command

### Requirement: Owner-native OpenSpec Change Lookup
ETHOS projections SHALL preserve exact owner-native active and archived Change
identity without adding an archive-query command, alias, redirect, or fallback.

#### Scenario: Logical archive ID resolves uniquely
- **WHEN** owner-native lookup receives a valid logical ID with exactly one
  matching dated archive directory
- **THEN** the projection reports the resolved relative archive carrier path
- **AND** it does not invoke active Change lookup or archive mutation

#### Scenario: Archive query fails closed
- **WHEN** owner-native lookup receives an invalid logical ID, archive directory
  name, no matching archive, or multiple matching archives
- **THEN** the projection reports a distinct required gap
- **AND** it does not choose by date or mutate an archive

#### Scenario: Numeric or temporal logical IDs are rejected
- **WHEN** owner-native lookup receives a numeric-leading ID, terminal-date ID,
  archive directory name, absent ID, or ambiguous logical ID
- **THEN** the projection rejects it as an invalid logical Change ID
- **AND** it requires the date-free logical ID rather than an alias, redirect,
  or fallback lookup

#### Scenario: Archive directory is passed to active selector
- **WHEN** active Change selection receives the exact name of a dated archive
  directory
- **THEN** it reports that an archive directory is not an active identifier
- **AND** it does not treat the archived carrier as an active Change

## MODIFIED Requirements

### Requirement: Public Command Plane
ETHOS SHALL expose exactly six public root commands: `adopt`, `status`, `plan`,
`prove`, `land`, and `publish`. `status` SHALL be the single bounded reader;
the other five roots SHALL own adoption, planning, proof, integration, and
publication respectively. Maintainer-only `lane` and `hook` operations SHALL
remain hidden from root help and SHALL NOT become parallel public products.

#### Scenario: Cyclopts exposes the terminal root surface
- **WHEN** the root CLI help is rendered
- **THEN** it exposes exactly the six public roots
- **AND** `status` returns role, authority, required gaps, advisories, local
  proof, per-provider states, coordination facts, and next actions from the same
  verdict owners used by lifecycle transitions
- **AND** `lane` and `hook` remain callable only as hidden operational groups

#### Scenario: PlanIR is the single transition projection
- **WHEN** `ethos plan --json` compiles the selected ChangeContract, repository
  facts, and declared nodes
- **THEN** it returns one deterministic `plan_ir`
- **AND** no parallel workflow runtime or command-family read model is emitted

#### Scenario: Default payloads stay bounded
- **WHEN** `ethos status --json` or `ethos plan --json` exceeds its declared
  default payload budget
- **THEN** the command preserves verdict, summary, required gaps, and next actions
- **AND** oversized detail is replaced by a digest-bound artifact reference
- **AND** no alternate reader command or truth source is introduced

### Requirement: Prove Is The Singular Quality Execution Surface
All repository quality, policy, projection, adapter, documentation, and
conformance checks SHALL be selected through admitted gate IDs on
`ethos prove`. `system/gates.toml` SHALL bind each gate directly to its semantic
provider or owner-native command without another ETHOS command layer.

#### Scenario: One focused gate is requested
- **WHEN** `ethos prove --execute --gate <gate-id> --json` runs
- **THEN** the declared provider or owner command executes directly
- **AND** proof evidence records the gate ID, implementation identity, verdict,
  and diagnostics
- **AND** no capability-specific public command is registered or invoked

#### Scenario: Full repository proof is requested
- **WHEN** `ethos prove --full --json` runs
- **THEN** ETHOS compiles the complete admitted gate graph and its dependency
  closure
- **AND** unadmitted capability checks do not create commands or proof authority

### Requirement: Retired Family Command Vocabulary
The root identifiers `orient`, `report`, `doctor`, `explain`, `docs`, `audit`,
`openspec`, `fleet`, `intake`, `rules`, `assistants`, `campaign`, `parity`,
`quality`, and `playbooks` are retired. Legacy family prefixes `governance`,
`workspace`, `agent`, `project`, `kernel`, and `node` are also invalid command
roots. None of these identifiers SHALL be registered, documented as a current
command, emitted as a next action, or retained through an alias, wrapper, or
fallback.

#### Scenario: Retired capability command appears
- **WHEN** root dispatch, governed documentation, generated command metadata, or
  a lifecycle result contains a retired root identifier as an ETHOS command
- **THEN** command-surface validation reports a required gap or dispatch rejects
  the command
- **AND** remediation points to one of the six public roots or an admitted gate

### Requirement: Semantic Lane Lifecycle Groups
Work Lane lease, handoff, linked retirement, candidate maintenance, and hook
admission mechanics SHALL remain under the hidden `lane` and `hook` operational
groups. Their operations SHALL call one semantic owner directly and SHALL NOT be
promoted, aliased, or re-exported as public roots.

#### Scenario: retirement commands are grouped
- **WHEN** a maintainer invokes an exact hidden operation
- **THEN** retirement exposes only `ethos lane retire landed` and
  `ethos lane retire superseded`
- **AND** Lease lifecycle remains under `ethos lane lease` and holder transfer
  under `ethos lane handoff`
- **AND** no Resolution, unbound-retirement, ownerless, or reconciliation command
  is registered, documented, or emitted as a next action
- **AND** every operation remains generation-bound, admission-controlled, and
  scoped to its lane or hook owner
- **AND** root help and generated public command metadata still expose only the
  six public roots

## REMOVED Requirements

### Requirement: Self OpenSpec Lifecycle Mode

**Reason**: OpenSpec lifecycle operations belong to the official OpenSpec CLI,
not an ETHOS public root.

**Migration**: Use owner-native OpenSpec commands; ETHOS `plan`, `prove`, and
`land` consume their results through the admitted OpenSpec adapter.

**Replacement**: OpenSpec Carrier Observation

### Requirement: ETHOS OpenSpec adapter remains under one command plane

**Reason**: Re-exporting OpenSpec through ETHOS creates a second owner for the
official lifecycle and contradicts the six-root command plane.

**Migration**: Use owner-native OpenSpec list, status, validation, and archive
operations. ETHOS consumes carrier state without re-exposing those operations.

**Replacement**: OpenSpec Carrier Observation

### Requirement: Explain Command Projects Invalid-State Signals

**Reason**: Invalid-state detail is part of lifecycle gaps and proof diagnostics,
not a standalone command product.

**Migration**: Read gaps and next actions from `ethos status --json`,
`ethos plan --changed --json`, or `ethos prove --json`.

**Replacement**: Invalid-State Diagnostic Projection

### Requirement: OpenSpec archive query uses logical Change IDs

**Reason**: Archive lookup and mutation are official OpenSpec responsibilities.

**Migration**: Use `openspec status --change <id> --json` for active state and
`openspec archive <id> --yes --json` for owner-native archival.

**Replacement**: Owner-native OpenSpec Change Lookup

### Requirement: Active Change selection excludes archive directory names

**Reason**: Active Change selection is owned by the official OpenSpec CLI and
does not require an ETHOS selector.

**Migration**: Supply the logical Change ID to owner-native OpenSpec status or
archive operations.

**Replacement**: Owner-native OpenSpec Change Lookup
