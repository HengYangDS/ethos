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

### Requirement: Linked Work Lane retirement has one exact effect

Landed and superseded retirement SHALL share one strict request and owner,
binding actor, mode, lane ref/HEAD, clean linked path and accepted ref/HEAD.
Consumed Leases SHALL bind only lane ref, holder, generation and expiry under
SQLite transaction; Git facts remain independent. Remove only the selected clean
checkout and compare-delete its exact ref in a transaction verifying accepted.

#### Scenario: Landed preview supplies an executable exact continuation

- **WHEN** an admitted preview selects one landed branch without an expected HEAD
- **THEN** its next command binds that branch's observed HEAD, not accepted's HEAD
- **AND** executing it rechecks all current admission and exact-effect conditions
- **AND** an explicitly supplied expected HEAD is preserved, never silently replaced

#### Scenario: Nontracked content requires an explicit disposition

- **WHEN** a linked worktree contains nontracked content, including ignored evidence
- **THEN** automatic retirement preserves the worktree, refs, Lease and content
- **AND** the preview reports its native footprints and existing lifecycle labels
- **AND** neither Git ignore rules nor a lifecycle label authorize deletion
- **AND** continuation requests existing exact content review before separately authorized disposal
- **AND** required custody is preserved outside the retiring resource before disposal

#### Scenario: Nontracked content appears after planning

- **WHEN** ignored content appears before an unreviewed retirement effect or receipt recovery
- **THEN** fresh effect admission refuses deletion and selects a new content review
- **AND** a reviewed receipt still refuses changed content, foreign ownership and active consumers

#### Scenario: Exact Lease observation changed after planning

- **WHEN** a planned live or expired Lease differs in lane ref, holder ref,
  generation, or expiry at effect time
- **THEN** ETHOS blocks the effect
- **AND** it leaves the linked worktree, lane ref, and current Lease intact.

#### Scenario: A Lease appears after an absent observation

- **WHEN** landed retirement planned against an absent Lease and a row for the
  target lane exists when the SQLite transaction re-observes it
- **THEN** ETHOS blocks the effect
- **AND** it does not delete the linked worktree, branch, or new Lease.

#### Scenario: Accepted ref changes during linked retirement

- **WHEN** the accepted ref differs after the worktree is removed but before the
  lane ref transaction commits
- **THEN** the Git ref transaction rejects lane-ref deletion
- **AND** the SQLite Lease deletion rolls back
- **AND** ETHOS reports a blocked partial transition without claiming retirement.

#### Scenario: Lease commit fails after Git removal

- **WHEN** the clean worktree and exact lane ref were removed but the SQLite
  transaction cannot commit
- **THEN** ETHOS re-observes the ref, worktree, and Lease postconditions
- **AND** it reports the exact non-terminal state without claiming retirement.

## ADDED Requirements

### Requirement: Archive completion requires exact postimage quality

Archive completion SHALL require native OpenSpec validity and the existing
applicable proof for the actual resulting HEAD. Prearchive proof and Git effect
evidence SHALL NOT establish postimage quality. Pending verification SHALL
preserve and report the observed committed effect without claiming completion.

#### Scenario: Archive changes an input consumed by a repository check

- **WHEN** prearchive proof passes but the resulting source has no passing applicable proof
- **THEN** archive reports a blocked committed repair boundary with the actual HEAD
- **AND** its continuation selects that HEAD's existing proof command and repository root
- **AND** stale, failed or unrelated proof cannot make archive completion pass

#### Scenario: Exact postimage proof is available

- **WHEN** native OpenSpec validity and exact postimage proof both pass
- **THEN** archive completion passes using the original effect evidence
- **AND** replay neither repeats Git effects nor reruns checks

### Requirement: Current prose preserves meaning without copied execution state

ETHOS SHALL keep obligations, dependency order, task progress and observed
results at their existing semantic owners. Current entrypoints SHALL expose the
relevant route without requiring historical narratives. Reducing text or token
cost SHALL NOT remove valid constraints, functionality, performance or acceptance.

#### Scenario: Completed observations leave the current plan entry

- **WHEN** historical execution detail is removed from a current entrypoint
- **THEN** exact source bytes remain recoverable through the existing history owner
- **AND** every still-valid obligation remains in its current owner or explicitly open
- **AND** task status and dated results are referenced rather than copied into another ledger

#### Scenario: A reader needs the next useful action

- **WHEN** a person or agent reads the current convergence entry
- **THEN** it reaches the existing task and authority owners without loading historical results
- **AND** local, installed, hosted and actual-use claims remain distinct
- **AND** measured text or token reduction alone does not prove semantic preservation

### Requirement: Accepted feedback closes through demonstrated improvement

ETHOS SHALL preserve each accepted feedback obligation's declared source scope,
responsible owner and acceptance conditions in official OpenSpec. Closure SHALL
require a demonstrated improvement, current evidence of prior satisfaction, or
an explicitly justified supersession or rejection. Missing evidence SHALL remain
open. A note, checkbox, extra artifact or larger skill SHALL NOT establish closure.

#### Scenario: A local example expresses a global obligation

- **WHEN** accepted feedback uses one defect to require a repository-wide principle
- **THEN** a bounded repair preserves the wider obligation and its remaining gaps
- **AND** closing the example does not close unverified sibling consumers

