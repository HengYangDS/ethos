## REMOVED Requirements

### Requirement: Evidence-backed Claims

**Reason**: Claim duplicates the Attestation evidence envelope.

**Migration**: Express the assertion as an Attestation predicate and payload.

### Requirement: Evolution Governance

**Reason**: Campaign and Claim fields duplicate Commitment hypotheses and
Attestation observations.

**Migration**: Commitment owns hypotheses/protocols; Attestations own runs,
observations, results, and judgments.

### Requirement: Evolution Ledger Protocol

**Reason**: A mutable ledger creates a second currentness and selection owner.

**Migration**: Derive learning views from Commitments and Attestations.

### Requirement: Practice Selection And Fate

**Reason**: Practice Claims, candidate sets, evaluations, and fate records are
Attestation payloads and relations, not independent authorities.

**Migration**: Selection Attestations preserve judgments; successor Commitments
adopt normative effects.

### Requirement: Practice Evolution Kernel

**Reason**: Its useful contract is subsumed by Commitment protocols and
Attestation judgments without Claim or Chronicle promotion.

**Migration**: Use the two-root model and typed successor binding.

### Requirement: Trust-bearing Claim Admission

**Reason**: Trust evidence is an Attestation predicate with exact bindings.

**Migration**: Validate the bound Attestation in the operation authority query.

### Requirement: Claim evidence freshness is explicit

**Reason**: Attestation validity and bindings own freshness directly.

**Migration**: Use issued/valid times and exact semantic bindings.

### Requirement: Evolution Ledger Single Source Of Truth

**Reason**: There is no independent evolution truth store.

**Migration**: Use Commitment and the selected Attestation set.

### Requirement: Campaign Orchestration

**Reason**: Campaign state duplicates bounded OpenSpec Changes and task progress.

**Migration**: Use dependency-linked successor Commitments and one task graph per
Change.

### Requirement: Campaign Lifecycle Truth Is Carrier-Bound

**Reason**: Campaign lifecycle is a parallel projection that can disagree with
Git, Change, and Attestation facts.

**Migration**: Derive program views from the two-root model.

### Requirement: Canonical Persisted Claim Envelope

**Reason**: Attestation v2 is the sole persisted evidence envelope.

**Migration**: Historical Claim bytes remain inert; no current reader remains.

### Requirement: Campaign-terminal protected publication admission

**Reason**: Campaign state cannot authorize publication.

**Migration**: A successor publication Change shall consume exact Commitments,
Facts, plans, and Attestations.

### Requirement: Promotion Target Readiness

**Reason**: Claim-owned promotion targets duplicate Commitment scope and
acceptance.

**Migration**: The successor Commitment names normative targets and exact
operation queries consume their Attestations.

### Requirement: Semantic claim attestations are typed and candidate-external

**Reason**: The Claim assurance class duplicates Attestation v2.

**Migration**: Use one candidate-external Attestation with exact predicate,
payload, validity, and bindings.

### Requirement: Lifecycle claim semantic scope is behavior-exact

**Reason**: Claim semantic-scope freshness is a second selection and currentness
owner.

**Migration**: Bind exact affected paths and semantic inputs in Commitment and
operation Attestations.

## MODIFIED Requirements

### Requirement: Work Lane Lifecycle Resolution

Routine lifecycle SHALL remain mechanically derived from current facts and exact
plans. Exceptional interpretive judgment SHALL be an exact, non-authorizing
Attestation selected by the operation; Chronicle SHALL have no current reader or
producer.

#### Scenario: routine lifecycle remains local

- **WHEN** coordination is mechanically determined
- **THEN** ETHOS uses local Lease fencing and postcondition Attestations
- **AND** no tracked decision record is required

#### Scenario: exceptional cleanup consumes prior accepted judgment

- **WHEN** an exceptional destructive operation requires human judgment
- **THEN** a separately accepted Commitment and bound decision Attestation name
  exact target, evidence, disposition, recovery, and validity
- **AND** the operation re-observes mutable facts before its first effect

#### Scenario: dirty or unknown work is preserved by default

- **WHEN** ownership, Lease, content, or recovery status is unknown or dirty
- **THEN** ETHOS preserves or blocks rather than inferring authority
- **AND** irreversible deletion requires exact accepted judgment and evidence

#### Scenario: break-glass reconciles after emergency action

- **WHEN** a predeclared break-glass Commitment admits an emergency effect
- **THEN** the result is an exact Attestation and later integration remains
  blocked until accepted reconciliation
- **AND** a self-supplied flag or holder string is insufficient

#### Scenario: lane handoff is recorded as Chronicle resolution

