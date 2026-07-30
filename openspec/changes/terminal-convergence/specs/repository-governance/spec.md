## ADDED Requirements

### Requirement: Lossless Campaign Intent Closure
Campaign refinement SHALL preserve every accepted independent obligation under
one current semantic owner without creating a conversation ledger, parallel
task store, or compatibility surface. Within the same authority and scope, the
latest explicit ruling SHALL supersede earlier conflicting guidance.

#### Scenario: planning artifacts are replaced
- **WHEN** proposal, design, specification, or task carriers are substantially rewritten
- **THEN** every previously accepted obligation is mapped to a current requirement,
  stable task, acceptance condition, and verifier, or receives an explicit
  rejection, deferral, or supersession reason
- **AND** completed tasks retain their identity and commit or proof evidence
- **AND** phase-local coordinates stay continuous while obligation identity is
  preserved through explicit predecessor and disposition mappings
- **AND** coordinates are not silently reused or renumbered to reset progress
- **AND** unmapped meaning or unresolved contradiction produces `model_gap` and
  blocks carrier retirement and campaign closeout.

#### Scenario: a later explicit decision conflicts with an earlier decision
- **WHEN** both decisions have the same authority, subject, and scope
- **THEN** the later decision is current
- **AND** the earlier decision remains non-authorizing history
- **AND** projections and execution plans cannot silently restore the earlier decision.

#### Scenario: a campaign reports progress
- **WHEN** campaign progress is projected
- **THEN** it reports completed foundations, the single current critical-path
  task, remaining phase exits, and evidence bindings separately
- **AND** elapsed time, analysis, or repeated gate execution without a verified
  terminal-state delta is not reported as implementation progress.

#### Scenario: historical task identity is audited
- **WHEN** the campaign task carrier is compared with its declared history cutover
- **THEN** an existing obligation body is immutable and completion may only advance
- **AND** a removed, reset, or pre-cutover-reused identity has an explicit
  disposition, current task, and evidence or ruling in the existing design
- **AND** a normalized coordinate has an explicit predecessor while any older
  obligation sharing that coordinate resolves to an explicit successor set
- **AND** an older completed obligation resolves to at least one completed
  Foundation identity
- **AND** an unmapped identity produces `model_gap` and blocks closeout.

#### Scenario: a superseded feedback carrier is retired
- **WHEN** the terminal design structurally maps every accepted feedback ID and
  every independent fact-boundary constraint to a current task and semantic
  owner or explicit absence reason
- **THEN** the superseded carrier is deleted from the current documentation and
  repository-audit surfaces
- **AND** Git history remains non-authorizing evidence of the retired text.

#### Scenario: the tracked carrier inventory is total and non-overlapping
- **WHEN** the cutover disposition is checked against the current tracked tree
- **THEN** every tracked path resolves through the ordered selector table to one
  carrier family
- **AND** an uncovered path or overlap outside the declared final remainder is
  `model_gap` and blocks carrier retirement.

#### Scenario: self-profile tasks remain a bounded execution carrier
- **WHEN** ETHOS reads this Change's task projection
- **THEN** it treats those tasks as the ETHOS self-profile campaign execution
  carrier only
- **AND** stable task identity and completion evidence preserve execution
  continuity
- **AND** no task file, progress field, or campaign projection becomes a generic
  product task database, lifecycle runtime, or authorization source.

### Requirement: Exact Work Lane Lifecycle Effects
Routine coordination SHALL remain a local projection. Exceptional repository-semantic effects SHALL require exact selected Commitment, fresh Facts, explicit holder or authorized takeover, CAS preconditions, post-observation, and an Attestation; generic cleanup SHALL never infer authority.

#### Scenario: routine lifecycle remains local

- **WHEN** a lease is acquired, renewed, resumed, locally handed off, expires, or
  the same holder retires a clean mechanically proven landed lane
- **THEN** ETHOS uses ignored local coordination and postcondition receipts
- **AND** no tracked historical Chronicle record is required.

