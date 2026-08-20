## MODIFIED Requirements

### Requirement: Declared publication peer topology

The repository SHALL declare zero or more publication peers explicitly. Each
peer SHALL have a unique peer ID and Git remote plus a provider label used only
to select a transport or observation adapter. Provider labels MAY repeat and
SHALL NOT create a primary peer, product identity, object producer, signing
authority, or dependency between peers. The locally existing Git object SHALL
be the sole publication source. Every peer SHALL be optional and independently
observed, updated, verified, retried, and attested.

#### Scenario: local-only publication remains valid

- **WHEN** valid local verification and installation are declared with no peers
- **THEN** the local publication lifecycle SHALL complete without remote observation
- **AND** it SHALL NOT claim hosted CI or remote publication

#### Scenario: independent remote observations remain no-push

- **WHEN** publish readiness observes one or more declared peers
- **THEN** it SHALL expose each target separately without pushing
- **AND** hosted CI status SHALL remain unclaimed unless separately evidenced

#### Scenario: publication is local only

- **WHEN** the peer collection is empty and both local commands are valid
- **THEN** topology and local publication readiness SHALL remain valid
- **AND** no remote observation or hosted claim SHALL be manufactured

#### Scenario: GitLab is the only declared peer

- **WHEN** exactly one GitLab peer is declared
- **THEN** publication SHALL observe and update only that peer
- **AND** it SHALL NOT require GitHub or infer a primary provider

#### Scenario: GitHub is the only declared peer

- **WHEN** exactly one GitHub peer is declared
- **THEN** publication SHALL observe and update only that peer
- **AND** it SHALL NOT require GitLab or infer a primary provider

#### Scenario: both remote peers are declared

- **WHEN** several peers have unique IDs and Git remotes
- **THEN** every peer SHALL receive the same selected local Git object
- **AND** no peer SHALL read, wait on, rewrite, or act as the source for another peer

#### Scenario: provider labels repeat

- **WHEN** several distinct peers use the same provider adapter
- **THEN** topology SHALL remain valid
- **AND** peer identity SHALL remain the declared ID and Git remote rather than the provider label

#### Scenario: peer identity is ambiguous

- **WHEN** two peers reuse an ID or Git remote
- **THEN** topology SHALL fail closed before remote observation or mutation

#### Scenario: retired and current declarations coexist

- **WHEN** peer tables coexist with a fixed provider publication scalar
- **THEN** topology SHALL fail closed as an ambiguous declaration

### Requirement: Strict remote publication admission

Publication admission SHALL resolve the complete target ref through one
provider-neutral contract:

```text
ref kind -> lifecycle role -> local source object -> allowed effect
```

The admitted kinds SHALL be accepted branch, release branch, proposal branch,
and annotated release tag. Candidate and Work Lane branches SHALL remain local
only. An annotated release tag matching the declared release-tag policy SHALL
have release-publication role and SHALL NOT be classified as branch role
`other`. Unknown refs, lightweight release tags, undeclared remotes, ambiguous
topology, untrusted local signatures, and refs outside the positive role set
SHALL fail closed before a writable remote effect.

#### Scenario: accepted and release branches are publishable

- **WHEN** a proved accepted object is selected for the declared accepted and release refs
- **THEN** both refs SHALL be eligible targets of one receipt-bound publication request
- **AND** each desired OID SHALL be the exact selected local commit OID

#### Scenario: explicit remote admission preserves local candidate isolation

- **WHEN** a proved candidate object is selected for a declared proposal ref
- **THEN** the proposal ref SHALL be eligible for publication
- **AND** candidate and Work Lane refs themselves SHALL remain remote-forbidden

#### Scenario: annotated release tag is classified positively

- **WHEN** a locally existing signed annotated tag matches the declared release-tag policy
- **THEN** `refs/tags/<tag>` SHALL resolve to annotated release tag and release-publication role
- **AND** it SHALL NOT emit `publication_remote_role_unavailable:other`

#### Scenario: tag is lightweight or untrusted

- **WHEN** a release-tag target is not an annotated tag object or its local signature is not trusted
- **THEN** publication SHALL fail before observing a writable remote effect
- **AND** it SHALL identify the exact object or trust gap

#### Scenario: non-canonical declaration fails closed

- **WHEN** publication configuration is missing, contains unknown fields, mixes retired scalar ownership with peers, or names an undeclared remote
- **THEN** admission SHALL fail closed
- **AND** it SHALL NOT infer `origin`, preserve a compatibility state, or bypass ref enforcement

#### Scenario: repository-only peer has no CI

- **WHEN** a declared peer omits both the `ci_cd` capability and `ci_surface`
- **THEN** local verification SHALL remain required
- **AND** hosted CI SHALL remain unclaimed without blocking repository publication

### Requirement: Independent peer effects remain recoverable

ETHOS SHALL treat each declared peer as an independent transaction and SHALL
NOT claim cross-peer atomicity. A request SHALL bind each peer's exact expected
OID, desired local object OID, and target ref. If one peer succeeds before
another fails, the terminal Attestation SHALL identify applied, failed, and
pending peers. Replaying the same request SHALL preserve peers already equal to
the desired OID and continue safely without replaying, re-signing, merging, or
rewriting any product object.

#### Scenario: one peer rejects the push