- **WHEN** an exceptional handoff judgment is required
- **THEN** it is recorded as a decision Attestation, not Chronicle
- **AND** it does not replace the destination-local Lease

#### Scenario: orphan audit produces a decision, not a persistent orphan state

- **WHEN** a lane has missing or ambiguous holder evidence
- **THEN** orphan-like facts remain observations and accepted disposition is an
  Attestation
- **AND** no persistent orphan or Chronicle state is created

#### Scenario: clean ownerless diverged source retires after semantic absorption

- **WHEN** exact accepted judgment and evidence admit retirement
- **THEN** the resolver re-observes the source and emits an effect Attestation
- **AND** the authority does not extend to another lane or remote effect

### Requirement: Work Lane Coordination Read Model

The coordination reader SHALL derive current lane views from Git facts, the
selected Commitment, local Lease fencing, and exact Attestation queries. It
SHALL NOT expose shared-inbox acknowledgement, consumed state, cursor, mutable
selection, or inbox digest as lifecycle or progress authority.

#### Scenario: Concurrent input exists

- **WHEN** input occurrences are present in the Attestation set
- **THEN** status may project their immutable identities and selected
  dispositions
- **AND** absence of an acknowledgement or mutable inbox flag creates no hidden
  progress state

#### Scenario: foreign lane preview remains observe-only

- **WHEN** status sees a foreign Work Lane
- **THEN** it projects observed facts without mutation authority
- **AND** visibility grants no handoff, land, or retirement right

#### Scenario: bounded readers defer foreign path scopes

- **WHEN** detailed foreign path inspection is outside the bounded read
- **THEN** the reader marks detail deferred
- **AND** it does not infer overlap or safety

#### Scenario: projection preserves observed coordination detail state

- **WHEN** a bounded reader emits coordination detail state
- **THEN** summary and payload agree on that state
- **AND** no inbox counter substitutes for direct observation

#### Scenario: normalized lease has one concrete current holder

- **WHEN** a valid current Lease is projected
- **THEN** it names one concrete holder and generation
- **AND** no shared-inbox consumer identity replaces the holder

#### Scenario: lease generation detects but does not claim hard fencing

- **WHEN** a Lease generation is current
- **THEN** it detects stale local mutations and coordinates writers
- **AND** it does not claim distributed or provider fencing

#### Scenario: lease and Git lifecycle is crash-consistent

- **WHEN** a coordinated transition is interrupted
- **THEN** exact receipt and observed Git/Lease states determine recovery
- **AND** no mutable inbox state determines success

#### Scenario: legacy adoption and cleanup resist replay

- **WHEN** retired coordination bytes are encountered
- **THEN** current readers ignore them as authority
- **AND** they cannot be replayed through compatibility discovery

#### Scenario: cross-host handoff creates destination-local coordination

- **WHEN** an exact handoff is accepted on another host
- **THEN** the destination creates its own local Lease generation
- **AND** an acknowledgement is evidence only, not lifecycle state

### Requirement: Preservation-bound exceptional Work Lane retirement

ETHOS SHALL preserve or preserve-retire a dirty foreign or ownerless Work Lane
only when a separately accepted Commitment requires the disposition and one
exact decision Attestation binds target, observation, recovery material,
validity, and actor. The operation SHALL re-observe every mutable fact before
its first effect.

#### Scenario: dirty residual lane is preserved without retirement

- **GIVEN** an exact decision Attestation selects preservation for one dirty lane
- **WHEN** a maintainer applies the accepted operation
- **THEN** ETHOS writes and verifies the digest-bound recovery package
- **AND** retains the exact branch and worktree

#### Scenario: dirty lane is preserved before retirement

- **GIVEN** an exact decision Attestation selects preserve-retire
- **WHEN** irreversible controls and fresh observations pass
- **THEN** ETHOS verifies recovery material before exact retirement
- **AND** emits one effect Attestation requiring reconciliation when partial

#### Scenario: ordinary dirty retirement remains blocked

- **WHEN** dirty retirement lacks the accepted Commitment and exact decision
  Attestation
- **THEN** ETHOS blocks without removing branch or worktree

#### Scenario: Chronicle disposition is bound before the effect

- **WHEN** a disposition is required before an exceptional effect
- **THEN** ETHOS binds one decision Attestation and its canonical identity
- **AND** no Chronicle path, mutable decision record, or supplied flag authorizes
  the effect

#### Scenario: detached dirty residue is normalized without changing bytes

- **WHEN** a detached historical worktree is prepared for exact resolution
- **THEN** ETHOS first captures HEAD, index, reflog, path, ownership, and content
  digests without changing bytes
- **AND** any reconstructed ref mints neither ownership nor effect authority

### Requirement: External-adopter profile evidence has a bounded durable record

