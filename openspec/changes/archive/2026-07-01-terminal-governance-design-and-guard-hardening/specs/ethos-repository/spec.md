## ADDED Requirements

### Requirement: OpenSpec-first governance mutation
ETHOS SHALL require a dedicated OpenSpec change, or an explicit active
non-complete OpenSpec change attachment, before non-trivial tracked mutations
to repository governance semantics.

#### Scenario: Governance design starts with OpenSpec
- **WHEN** an agent plans to change rules, skills, hook policy, product shape,
  architecture design, or governance workflow semantics
- **THEN** the agent verifies the relevant OpenSpec change with
  `openspec status --change <change> --json` before tracked mutation

#### Scenario: Complete changes are not reused silently
- **WHEN** all existing relevant OpenSpec changes are complete
- **THEN** ETHOS treats them as insufficient carriers for new semantic work
- **AND** the agent creates or selects a new non-complete change before editing

### Requirement: Context-bound mutation admission
ETHOS SHALL bind tracked mutation admission to explicit repository root,
checkout role, editor root, and target paths before a write-capable tool can
mutate tracked files.

#### Scenario: Implicit-root mutation is blocked
- **WHEN** a write-capable tool does not carry an explicit target root matching
  the current Work Lane
- **THEN** ETHOS blocks the tracked write before filesystem mutation
- **AND** reports the expected root, actual root, checkout role, and target
  paths

#### Scenario: Manual prewrite is degraded mode
- **WHEN** a host cannot install a pre-tool mutation hook
- **THEN** the agent MUST run `ethos lane prewrite <paths> --editor-root <root>
  --require-editor-root --json` before tracked writes
- **AND** the terminal design still treats manual prewrite as weaker than a
  bound mutation hook

### Requirement: Failure blocking moves upstream
ETHOS SHALL promote repeated late failures to earlier controls until the normal
workflow prevents the invalid state before mutation when practical.

#### Scenario: Late failure is promoted
- **WHEN** a repeated violation is detected after write, commit, CI, land, or
  publish
- **THEN** ETHOS records the diagnosis and promotes the control toward rule,
  hook, scaffold/template, or schema/default placement

#### Scenario: Bypassable guidance is incomplete
- **WHEN** a normal mutation path can bypass a documented guard
- **THEN** ETHOS treats the guard design as incomplete until the guard is bound
  to the mutation capability or an explicit degraded mode is declared

### Requirement: Productized OpenSpec carrier governance
ETHOS SHALL treat OpenSpec as the repository case and specification carrier,
with accepted specs, active changes, archived changes, capability profiles,
claims, and evidence refs serving distinct product duties.

#### Scenario: Capability routing uses live capability profiles
- **WHEN** an active OpenSpec proposal routes a governance semantic change
- **THEN** the primary capability name resolves directly to a live
  `openspec/specs/<capability>/spec.md`
- **AND** the sibling `capability.toml` records family, owner boundary, primary
  invariant, routing question, boundary rules, and proof profile metadata

#### Scenario: Proposal metadata explains ownership and stance
- **WHEN** an active OpenSpec proposal lists a capability impact
- **THEN** the proposal records the stable subject, reuse stance, change
  stance, lifecycle facet, surface facet, and authority facet for that impact
- **AND** secondary impacts do not create duplicate normative owners

#### Scenario: New or extracted capability topology requires design
- **WHEN** an OpenSpec change introduces a new capability or extracts behavior
  from an existing capability
- **THEN** the change includes `design.md`
- **AND** the design explains why reuse or extension is insufficient, the
  official-vs-ETHOS validation boundary, proof impact, and rollback strategy

#### Scenario: Archive closeout protects live specs and evidence refs
- **WHEN** ETHOS closes out an OpenSpec change through the archive path
- **THEN** it verifies live spec edits are scoped to the archived deltas
- **AND** archived task state, archive directory identity, Markdown links, claim
  refs, and evidence refs remain valid after the archive move

#### Scenario: Adoption scaffold includes usable OpenSpec substrate
- **WHEN** `ethos init` or `ethos adopt` creates a governed repository substrate
- **THEN** the scaffold includes OpenSpec config, README files, change
  templates, capability templates, `specs/families.toml`, and
  profile-appropriate first capability profiles when the profile knows the
  governed domain
- **AND** an empty `openspec/` directory is not reported as a complete
  governance scaffold