#### Scenario: an authorized Lease takeover changes one holder exactly

- **GIVEN** an authorization binds one branch, exact HEAD, lane incarnation and
  Lease generation, current dirty-content digest, target actor, and source state
  of `quiesced` or `source_lost`
- **WHEN** the target actor executes takeover against fresh Facts
- **THEN** one full-row Lease compare-and-swap changes the holder, increments the
  epoch, preserves the bound branch, HEAD, and content, and emits an exact effect
  Attestation
- **AND** `source_lost` remains an explicit unknown-quiescence boundary rather
  than being reported as a normal handoff
- **AND** drift in the branch, HEAD, generation, dirty-content digest, target
  actor, source-state authorization, or CAS precondition produces zero Git,
  filesystem, and Lease effect.

#### Scenario: exceptional cleanup consumes prior accepted judgment

- **WHEN** orphan recovery, foreign retirement, non-mechanical supersession,
  disputed handoff, preserve, block, or irreversible deletion is requested
- **THEN** a separate owned governance Work Lane has already promoted a
  valid Attestation binding policy, evidence, exact head, lane-incarnation
  digest, disposition, recovery plan, and target-observation digest
- **AND** cleanup recomputes the mutable target facts before its first
  destructive step
- **AND** any mismatch blocks cleanup and requires a new decision
- **AND** the decision authorizes an effect while postconditions alone prove what
  was actually removed.

#### Scenario: dirty or unknown work is preserved by default

- **WHEN** lane ownership, lease state, tracked/untracked contents, or recovery
  status is dirty, missing, ambiguous, or unknown
- **THEN** ETHOS preserves or blocks the lane instead of automatically deleting
  it
- **AND** irreversible deletion requires an accepted decision proving the exact
  target and why preservation is impossible or no longer required.

#### Scenario: break-glass reconciles after emergency action

- **GIVEN** a predeclared break-glass Commitment binds verified maintainer
  identity, exact target/head, reason, blast radius, expiry, preservation
  default, and postcondition plan
- **WHEN** an emergency command independently verifies those facts and acts
  before a new judgment Attestation can be issued
- **THEN** it emits a digest-bound receipt and blocks later integration and
  publication
- **AND** a separate governance Work Lane promotes post-hoc judgment and
  reconciles residue before the block clears
- **AND** a self-supplied flag or holder string is insufficient.

#### Scenario: exceptional lane handoff is attested

- **GIVEN** a Work Lane handoff cannot be resolved by the normal local
  offer/accept protocol or becomes disputed
- **WHEN** an accepted exceptional judgment resolves the handoff
- **THEN** ETHOS records an Attestation with predicate
  `lane_resolution/handoff` binding the prior and next holder observations,
  evidence, exact head, lane-incarnation digest, and result
- **AND** routine local handoff remains ignored coordination and does not require
  tracked historical Chronicle telemetry
- **AND** the Attestation does not replace the active destination-local Lane Lease.

#### Scenario: orphan audit produces a decision, not a persistent orphan state

- **GIVEN** a Work Lane has missing, stale, ambiguous, or legacy holder evidence
- **WHEN** ETHOS audits the lane for exceptional closeout or cleanup
- **THEN** orphan-like facts remain observations requiring a separate accepted
  resolution decision before destructive action
- **AND** the durable outcome records `retire`, `preserve`, `block`, `handoff`, or
  `break_glass` together with exact target and recovery evidence
- **AND** dirty or owner-unknown lanes are preserved or blocked rather than
  automatically deleted.

#### Scenario: clean ownerless diverged source retires after semantic absorption

- **GIVEN** one clean ownerless source Work Lane has diverged because its
  historical evidence and carrier bytes differ from an independently accepted
  current-baseline implementation of its useful behavior
- **AND** a target-specific valid Attestation binds its exact ref,
  exact source head, semantic basis, recovery plan, and `lane_resolution/retire`
  policy
- **WHEN** the native resolver records and applies a fresh decision for that
  exact linked source with break-glass and irreversible confirmation