#### Scenario: A proposed resolution contains only prose

- **WHEN** feedback requires changed behavior but the candidate supplies only a retrospective or unchecked claim
- **THEN** the existing acceptance owner refuses closure for missing execution evidence
- **AND** neither additional headings nor task completion flags satisfy that obligation

#### Scenario: A mechanism has been changed and verified

- **WHEN** the responsible implementation or native policy changes and its distinguishing counterexample passes
- **THEN** evidence binds the candidate, applicable policy, environment and actual consumer
- **AND** required installation, publication or use observations remain separate conditions
- **AND** stale, contradictory or unrelated evidence cannot close the obligation

#### Scenario: A failure recurs despite an existing safeguard

- **WHEN** the same failure recurs after a claimed correction
- **THEN** closure reopens the failed safeguard's owner and examines why its prior check or guidance was ineffective
- **AND** the replacement removes the disproved path rather than adding another equivalent workaround

#### Scenario: A feedback procedure is selected during planning

- **WHEN** the current planning subject is feedback closure
- **THEN** the existing skill compiler selects repository governance and its canonical feedback rule
- **AND** package integrity and routing evidence do not claim host loading or successful agent behavior

#### Scenario: Feedback is already satisfied or contradicted by current facts

- **WHEN** current evidence establishes prior satisfaction or a justified rejection
- **THEN** the resolution preserves that evidence and its source scope without forcing unnecessary edits
- **AND** structural validation does not certify unrecorded conversation or complete intent understanding

### Requirement: Feedback preserves each repository's domain authority

ETHOS SHALL support feedback closure for self-hosting and adopted repositories
under their own accepted business meaning. The repository SHALL own goals,
constraints, success criteria and authorized judgments. Shared mechanisms and
capability adapters SHALL NOT replace those meanings with ETHOS-specific metrics
or imply business success from technical verification alone.

#### Scenario: Technical checks pass while a required business outcome fails

- **WHEN** a selected domain obligation has failed, missing or stale outcome evidence
- **THEN** its completion claim remains open despite green technical checks
- **AND** independently admissible source work can continue without claiming that outcome

#### Scenario: Different domains use the same protocol

- **WHEN** two adopters declare different business meanings and evidence providers
- **THEN** each is evaluated against its own accepted criteria through the shared owner
- **AND** neither acquires another repository's business policy, private context or authority

#### Scenario: A fresh authored correction follows an archived Change

- **WHEN** patch checks pass but requested paths are outside the attested archive effect's scope
- **THEN** admission remains blocked and directs the actor to fresh official intent
- **AND** it does not request another equivalent patch or expand historical write permission

### Requirement: Feedback can revise its governing model

Feedback SHALL distinguish implementation failure from inadequate methods,
governing models or problem framing. A demonstrated model gap SHALL select the
smallest sufficient Model Promotion, recompile dependent meanings, migrate
consumers and retire replaced mechanisms. Changes to goals or standards SHALL
require authorized intent alignment rather than outcome-driven relaxation.

#### Scenario: Local repairs do not resolve the contradiction

- **WHEN** valid counterexamples expose a missing distinction in the current model
- **THEN** the owning model is reconsidered before another equivalent local patch
- **AND** acceptance exercises the counterexample and preserved valid behavior after migration

#### Scenario: The feedback safeguard itself produces false closure

- **WHEN** its observations, interpretation or judgment contradict actual outcomes
- **THEN** the affected closure and safeguard are reopened for correction
- **AND** a note, new abstraction name or lower threshold cannot establish improvement

### Requirement: Publication continuation requests only missing observations

Locally ready publication with an unprobed configured peer SHALL select exact
remote observation before suggesting repeated local verification. The command
SHALL bind the current source ref and HEAD. Cached tracking, local proof and
remote effects SHALL remain distinct evidence; observation grants no authority.

#### Scenario: A configured peer has not been probed

- **WHEN** local publication readiness passes with an unprobed peer
- **THEN** continuation selects the public exact-ref remote observation command
- **AND** cached synchronized tracking cannot replace that observation
- **AND** no local verification or remote publication effect is repeated

#### Scenario: No remote observation is available

- **WHEN** publication is local-only or its peers are unconfigured or unavailable
- **THEN** existing local fallback guidance and its evidence state remain available
- **AND** local readiness failure still blocks publication

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


### Requirement: Accepted history repair preserves original acceptance provenance

Accepted-source consumers SHALL resolve original acceptance through validated
completed history-repair relations for the exact accepted ref. They SHALL retain
the original Attestation and distinguish its coordinates from current source
coordinates. Equal trees alone SHALL NOT establish acceptance or authority.

#### Scenario: A repaired accepted source is proved and released

- **WHEN** governed history repair replaces an accepted commit and a new exact-source proof succeeds
- **THEN** closeout and release retain the original accepted-effect Attestation
- **AND** validated repair relations explain the current source coordinates
- **AND** current actor-owned Lease admission is independent of the proof's original execution root

#### Scenario: Related bytes do not prove current authority

- **WHEN** repair provenance is absent, ambiguous, cyclic or does not select the accepted ref
- **THEN** acceptance is not inferred from matching trees or a historical identity
- **AND** unrelated plans are not decoded as potential authority for that source
