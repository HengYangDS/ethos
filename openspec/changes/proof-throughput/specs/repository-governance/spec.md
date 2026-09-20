## MODIFIED Requirements

### Requirement: Release tags preserve native product version authority

ETHOS SHALL create requested signed annotated tags from exact committed native
version authority through the existing Git effect. Independent release may
advance its declared branch; an accepted mirror SHALL already be aligned and
remain an assertion. Malformed, conflicting or untrusted inputs SHALL block.
An existing package version SHALL NOT require a parallel VERSION carrier.

#### Scenario: Native package version owns release

- **WHEN** package.json is the unambiguous committed version owner
- **THEN** the tag matches that version and peels to accepted
- **AND** its signature passes current protected trust verification
- **AND** release changes and the new tag use one native transaction

#### Scenario: Tag or version conflicts

- **WHEN** the requested tag disagrees with version, already exists without a carried
  request, is divergent or lacks a trusted signature
- **THEN** neither release nor tag ref changes

#### Scenario: Accepted mirror creates a release tag

- **WHEN** accepted closeout has aligned the protected branches and the request
  names that exact accepted object for both coordinates
- **THEN** the release owner creates the tag while asserting both branch objects
- **AND** a misaligned mirror is directed to accepted closeout without effects
- **AND** a release-tag hook lacking executor intent selects the exact release preview

#### Scenario: Aligned release has no requested change

- **WHEN** the exact release branch already equals accepted and no tag is requested
- **THEN** validation succeeds without a ref update or new effect Attestation

#### Scenario: Interrupted or repeated release

- **WHEN** release resumes after an observed or unknown effect in either mirror mode
- **THEN** ETHOS observes exact refs and evidence before replay
- **AND** an accepted tag object is reused without resigning
- **AND** compensation reverses only changed refs and retains branch assertions
- **AND** pending linked worktree synchronization remains explicit

### Requirement: Control replacement preserves trusted prior verification

Control replacement SHALL read independent-verification policy from both exact
committed objects and retain the stricter mode during acceptance. Changed gate
identities SHALL remain review evidence, not implicit provider enrollment.
Applying a changed floor SHALL require explicit authorization, exact accepted
and candidate commits, current proof, fresh effect admission and CAS.

#### Scenario: Candidate cannot disable its required verifier

- **WHEN** a candidate replaces a required accepted verification policy with disabled
- **THEN** control replacement still requires evidence under the prior policy

#### Scenario: Executing authority is not an ordinary unverified change

- **WHEN** runtime selection, hook execution or Git-effect implementation changes
- **THEN** admission classifies the changed path as control and applies that policy

#### Scenario: Changed gate identities retain local-first acceptance

- **WHEN** both exact policies disable independent verification and gate execution changes
- **THEN** admission does not inspect or require host provider configuration
- **AND** the report exposes changed obligations without claiming semantic equivalence
- **AND** apply without explicit candidate selection is rejected without moving refs
- **AND** exact authorized acceptance remains reachable without an external receipt

#### Scenario: Uncommitted policy cannot change the verification requirement

- **WHEN** worktree policy differs from the selected candidate commit
- **THEN** verification selection uses the committed candidate and accepted predecessor

### Requirement: Official Change bootstrap is a bounded write authority

An owned Work Lane with a valid Lease SHALL create and complete one selected
official Change before Commitment compilation. Selection SHALL consume exact
active identity and official artifact outputs, including when other Changes
coexist. Only those outputs are admitted; directory-wide authority is excluded.

#### Scenario: Official metadata starts the first Change

- **GIVEN** a clean owned Work Lane has a valid current Lease
- **AND** no other active official Change exists
- **WHEN** the official OpenSpec command creates one valid Change metadata file
- **THEN** prewrite admits that Change's official proposal, specs, design,
  tasks, and metadata paths
- **AND** no product path, unrelated Change, archive path, or generated carrier
  is admitted.

#### Scenario: Exact absent Change root resolves to metadata bootstrap

- **GIVEN** a clean owned Work Lane has a valid current Lease
- **AND** no active official Change exists
- **WHEN** prewrite receives exactly `openspec/changes/<change>` for an absent,
  valid Change identifier
- **THEN** it returns a structured block rather than directory write authority
- **AND** its unique next action is the exact prewrite command for
  `openspec/changes/<change>/.openspec.yaml`
- **AND** it does not select archived Change authority.

#### Scenario: Ordinary Commitment attribution replaces bootstrap

- **WHEN** the official Change becomes complete enough to compile its transient
  Commitment
- **THEN** current resolution uses ordinary Commitment and fresh-path
  attribution
- **AND** bootstrap authority grants no additional scope or durable permission.

#### Scenario: Ambiguous or invalid bootstrap fails closed

- **WHEN** the request cannot select one active Change, an identifier is
  invalid, or a requested path is outside the selected official artifact graph
- **THEN** prewrite reports the first exact OpenSpec or uncovered-path gap
- **AND** historical archive authority, another Change, or a fallback path does
  not authorize the write.