- **THEN** it SHALL re-observe the source before effect and emit a receipt after
  the exact retirement
- **AND** tree inequality, a missing lease, a preservation package, or an
  inventory entry alone SHALL NOT authorize retirement
- **AND** the authority SHALL NOT extend to another lane, a valid lease, remote
  mutation, or a hosted-provider claim.

## REMOVED Requirements

### Requirement: Productized OpenSpec carrier governance
**Reason**: lifecycle ownership moves to `adapters / Official OpenSpec Lifecycle
Adapter`; repository governance owns only self-profile selection and exact
transition effects.

### Requirement: Productized OpenSpec Substrate
**Reason**: OpenSpec is optional profile capability, not a universal repository
governance substrate.

### Requirement: OpenSpec customization stays official-compatible
**Reason**: official syntax, validation, completion, and archive semantics are
owned once by the lifecycle adapter; ETHOS-specific Commitment and scope checks
remain downstream consumers.

### Requirement: Official OpenSpec goal metadata is lifecycle-compatible
**Reason**: accepted official metadata needs no parallel ETHOS compatibility
requirement or historical parser.

## MODIFIED Requirements

### Requirement: Contextual Authority Resolution
Authority and currentness SHALL resolve contextually by subject, predicate,
scope, plane, validity, and exact bindings. No global rank, current pointer,
directory status, graph, or manual index decides it.

#### Scenario: independent planes report different states
- **WHEN** local proof passes while a configured forge has no hosted Attestation
- **THEN** local proof is current only for its local plane and hosted state remains unknown

### Requirement: Work Lane Coordination Read Model
Worktree families, lanes, leases, handoffs, inboxes, queues, records, and dashboards SHALL be resource facts or derived projections; they SHALL not own intent, task, campaign, or currentness.

#### Scenario: a Worktree Family is projected

- **WHEN** coordination groups Work Lanes for one bounded objective
- **THEN** the Family identity binds repository identity, a stable family key,
  declared coordination scope, and current policy without equating the Family to
  one Commitment
- **AND** every member binds its lane-incarnation ID, branch, exact HEAD, Lease
  generation, scope relation, and disposition
- **AND** the canonical head remains absent until an exact selection Attestation
  and candidate compare-and-swap establish it.

#### Scenario: Family members cooperate, compete, absorb, and retire

- **WHEN** current member scopes and acceptance conditions are resolved
- **THEN** disjoint members may cooperate while overlapping alternatives compete
  under the same acceptance conditions
- **AND** selection absorbs every accepted unique semantic delta into the
  canonical result with evidence
- **AND** a member becomes retireable only after its delta is absorbed or proved
  void, its required preservation exists, and no active Lease or consumer remains.

#### Scenario: an exact leased successor retires its absorbed source

- **GIVEN** one clean linked source member has no Lease
- **AND** the current checkout is another Work Lane whose exact HEAD contains the
  source HEAD as an ancestor and whose Lease is valid and bound to the invoking actor
- **WHEN** `retire superseded` binds both exact HEADs and applies one transaction
- **THEN** ETHOS preserves the accepted and successor refs through compare-and-swap,
  removes only the source worktree and ref, and retains the successor Lease
- **AND** a dirty source, a valid, expired, or unknown source Lease, a stale or
  dirty successor, a holder mismatch, or non-ancestral history blocks before effect.

#### Scenario: a shared inbox is rebuilt and consumed

- **WHEN** a collaboration inbox is projected from selected Commitments, Git and
  Lease Facts, handoff observations, Attestations, gaps, and next actions
- **THEN** a stable semantic item digest deduplicates equivalent inputs and the
  projection can be deleted and rebuilt without meaning loss
- **AND** acknowledgement binds the actor and observed item digest without
  consuming the item
- **AND** consumption binds the exact accepted result, effect, or superseding
  Attestation
- **AND** conflicting current inputs remain one explicit conflict and block
  consumption until resolution.

#### Scenario: an A2A adapter delegates bounded work