- **WHEN** an earlier peer applies and a later peer rejects its exact-CAS update
- **THEN** the result SHALL be a partial effect with immutable evidence
- **AND** unchanged request replay SHALL converge without rewriting the applied peer

#### Scenario: a peer is already current

- **WHEN** a peer target already equals the request's desired object OID
- **THEN** that peer SHALL be recorded as already applied
- **AND** no push or object reconstruction SHALL occur for that peer

#### Scenario: a peer diverges

- **WHEN** a peer target equals neither the exact expected OID nor desired OID
- **THEN** the request SHALL fail before the first new effect
- **AND** ETHOS SHALL NOT merge, replay, re-sign, or infer equivalence from its tree

### Requirement: Publication semantics have one owner per layer

The peer collection SHALL be the sole topology owner. One typed full-ref target
resolver SHALL own ref kind and lifecycle role. One `TransitionPlan` compiler
SHALL bind local object facts, selected proof Attestation, exact peer targets,
and effects. One Git executor SHALL own live remote observation, exact CAS,
post-write verification, and partial-effect Attestation. Public CLI and Git
hooks SHALL consume these owners and SHALL NOT recreate branch parsing, proof
selection, peer reconciliation, or object identity policy.

#### Scenario: public command and hook inspect one target

- **WHEN** `ethos publish` and pre-push evaluate the same target ref and local object
- **THEN** they SHALL project the same ref kind, lifecycle role, proof authority, and required gaps
- **AND** a missing proof SHALL name one executable `ethos prove --execute --expect-head <oid> --json` continuation

#### Scenario: observation projections are not mutation authority

- **WHEN** remote-tracking refs or provider status are displayed
- **THEN** those readers MAY describe current observations
- **AND** they SHALL NOT authorize or alter an exact-CAS publication effect

#### Scenario: several peers use one provider

- **WHEN** peer IDs and Git remotes are unique but provider labels repeat
- **THEN** topology SHALL remain valid
- **AND** each peer SHALL be independently observed and admitted

#### Scenario: no remote peer is declared

- **WHEN** local verification and installation commands are valid and peers are empty
- **THEN** local publication readiness SHALL remain valid
- **AND** no remote observation or hosted claim SHALL be manufactured

## ADDED Requirements

### Requirement: Exact local Git object projection

A product commit or annotated release tag SHALL be created and signed once in
the local Git authority. ETHOS SHALL verify the selected local object's
signature through Git and the repository's declared OpenSSH trust projection,
then publish the exact existing object bytes. Transport authentication,
provider account identity, and provider `Verified` presentation SHALL remain
separate observations and SHALL NOT alter author, committer, tagger, message,
parents, timestamp, signature, or object OID.

For a commit target, verification SHALL bind the exact commit OID and tree. For
an annotated tag, verification SHALL bind the exact tag object OID, peeled
commit OID, peeled tree OID, signer principal, signer fingerprint, and trust-root
digest. Every peer post-observation SHALL match those coordinates exactly.

#### Scenario: one signed commit reaches two peers

- **WHEN** one trusted local commit is published to two independent peers using different transport credentials
- **THEN** both peer refs SHALL equal the local commit OID
- **AND** the transport credentials SHALL not appear in product object identity

#### Scenario: one annotated tag reaches two peers

- **WHEN** one trusted local annotated tag is published to two independent peers
- **THEN** local and peer tag object OIDs SHALL be exactly equal
- **AND** their peeled commit and tree OIDs SHALL be exactly equal

#### Scenario: a new remote ref is created

- **WHEN** the target ref is absent
- **THEN** the plan SHALL bind the repository's zero OID as the expected state
- **AND** Git execution SHALL compile that state into an explicit empty exact lease

#### Scenario: tree-only equality is insufficient

- **WHEN** a peer object has the expected tree but a different commit or tag object OID
- **THEN** publication parity SHALL fail closed
- **AND** ETHOS SHALL NOT accept provider replay, re-signing, identity rewrite, or tree-only equivalence

#### Scenario: proof authority is exact

- **WHEN** publication selects a proof Attestation
- **THEN** the plan SHALL bind its exact ID, repository Commitment, commit, tree, gate-set policy digest, and verdict
- **AND** hook and receipt apply SHALL reject any coordinate drift

## REMOVED Requirements

### Requirement: Proposal publication is receipt-bound exact CAS

**Reason**: Proposal-only publication is replaced by one full-ref Git object
publication contract that covers proposal, accepted, release, and annotated tag
targets through the same plan and executor.

**Migration**: Use `ethos publish` to derive and apply the typed target set. The
proposal mode remains a target selection, not a separate effect type or object
producer.

### Requirement: Maintainer remote reconciliation preserves observed protected history

**Reason**: Treating divergent peer tips as product inputs contradicts local
Git object authority and creates a second history producer.

**Migration**: A peer must either equal the local desired OID or the request's
exact expected old OID. Other states fail closed. A separately authorized,
one-time destructive cutover may replace a known remote tip but SHALL never
merge or replay it into product history.

### Requirement: Remote reconciliation continuation preserves historical carrier boundaries

**Reason**: The standing reconciliation lifecycle depends on the removed
divergent-history model and preserves obsolete Claim and archive coupling.

**Migration**: Retain historical bytes as non-authorizing Git history. Current
publication starts from the selected local object and exact live peer facts;
historical reconciliation state grants no authority and has no continuation.