#### Scenario: Official creation coexists with another active Change

- **GIVEN** official new-change execution creates metadata beside another active Change
- **WHEN** every prewrite path belongs to that one existing active Change root
- **THEN** current resolution selects it and consumes its official artifact graph
- **AND** public prewrite, pre-tool and Git commit use the same admission owner
- **AND** a missing or mismatched Lease still rejects the request

#### Scenario: Ordinary work remains ambiguous

- **WHEN** product paths or several Change roots cannot identify one selected intent
- **THEN** ETHOS keeps the unresolved intent gap and marks the choice as required
- **AND** its next action inspects the official Change list rather than repeating status
- **AND** explicit plan and proof selection remain bound to the named official intent

### Requirement: Native Documentation Topology

ETHOS SHALL organize governed documentation by function and authority rather
than by `current`/`future` directory names, and SHALL use one explicit rule for
documentation roots, onboarding placement, and README necessity. The physical
shape of ETHOS's own docs is a product projection; adopter repositories retain
their native subject layout under the portable Docs Registry contract.

#### Scenario: Common docs kernel is audited

- **WHEN** documentation governance audits the repository
- **THEN** it checks declared subjects, purposes, authority and reachable
  relationships without requiring evidence or lifecycle directories
- **AND** product roots remain only for distinct subject responsibilities
- **AND** retained evidence follows its producer, consumer, binding and lifetime
- **AND** no ETHOS extension root is mandatory for an adopter

#### Scenario: First-run guidance is placed by function

- **WHEN** ETHOS has one first-run onboarding document
- **THEN** it SHALL live under the `guides` function root as `docs/guides/quickstart.md`
- **AND** links, stable-path metadata, taxonomy metadata, registry output, and
  command examples SHALL resolve to that path
- **AND** the former onboarding root SHALL not remain as a historical habit or
  redirect root

#### Scenario: A documentation directory needs a README

- **WHEN** a documentation directory is evaluated for a README
- **THEN** a README SHALL exist only when it provides real navigation, a
  semantic boundary, or an index for multiple meaningful children
- **AND** a directory with one substantive document SHALL not receive a
  placeholder README merely because the directory exists
- **AND** an empty directory or `.gitkeep` SHALL be removed

#### Scenario: Documentation taxonomy is projected

- **WHEN** the Docs Registry reads the ETHOS documentation tree
- **THEN** role, state, subject, and relation metadata are validated by the
  registry owner and directory names express subject/function rather than
  lifecycle state
- **AND** the registry SHALL report every broken link, stale stable path,
  unindexed document, duplicate subject, and invalid README disposition

#### Scenario: `current`/`future` roots do not become truth lanes

- **WHEN** ETHOS audits docs topology or scaffolds an adopted repository
- **THEN** ETHOS does not require physical `current` or `future` roots, and does
  not accept `current` or `future` as documentation state values
- **AND** present repository truth is proven by HEAD, authority order,
  contracts, evidence, claims, and proof rather than by directory name
- **AND** proposed behavior and acceptance belong in the selected official
  Change; plans, research and revisit conditions supply linked context only
- **AND** no generic intent directory becomes a second change authority

#### Scenario: Product pseudo-lanes do not become common kernel

- **WHEN** ETHOS reports product extension roots
- **THEN** architecture, concepts, governance, plans, research, guides, and
  metadata roots may appear as product extensions
- **AND** contract and evolution labels do not become mandatory replacement
  roots for the removed `current`/`future` lanes

## ADDED Requirements

### Requirement: Invocation-local intent selection

ETHOS SHALL resolve an explicit command or API Change before the invocation's
`ETHOS_CHANGE`, then use applicable native inference. The selected official
intent SHALL remain an input, independent of current mutation authority.
Absent selection SHALL preserve ambiguity; invalid selection SHALL fail closed.

#### Scenario: One selected product operation spans native consumers

- **GIVEN** an owned Work Lane contains two active official Changes
- **WHEN** an invocation selects one complete Change
- **THEN** prewrite, pre-tool, native commit, plan and proof consume that intent
- **AND** explicit command selection overrides the environment input
- **AND** removing the input restores unresolved selection
- **AND** holder mismatch remains a blocking authority gap

### Requirement: Exact proof query selects intent without weakening evidence

A proof query SHALL select the requested official intent, or the intent bound
to an explicitly selected Attestation. When both are explicit, they SHALL agree. Applicable evidence SHALL retain exact
source, policy, integrity, freshness and authority checks. Distinct intents
SHALL remain distinct queries; conflicting evidence for the same query SHALL
not be resolved by choosing a convenient proof.

#### Scenario: Several intents have proofs at the same source

- **WHEN** two official Changes have current proofs for one exact commit
- **THEN** an invocation selects only its own intent's proof
- **AND** an exact Attestation selection overrides the environment choice
- **AND** an unproven selected intent cannot borrow the other proof
- **AND** malformed evidence and same-intent contradictions remain blocking