- **WHEN** an optional A2A-style adapter delegates repository work
- **THEN** the request binds source and target actors, scope, permissions, exact
  inputs, expiry, and acceptance conditions
- **AND** the target returns `accept` or `reject` before returning an exact result
  or a handoff or takeover reference
- **AND** protocol state is disposable and reconstructable and owns no
  Commitment, Lease, task, verdict, evidence, or repository authority.

#### Scenario: branch roles bound local and remote transitions

- **WHEN** ETHOS resolves the branch role for an integration or publication
  transition
- **THEN** `work/*` and `candidate/dev` are local-only, `dev` and the default
  `main` are protected, and `proposal/*` is the sole remote review role
- **AND** an unknown or mismatched role blocks before any remote effect.

#### Scenario: foreign lane preview remains observe-only

- **WHEN** status reports a linked foreign Work Lane
- **THEN** its action preview lists `observe` as the only candidate action and
  blocks `write`, `land`, and `retire`
- **AND** it states `mints_authority=false` and `recheck_required=true`
- **AND** actual mutation re-evaluates the exact current request
- **AND** legacy actor-capability fields cannot be replayed as authority and are
  retired after client migration.

#### Scenario: bounded readers defer foreign path scopes

- **WHEN** a bounded status, planning, proof, landing, or publication
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

#### Scenario: normalized lease has one concrete current holder

- **WHEN** a lane lease is created, renewed, resumed, or handed off
- **THEN** it binds a random local lane-incarnation ID, lease ID, structured
  holder reference, epoch, issuance, renewal, expiry, and optional path scope
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

#### Scenario: a session is lost
- **WHEN** a worker session or inbox projection disappears
- **THEN** an authorized successor reconstructs admissible work from Git, Commitment, fresh Facts, and Attestations

### Requirement: Cohort-bound full Work Lane convergence
Collaboration and competition SHALL derive from scope conflict, capacity, risk, and proof cost; no universal worker or competitor cardinality applies.

#### Scenario: adaptive admission preserves fair candidate progress

- **WHEN** multiple ready Work Lanes compete for authoring, proof, or candidate
  capacity
- **THEN** admission derives WIP from scope conflict, host capacity, risk, proof
  cost, queue age, and observed candidate throughput
- **AND** equivalent ready work ages monotonically and cannot starve without an
  explicit current blocker
- **AND** authoring and proof may run concurrently while only the candidate CAS
  is serialized
- **AND** a stale candidate attempt has zero effect, re-observes and re-proves
  before bounded retry, and reports the blocker when retry cannot safely proceed.

#### Scenario: a convergence cohort is frozen before mutation

- **GIVEN** a maintainer requests convergence of multiple existing Work Lanes
- **WHEN** the program begins
- **THEN** a separate owned governance Work Lane records the exact branch, HEAD,
  worktree binding, dirty state, lease/incarnation evidence, Attestation binding,
  intended disposition, and target-observation evidence for each lane
- **AND** later-created refs are outside the cohort unless separately admitted
- **AND** every effect recomputes mutable target facts before mutation.

#### Scenario: graph absorption does not erase a dirty overlay

- **GIVEN** a lane HEAD is equal to or an ancestor of accepted truth
- **AND** its linked worktree contains a dirty tracked or untracked delta
- **WHEN** convergence classifies the lane
- **THEN** the delta is preserved and semantically reviewed before retirement
- **AND** graph ancestry alone cannot authorize deletion.

#### Scenario: a valid foreign lease remains holder-bound

- **GIVEN** a cohort lane has a normalized valid lease owned by another holder
- **WHEN** convergence needs its implementation or closeout
- **THEN** normal holder completion or a quiesced exact handoff is preferred
- **AND** process absence, provider identity, or a supplied holder string does
  not grant takeover authority
- **AND** replay in an owned successor keeps the original lane observe-only.

#### Scenario: exceptional cohort resolution consumes accepted judgment

- **GIVEN** a cohort lane is dirty, missing trusted lease state, owner-uncertain,
  or requires irreversible retirement
