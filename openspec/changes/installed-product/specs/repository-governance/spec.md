## ADDED Requirements

### Requirement: Adoption rejects invalid existing intent configuration before binding

Adoption SHALL consume the existing official OpenSpec configuration audit before
writing any binding. Preserving authored bytes SHALL NOT imply accepting an
invalid carrier. CLI, SDK and MCP SHALL share this decision and retain its gaps.

#### Scenario: Existing OpenSpec configuration fails its owning audit

- **WHEN** adoption previews or applies with malformed, missing-schema or forbidden-root configuration
- **THEN** it reports the OpenSpec path conflict and the owning audit's reasons
- **AND** no profile or configuration is written, existing bytes remain unchanged, and continuation requires resolving that conflict

#### Scenario: A valid authored configuration differs from the default

- **WHEN** its owning audit passes
- **THEN** adoption preserves its exact bytes and does not replace its schema, context or rules
- **AND** this preservation does not certify full mutation readiness or executed proof

## MODIFIED Requirements

### Requirement: Minimal Adoption Binding

ETHOS SHALL own one typed profile binding and compose official OpenSpec
configuration initialization and readiness. Optional domain, documentation,
Skills and provider surfaces SHALL retain their own owners.

#### Scenario: A repository is adopted

- **WHEN** authorized exact-HEAD adoption targets an eligible Git repository
- **THEN** it plans the ETHOS profile and the selected native OpenSpec configuration
- **AND** no placeholder, generic project context, artifact rules or unrelated surface is invented

#### Scenario: Default binding serializes from the typed contract

- **WHEN** ETHOS compiles its default profile binding
- **THEN** one strict frozen declaration validates the in-memory value and native TOML serialization
- **AND** no profile registry, renderer manifest, digest snapshot or template environment becomes a second owner

#### Scenario: Existing bootstrap content differs

- **WHEN** an ETHOS binding is invalid, symlinked, non-regular or unreadable
- **THEN** adoption refuses the exact path without an implicit merge, alias or migration
- **AND** a valid existing profile is preserved, while an empty ETHOS profile may be replaced
- **AND** an empty native OpenSpec configuration remains an invalid existing carrier rather than absent configuration

#### Scenario: Unselected optional capabilities do not block a new adopter

- **WHEN** a valid adopter has not selected optional documentation, Skills, schemas, generated assets or hosted providers
- **THEN** their absence does not become a bootstrap gap
- **AND** native configuration and applicable material-scope correctness remain independently enforced

#### Scenario: Configuration is absent

- **WHEN** adoption initializes native configuration
- **THEN** its bytes match the official initializer's default configuration
- **AND** a first Change is usable through the official CLI without generated directory anchors

#### Scenario: Native meaning cannot be preserved

- **WHEN** configuration fields, schema resolution, rule applicability or required templates fail native validation
- **THEN** adoption blocks before writing and retains native warnings and reasons
- **AND** unavailable supply or observation remains UNKNOWN rather than malformed-user-content blame
- **AND** a pointer-only external store receives an explicit unsupported-operation reason, independent of host registration

#### Scenario: Authored configuration and custom schemas already exist

- **WHEN** the official reader selects valid YAML or YML and resolves repository-owned schema inputs
- **THEN** their exact bytes remain unchanged
- **AND** an explicit expected-plan digest rejects changed configuration, schemas or templates before apply

#### Scenario: A file effect fails

- **WHEN** an admitted write or its native postcondition fails
- **THEN** every independently safe owned write is compensated without overwriting intervening content
- **AND** incomplete or unobserved recovery is not reported as successful adoption
- **AND** the initiating failure and each failed compensation remain observable
- **AND** no multi-file crash-atomic guarantee is inferred from individual atomic replacements

### Requirement: Current product revision one-binding external-adopter observation is bounded and durable

ETHOS SHALL distinguish its sole binding from native initialization effects when
observing isolated adopter clones. Evidence SHALL bind exact inputs and effects
without private adopter coupling or claims beyond the exercised boundary.

#### Scenario: Missing binding is created without unrelated writes

- **WHEN** an isolated clone lacks the ETHOS profile
- **THEN** preview reports that binding and any required native configuration initialization separately
- **AND** authorized exact-HEAD apply preserves the source clone and unrelated files

#### Scenario: Existing adopter surfaces reject generic replacement

- **WHEN** an existing binding conflicts or its native configuration is invalid
- **THEN** no implicit merge, alias or replacement hides the conflict
- **AND** the result preserves the precise owning reason

#### Scenario: Current observation is promoted without private coupling

- **WHEN** an observation is retained as product evidence
- **THEN** it binds revisions, observed outcomes and the raw-bundle identity without host paths or credentials
- **AND** native backend parity, full semantic correctness, hosted execution and independent review require their own evidence

### Requirement: Exact accepted proposal retirement

ETHOS SHALL retire a proposal through its existing publication effect only after
fresh observations establish accepted absorption, closed review, and exact
peer ref identity. Retirement SHALL NOT depend on main release convergence,
active Change presence, or a historical authoring Lease.

#### Scenario: Accepted contribution no longer needs its review projection

- **WHEN** a proposal tip is reachable from local accepted dev and the selected
  peer's accepted dev, and no matching review remains open
- **THEN** public publication can delete that exact proposal by peer-local CAS
- **AND** a delayed main release does not block retirement

#### Scenario: Incomplete or unrelated evidence cannot authorize deletion