#### Scenario: Explicit archive cannot borrow another intent's proof

- **GIVEN** two official Changes share the exact source and only one has proof
- **WHEN** archive explicitly requests the unproven Change
- **THEN** admission rejects before changing refs, index or content
- **AND** an environment-selected proof for the other Change cannot satisfy it

#### Scenario: Explicit archive remains selected through post-observation

- **GIVEN** the named Change has a current exact proof
- **WHEN** archive runs with an unrelated or invalid environment selection
- **THEN** admission and post-observation consume the explicit Change
- **AND** unselected intent remains unchanged and replay observes the prior effect

#### Scenario: Explicit proof constraints must agree

- **WHEN** a query names an Attestation and a different or invalid Change
- **THEN** it rejects instead of ignoring either explicit constraint
- **AND** matching active or attested archived intent remains admissible

#### Scenario: Several completed archives retain separate proof identities

- **GIVEN** two distinct accepted intents have verified archive effects
- **WHEN** either is explicitly selected at a later shared source commit
- **THEN** its exact archived acceptance remains available for proof and planning
- **AND** both contributed requirements and product results remain intact
- **AND** absent, unreadable, invalid or unverified intent is not silently accepted

#### Scenario: Full proof shares one current intent observation with audit

- **WHEN** full proof resolves an explicit intent that differs from its ambient default
- **THEN** governance audit consumes that same resolved OpenSpec observation
- **AND** it retains independent adopter, commit and release policy checks
- **AND** a new invocation observes current inputs rather than cached permission

### Requirement: External verification recovery follows its owning prerequisite

Required independent verification SHALL validate the configured provider before
requesting its receipt. Control replacement and publication SHALL share that
owner and report an actionable prerequisite without inventing evidence paths.
Optional unselected verification SHALL preserve local-first behavior.

#### Scenario: The required provider is unavailable

- **WHEN** its protected configuration is missing, unreadable or invalid
- **THEN** admission identifies that provider prerequisite and requests operator repair
- **AND** no repository effect or executable retry is presented as the repair

#### Scenario: A configured provider has no valid receipt

- **WHEN** evidence is absent, outside the protected store, stale or incorrectly bound
- **THEN** admission requests valid evidence from the configured provider
- **AND** its configured store and issuer remain distinct from repository private state
- **AND** valid signatures, freshness and exact bindings are all required for success

### Requirement: Semantic carriers preserve singular authority

ETHOS SHALL preserve one editable owner per proposition across requirements,
design, tasks, implementation and evidence. Human and agent projections SHALL
identify their source and preserve scope and limitations. They SHALL NOT grant
acceptance, task progress, proof or permission by presentation alone.

#### Scenario: A behavior obligation changes

- **WHEN** a behavior changes relative to the accepted capability requirement
- **THEN** the selected Change owns the delta, design and acceptance cases
- **AND** docs and tools reference the owner rather than redefine the requirement
- **AND** disagreement with product invariants or observed execution stays explicit

#### Scenario: Research informs implementation

- **WHEN** sourced research supports a bounded implementation decision
- **THEN** research retains attribution and limits, while the Change owns the
  decision, experiment procedure, acceptance and task progress
- **AND** a summary does not become another editable requirement or result store

### Requirement: Structured documentation metadata preserves meaning

ETHOS SHALL preserve metadata identity, purpose, lifecycle and typed relationships
under valid syntax variations. Invalid declarations and unresolved required
authority targets SHALL be reported. Human-readable and machine-readable
representations SHALL agree on the same declared meaning.

#### Scenario: Equivalent and ambiguous metadata are distinguished

- **WHEN** metadata uses valid quoted scalars or structured relationships
- **THEN** public observation preserves the equivalent meaning
- **AND** duplicate keys and unclosed frontmatter cannot silently pass

#### Scenario: Required guidance is absent or contradictory

- **WHEN** a required authority target is missing or visible state contradicts metadata
- **THEN** public observation identifies the exact disagreement or missing target
- **AND** literal examples cannot satisfy actual reader-guidance obligations

### Requirement: ETHOS directory navigation uses README only

Current ETHOS-authored directory navigation SHALL use a necessary README.md.
Alternate index.md entrypoints and duplicate directory catalogs SHALL be rejected.
Topic links, immutable historical references and unrelated machine indexing
SHALL not be mistaken for authored directory entrypoints.

#### Scenario: A nested directory gains an alternate entrypoint

- **WHEN** authored directory navigation introduces an index.md carrier
- **THEN** quality reports the exact path and README-only correction
- **AND** it does not require a marker-only README as replacement

#### Scenario: One source serves human and agent readers

- **WHEN** rendered, raw or structured access resolves a current rule
- **THEN** the same source, scope, prerequisites and limitations remain available
- **AND** semantic hierarchy and meaningful links preserve progressive detail
  without fragmenting one cohesive explanation or duplicating authority
- **AND** a move repairs affected links without changing subject identity