- **WHEN** the lane is resolved
- **THEN** a valid Attestation has already bound the exact policy and target
- **AND** a fresh two-phase judgment binds one exact observation and recovery
  plan
- **AND** dirty content is preserved before retirement
- **AND** a stale observation blocks the effect instead of falling back to raw
  Git deletion.

#### Scenario: local convergence completion keeps evidence planes separate

- **WHEN** all cohort intent has been integrated or explicitly superseded
- **THEN** strict carrier completion, parity, HEAD-bound executed proof,
  candidate landing, accepted-root closeout, and lane retirement are verified as
  distinct transitions
- **AND** recovery-package retention remains independent
- **AND** local completion does not claim remote push, hosted execution, or
  distribution publication.

#### Scenario: two variants overlap
- **WHEN** two valid variants address the same Commitment scope
- **THEN** only an explicit selection Attestation may advance an integration ref by exact CAS

### Requirement: External Retirement Readiness
A carrier SHALL be retired only when it is non-current, has no active inbound or runtime consumer, has an absorbed or void semantic delta, and has required preservation.

#### Scenario: a repository-family record enters immutable history

- **WHEN** ETHOS materializes a preservation or closeout record
- **THEN** `record-admit` accepts only an exact repository-family path under
  `evidence/<timestamp>-<purpose>/` or `recovery/<timestamp>-<purpose>/`
- **AND** the record contains `README.md`, `closeout.json`, `MANIFEST.json`, and
  `SHA256SUMS` with a complete integrity inventory
- **AND** `record-verify` passes before `records-index --write` changes the derived
  index
- **AND** indexed historical bytes are immutable; a later state adds a new record
  and superseding index entry rather than rewriting or deleting history
- **AND** the index remains a projection and mints no lifecycle authority.

#### Scenario: Retirement readiness is inspected
- **WHEN** a target carrier is evaluated for retirement
- **THEN** ETHOS reads the target repository's `.ethos/profile.toml`
- **AND** validates declared binding roots such as `.config/`
- **AND** rejects profile-declared forbidden product-core adopter roots in the
  ETHOS product repository
- **AND** includes parity and shadow false-negative evidence in the verdict
- **AND** reports external-default, embedded-freeze, rollback-window evidence,
  and final retirement lifecycle gaps separately from parity and product-boundary gaps
- **AND** requires a tracked rollback-window evidence manifest with completed
  `proof_report`, `work_lane_closeout`, `domain_gate`, and `assistant_playbook`
  scenarios before accepting a terminal retirement-ready backend state
- **AND** requires the rollback-window manifest to be repository-local,
  Git-tracked, parseable, bound to reachable adopter and external-product
  heads, and backed by per-scenario evidence path, command, digest, target-head,
  and product-head fields
- **AND** does not require `adopters/<name>`, `profiles/<name>`, or
  `tests/fixtures/adopters/<name>` inside the ETHOS product repository.

#### Scenario: a legacy document duplicates active semantics
- **WHEN** its unique meaning is absorbed and all consumers are removed
- **THEN** it becomes `deleted-after-proof` or `historical` without creating a generic archive truth root

### Requirement: Evolution Governance
Contradictions, stale projections, and model gaps SHALL promote the affected boundary and recompile dependent projections before retirement.

#### Scenario: Hypotheses are inspected
- **WHEN** a Commitment containing hypotheses is compiled
- **THEN** hypotheses remain immutable planning inputs rather than authority
- **AND** only a valid Attestation may establish an accepted experimental result

#### Scenario: a taxonomy cannot classify a valid observation
- **WHEN** classification would discard or distort a valid distinction
- **THEN** ETHOS blocks the effect and promotes the model boundary without imposing any taxonomy

## REMOVED Requirements

### Requirement: Work Lane Lifecycle Resolution

**Reason**: Two identically named lifecycle requirements create duplicate archived authority.

**Migration**: Their identical scenarios consolidate under one exact lifecycle-effect requirement.

**Replacement**: Exact Work Lane Lifecycle Effects
