## ADDED Requirements

### Requirement: Bounded Coordination Aggregate Detail State

ETHOS SHALL derive coordination aggregate detail state from the reader mode
selected by the caller, not from the number or contents of visible foreign Work
Lane rows.

#### Scenario: Empty bounded inventory remains deferred

- **GIVEN** no foreign Work Lane is visible
- **WHEN** `workspace_status` runs with foreign path-scope expansion disabled
- **THEN** coordination `detail_state` SHALL be `deferred`
- **AND** `dirty_foreign_work_lane_count`, `overlap_count`,
  `unknown_scope_count`, `closeout_residue_count`, and
  `dirty_closeout_residue_count` SHALL be `null`
- **AND** observable foreign-lane and lease counts SHALL remain available.

#### Scenario: Empty full inventory remains exact

- **GIVEN** no foreign Work Lane is visible
- **WHEN** `workspace_status` runs in its full default mode
- **THEN** coordination `detail_state` SHALL be `exact`
- **AND** `dirty_foreign_work_lane_count`, `overlap_count`,
  `unknown_scope_count`, `closeout_residue_count`, and
  `dirty_closeout_residue_count` SHALL all be zero.

## MODIFIED Requirements

### Requirement: Work Lane Coordination Read Model

ETHOS SHALL treat a Lane Lease as ignored, one-writer coordination within one Git
common directory. The lease SHALL identify a concrete holder and generation but
SHALL NOT be an identity assertion, capability grant, filesystem fence,
cross-host lock, or repository truth. Reader output SHALL be a
non-authoritative action preview rather than a reusable permission. Bounded
readers SHALL preserve the caller-selected `deferred` state even when no foreign
Work Lane rows are visible; full readers SHALL report `exact` only after the
full foreign coordination inventory has been computed.

#### Scenario: foreign lane preview remains observe-only

- **WHEN** status or orientation reports a linked foreign Work Lane
- **THEN** its action preview lists `observe` as the only candidate action and
  blocks `write`, `land`, and `retire`
- **AND** it states `mints_authority=false` and `recheck_required=true`
- **AND** actual mutation re-evaluates the exact current request
- **AND** legacy actor-capability fields cannot be replayed as authority and are
  retired after client migration.

#### Scenario: bounded readers defer foreign path scopes

- **WHEN** a bounded status, planning, proof, landing, publication, or scorecard
  reader needs local state and aggregate lane signals but not a coordination
  inventory
- **THEN** ETHOS MAY defer foreign Work Lane path scopes instead of running one
  history diff per visible foreign lane
- **AND** each deferred lane remains explicitly marked `scope_state=deferred`
  while retaining its non-authoritative observe-only coordination state
- **AND** the reader preserves observable lane count and lease signals without
  inferring path overlap, branch relation, dirty foreign contents, or retirement
  readiness
- **AND** full `lane status` and mutation admission retain exact foreign path
  scope computation before making any coordination decision.

#### Scenario: projection preserves observed coordination detail state

- **WHEN** bounded status or orientation projects a coordination observation
- **THEN** its summary and coordination payload SHALL both expose
  `detail_state=deferred`
- **AND** counts requiring foreign-path inspection SHALL remain `null` even when
  no foreign Work Lane row is visible
- **AND** a full coordination inventory MAY expose `detail_state=exact` and
  integer detail counts only after computing that full inventory
- **AND** neither state grants foreign Work Lane mutation authority.
#### Scenario: bounded-reader regression debt is explicit and temporary

- **WHEN** the bounded status read model introduces a focused regression carrier
  before its full and bounded fixtures can share a smaller harness
- **THEN** any source-budget allowance names that exact carrier, owner,
  replacement, and deletion wave
- **AND** its allowance is limited to the measured temporary carrier cost
- **AND** the ledger's aggregate maximum equals the sum of its append-only
  records
- **AND** later fixture consolidation removes the allowance rather than making
  it permanent.

#### Scenario: normalized lease has one concrete current holder

- **WHEN** a lane lease is created, renewed, resumed, or handed off
- **THEN** it binds a random local lane-incarnation ID, lease ID, structured
  holder reference, epoch, issuance, renewal, expiry, and optional claim/scope
- **AND** one lane incarnation has at most one current writer holder
- **AND** renewal preserves holder, lease ID, and epoch while handoff changes
  holder and increments epoch
- **AND** the prior holder resumes an expired lease only with the old generation,
  unchanged expected head, and no contrary accepted judgment
- **AND** expiry, provider labels, missing state, or ambiguity never authorize
  another holder or cleanup.

#### Scenario: lease generation detects but does not claim hard fencing

- **WHEN** an invocation's expected holder, lease ID, epoch, or head is stale
- **THEN** normal ETHOS mutation paths reject or flag it
- **AND** handoff requires offer, acceptance, and holder quiescence
- **AND** ETHOS does not claim to stop an already-running or bypassing same-user
  filesystem process
- **AND** uncertainty or residue blocks integration until inspected.

#### Scenario: lease and Git lifecycle is crash-consistent

- **WHEN** a lane operation spanning Git, filesystem, and SQLite partially fails
- **THEN** ETHOS reports the exact repair-required state and verifies
  postconditions on idempotent retry
- **AND** normal authoring remains blocked until required Git and sole-lease
  postconditions hold
- **AND** ETHOS does not claim cross-store atomicity or silently choose among
  duplicate legacy leases.

#### Scenario: legacy adoption and cleanup resist replay

- **GIVEN** a legacy or recreated lane lacks trusted normalized state
- **WHEN** it is adopted or exceptionally cleaned
- **THEN** a provable current holder may normalize only that same holder/head
- **AND** other cases require an accepted maintainer decision pre-binding the
  exact target observation and a new local lane-incarnation ID
- **AND** cleanup binds that incarnation digest so a same-named branch or another
  clone cannot replay the decision
- **AND** missing legacy incarnation evidence blocks destructive cleanup rather
  than creating a global repository or Agent registry.

#### Scenario: cross-host handoff creates destination-local coordination

- **WHEN** work moves to another clone or Git common directory
- **THEN** transfer binds content-addressed Git state and a digest-bound context
  or recovery carrier, not the source SQLite lease
- **AND** dirty tracked/untracked work is committed or explicitly preserved, not
  stashed or left in chat
- **AND** the destination creates a new local lane and acknowledges it before the
  source revokes its writer lease or retires its observe-only copy
- **AND** neither side claims a distributed lease or shared session identity.