A completed local external-adopter binding exercise SHALL be one Attestation
whose payload binds product revision, adopter revision, outcome, raw-bundle
digest, and publication boundary. Host-local raw material and provider state
remain evidence, not repository truth.

#### Scenario: Local profile evidence is promoted

- **WHEN** an isolated binding exercise completes
- **THEN** its Attestation binds exact revisions, outcomes, and raw-bundle digest
- **AND** explicitly states whether remote publication occurred

#### Scenario: Digest-bound evidence is reviewed

- **WHEN** the Attestation proves only digest-bound observation
- **THEN** it does not claim semantic correctness, hosted execution, provider
  authority, or independent review
- **AND** it requires no named account, credential, key, daemon, or network

### Requirement: Exceptional unbound Work Lane retirement is exact and accepted-policy-bound

`ethos lane retire unbound` SHALL admit one exact unbound ref only through a
selected Commitment and target-specific decision Attestation. The command SHALL
bind target ref/head, accepted relation, Lease observation, actor, reason, and
irreversible controls; no provider, session, host, Claim, or Chronicle grants
authority.

#### Scenario: Exact accepted-ancestor residue is inspected

- **WHEN** one unbound ref is an exact accepted ancestor with no linked worktree
  and its selected evidence matches
- **THEN** dry-run reports the exact retirement observation without mutation
- **AND** reports that the result mints no reusable authority

#### Scenario: One carrier does not authorize another target

- **WHEN** a decision Attestation names another ref or head
- **THEN** ETHOS blocks the target before mutation
- **AND** requires its own exact evidence and receipt

#### Scenario: A non-exact or non-accepted target is refused

- **WHEN** relation, head, Lease, target evidence, or accepted binding is absent,
  ambiguous, stale, foreign, or mismatched
- **THEN** ETHOS preserves the ref and Lease
- **AND** reports the exact failed binding

#### Scenario: Exceptional controls are incomplete

- **WHEN** authorization, break-glass, or irreversible confirmation is absent
- **THEN** ETHOS blocks before ref or Lease mutation

#### Scenario: Unavailable source holder is recovered only by exact accepted policy

- **WHEN** an accepted Commitment and decision Attestation bind owner-unavailable
  recovery, exact Lease generation, absent source path, actor, and target
- **THEN** ETHOS may revoke only that exact Lease through native CAS
- **AND** any present path, same holder, drift, or incomplete evidence blocks

### Requirement: Exceptional unbound effects are compare-and-delete and receipt-bound

Before an exceptional unbound effect, ETHOS SHALL re-observe the exact target,
selected Commitment, decision Attestation, Lease, and protected refs. It SHALL
publish a no-clobber attempt, compare-delete only the expected ref, verify
postconditions, and record the result in the sole Attestation set.

#### Scenario: Current holder relinquishes one exact lease generation

- **WHEN** the exact current holder and generation satisfy the selected operation
- **THEN** ETHOS revokes only that Lease through native CAS
- **AND** re-observes all non-Lease bindings before ref deletion

#### Scenario: Lease relinquishment remains fail-closed

- **WHEN** the Lease is absent, foreign, malformed, stale, replaced, or
  head-mismatched
- **THEN** ETHOS leaves the source ref intact and reports the observed gap

#### Scenario: Apply deletes only the observed ref

- **WHEN** all exact bindings remain stable and compare-delete succeeds
- **THEN** the effect Attestation binds before/after observations and
  postconditions
- **AND** protected refs remain unchanged

#### Scenario: Observation or postcondition drifts

- **WHEN** target, evidence, Lease, protected refs, or postconditions drift
- **THEN** ETHOS reports a blocked partial result without deleting newer state

#### Scenario: Target-specific evidence remains vendor-neutral

- **WHEN** exceptional retirement evidence is evaluated
- **THEN** its authority is limited to the exact branch, head, and operation
- **AND** vendor, account, session, host, or another target cannot extend it

### Requirement: Ref-absent owner-unavailable partial effects are reconciled only through exact native lease CAS

`ethos lane retire reconcile-ref-absent` SHALL reconcile only an immutable prior
attempt whose ref and path are absent while its exact foreign Lease remains. A
selected Commitment and decision Attestation SHALL bind the prior operation,
accepted head, source Lease tuple, recovery actor, and postconditions.

#### Scenario: Exact ref-absent residue is reconciled

- **WHEN** ref/path absence, protected refs, evidence, and Lease tuple still
  match the prior attempt
- **THEN** ETHOS revokes only that exact Lease through native CAS
- **AND** records success only after ref, path, and Lease absence are proven

#### Scenario: Reconciliation observation or evidence drifts