- **WHEN** absorption is absent, a review is open, the peer tip changed, or a
  required observation is unavailable
- **THEN** retirement preserves the proposal and reports the owning boundary
- **AND** patch equivalence, a user-supplied closed flag, and unrelated review
  results cannot substitute for the required observations

#### Scenario: Replayed deletion converges without repeated effects

- **WHEN** one peer was retired before interruption and another remains pending
- **THEN** recovery reobserves the same exact plan and skips the absent peer
- **AND** remaining peers are independently readmitted before deletion

#### Scenario: Verified history repair preserves accepted contribution identity

- **WHEN** an immutable, completed ETHOS history-repair effect establishes one
  exact old proposal tip to replacement mapping, and the replacement is absorbed
  by local and peer accepted dev
- **THEN** retirement recognizes that verified relationship without restoring
  the old history
- **AND** missing, ambiguous or invalid repair evidence cannot authorize deletion

#### Scenario: Publication retains its original positive-object guarantees

- **WHEN** the existing publication command projects commits or annotated tags
- **THEN** target updates still match the exact trusted source object
- **AND** retirement mode cannot delete protected, candidate, or tag resources

#### Scenario: Verified native refresh preserves the accepted contribution

- **GIVEN** validated native refresh evidence binds the old contribution, candidate
  and refreshed output, and the proposal is contained in the old input history
- **WHEN** isolated native composition reproduces the exact output tree and the
  output is absorbed by local and peer accepted dev
- **THEN** public retirement consumes that relationship without recreating an
  active historical Change, Lease or old branch
- **AND** current closed-review, exact peer identity and fresh CAS checks still apply
- **AND** missing, invalid, ambiguous or nonconserving evidence does not authorize
  deletion, while unavailable required observations remain explicit

#### Scenario: Remote retirement exposes separately admitted local closure

- **WHEN** selected peer retirement has completed but a same-named local proposal remains
- **THEN** the result preserves confirmed remote effects and reports `retirement_pending`
- **AND** its continuation invokes the native local retirement owner with exact root and OIDs
- **AND** the publication receipt does not authorize that local mutation
- **AND** replay reports full retirement only after the requested local projections are absent

#### Scenario: Local retirement shares verified accepted-contribution meaning

- **WHEN** a local proposal is accepted by ancestry, verified signature repair or conserved native refresh
- **THEN** its native retirement and compensation consume the same contribution observer as publication
- **AND** topic role, current accepted OID, no linked worktree, no Lease and exact CAS still apply
- **AND** missing, invalid or nonconserving evidence blocks deletion; unavailable conservation remains UNKNOWN
- **AND** failed local effect evidence preserves or compensates the exact original ref

## ADDED Requirements

### Requirement: Explicit repository identity transition

ETHOS SHALL permit a typed, explicitly authorized repository identity transition
through existing GitEffect, TransitionPlan, Attestation and CAS owners. Each
authorization SHALL bind one target ref, exact pre/post commits and trees,
old/new identities, one object database, accepted intent/proof, actor and current
Lease generation. Ordinary cross-identity CAS SHALL remain rejected.

#### Scenario: Identity changes progress through independently authorized stages

- **WHEN** a proven new-identity work lane explicitly integrates into an old-identity candidate
- **THEN** only the exact admitted target ref transitions and its result uses the new identity
- **AND** accepted and release refs may transition later under separate fresh authorizations
- **AND** unrelated refs are not changed to manufacture a global singleton identity

#### Scenario: Missing or contradictory authority cannot cross identities

- **WHEN** the semantic operation is unsupported or database identity, ancestry, target coordinates, intent/proof, actor or Lease generation is missing, stale or contradictory
- **THEN** admission preserves all refs and reports the owning refusal
- **AND** a shared object database does not make different profiles equivalent

#### Scenario: A completed authorization is not consumed twice

- **WHEN** the same exact transition is replayed after completion
- **THEN** recovery observes the original effect and result without repeating its mutation
- **AND** the original exact coordinates resolve to the original Attestation while invented coordinates remain rejected
- **AND** a later target-ref transition requires its own authorization
- **AND** partial or unknown execution is observed before any further effect

#### Scenario: Ref completion leaves checkout materialization pending

- **WHEN** the exact ref transition succeeds but its linked checkout synchronization fails
- **THEN** preview reports pending materialization rather than completed acceptance
- **AND** authorized recovery validates the original result and synchronizes only the admitted preimage without repeating the ref effect
- **AND** missing authorization, stale coordination and unrelated user edits remain rejected
- **AND** restored original content remains admissible despite stale stat metadata, without refreshing index bytes during observation

#### Scenario: Renaming does not retain an obsolete current product identity

- **WHEN** a target has completed its admitted old-to-new identity transition
- **THEN** its current results use the new identity without aliases or compatibility mappings
- **AND** old revisions remain historical or not-yet-transitioned stage inputs
- **AND** no temporary profile rollback or history rewrite is required

#### Scenario: A ref program contains both migration and new publication refs

- **WHEN** an admitted branch identity transition also creates a signed tag or follows a declared accepted-mirror policy
- **THEN** only existing branches whose identities change receive identity edges
- **AND** new tags and unchanged-identity refs remain in the same exact ref program without invented pre-identities

#### Scenario: Preview preserves the selected transition

- **WHEN** an identity transition is previewed before applying it
- **THEN** no ref changes and its continuation retains the exact root, source, target and explicit identity mode
- **AND** a future signed tag is distinguished from the branch scope already admitted by that preview