- **WHEN** a ref or path reappears or any bound fact changes
- **THEN** ETHOS blocks before Lease mutation
- **AND** preserves all foreign state

### Requirement: Ownerless closeout admission is consumed at the effect boundary

ETHOS SHALL retire a clean linked ownerless Work Lane only when the executor
recomputes the exact selected Commitment, decision Attestation, observations,
accepted relation, and local fencing. It SHALL perform no force operation and
write one completion Attestation only after exact postconditions pass.

#### Scenario: exact ownerless target is retired

- **WHEN** target, accepted head, decision, observation, occupancy, and fence
  remain exact
- **THEN** ETHOS performs only the admitted worktree/ref effects
- **AND** records completion after explicit absence checks

#### Scenario: decision snapshot replacement is rejected

- **WHEN** the decision Attestation changes after admission
- **THEN** ETHOS blocks before any effect
- **AND** later bindings derive from one immutable snapshot

#### Scenario: late coordination or competing decision blocks zero-effect

- **WHEN** a Lease, accepted head, decision, path, or reservation changes before
  the fence is acquired
- **THEN** ETHOS performs no Git or worktree effect

#### Scenario: worktree-remove failure is re-observed

- **WHEN** worktree removal fails
- **THEN** ETHOS re-reads ref, registration, and path
- **AND** reports the exact partial state rather than rollback success

#### Scenario: zero-effect retry is rebound after accepted history advances

- **WHEN** no effect occurred and accepted history advanced by ancestry only
- **THEN** fresh admission may replace the exact old fence and reservation
- **AND** divergence or any other drift blocks

#### Scenario: target-ref inspection is three state

- **WHEN** a target ref is present, absent, or unreadable
- **THEN** only explicit absence satisfies the postcondition

#### Scenario: destructive partial transition remains visible and recoverable

- **WHEN** any destructive boundary becomes partial or uncertain
- **THEN** inventory retains exact phase, target, decision, and recovery facts

#### Scenario: receipt-present cleanup retry converges

- **WHEN** the completion Attestation is durable but cleanup is incomplete
- **THEN** retry verifies it and performs only idempotent cleanup
- **AND** never recreates effect authority

#### Scenario: closeout-fence inspection is three state

- **WHEN** the exact fence is present, absent, or unverifiable
- **THEN** each recovery phase accepts only its explicitly declared state
- **AND** unverifiable state blocks

#### Scenario: successful cleanup preserves ordering

- **WHEN** cleanup follows durable completion
- **THEN** ETHOS releases the exact fence before removing the reservation

#### Scenario: effect-complete recovery precedes ordinary observation

- **WHEN** effect completion lacks its final Attestation
- **THEN** recovery resolves completion before ordinary lane observation

#### Scenario: dangling path and post-CAS exception fail closed

- **WHEN** a dangling path or post-CAS exception is observed
- **THEN** ETHOS treats the path as present and reports transition unknown

#### Scenario: native ownerless authority binding is exact

- **WHEN** any required decision or coordination field is absent or invalid
- **THEN** ETHOS rejects admission without inferring compatibility

#### Scenario: canonical and legacy reservations disagree

- **WHEN** historical reservation bytes coexist with the current carrier
- **THEN** current readers ignore historical bytes as authority
- **AND** no scan-order choice or compatibility merge occurs

#### Scenario: receipt compatibility is one way

- **WHEN** historical completion bytes are encountered after cutover
- **THEN** they remain inert history and cannot satisfy current recovery
- **AND** new completion uses Attestation v2 only

#### Scenario: damaged fence payload preserves independent lease truth

- **WHEN** a fence payload is invalid but Lease state is independently readable
- **THEN** inventory reports both facts separately
- **AND** invalid fence state cannot erase or authorize the Lease

## ADDED Requirements

### Requirement: Continuous intent preserves bounded Changes

Every accepted feedback occurrence SHALL be preserved in the Attestation set and
selected to a semantic owner or explicit absence, contradiction, or model-gap
disposition. New input SHALL NOT expand an active Commitment implicitly.

#### Scenario: Several agents provide concurrent feedback

- **WHEN** their inputs are independent
- **THEN** exact-CAS set union preserves every occurrence
- **AND** selections may feed disjoint successor Commitments

### Requirement: One Commitment binds one Change and lane generation

An effective Commitment SHALL bind one OpenSpec Change, one writable owner lane
generation, and one task authority. Successors MAY run concurrently only when
dependencies, scopes, and exact effects are disjoint.

#### Scenario: Input is deferred to a successor

- **WHEN** it cannot be completed inside the active boundary
- **THEN** selection and dependency remain traceable
- **AND** deferral does not count as implementation
