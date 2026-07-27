## ADDED Requirements

### Requirement: Derived Collaboration Inbox
The shared inbox MUST be a rebuildable projection of unconsumed intent amendments, conflicts, judgment Attestations, handoff offers, evidence gaps, and next actions; it MUST NOT become a truth store.

#### Scenario: The local inbox index is deleted
- **WHEN** the repository contract, Git facts, and attestations remain available
- **THEN** ETHOS reconstructs an equivalent inbox projection without semantic loss

### Requirement: Vendor-neutral Handoff And Takeover
A handoff package MUST contain the effective contract, exact HEAD/tree/diff, current facts, open plan nodes, attestations, lease generation, and next admissible action, and MUST exclude vendor transcripts and private session state.

#### Scenario: one agent product is taken over by another agent product
- **WHEN** the source task is lost but a valid recovery package exists
- **THEN** the destination reconstructs intent and safe next actions without vendor-specific replay

### Requirement: Agent Protocol Adapter Conformance
Any admitted MCP, A2A, or future agent-protocol adapter MUST consume the same
language-neutral contracts and permission model, remain stateless with respect
to repository truth, and expose only capabilities justified by a concrete
adopter. No named protocol adapter is required for core lifecycle completeness.

#### Scenario: An agent protocol adapter is uninstalled
- **WHEN** its files and manifest are removed
- **THEN** the core lifecycle, repository truth, and other protocol adapters remain intact

### Requirement: Optional Execution Substrates Cannot Own Repository Truth
External agent hosts, method packs, and execution runtimes MAY execute or
project OpenSpec and ETHOS contracts, but MUST remain replaceable and MUST NOT
own repository-local intent, design, task, progress, report, or lifecycle state.

#### Scenario: An ignored method-pack progress tree is written
- **WHEN** a writer targets `.superpowers/sdd/tasks/progress.md` or another path
  declared as repository lifecycle authority
- **THEN** topology policy and prewrite admission block the path even when Git
  ignores it
- **AND** the verdict preserves the declared semantic gap

#### Scenario: An execution runtime is absent or uninstalled
- **WHEN** a coding-agent, graph, durable-service, or method-pack backend is not
  installed
- **THEN** OpenSpec lifecycle, PlanIR, admission, proof, and attestations remain
  complete and executable through another conforming backend

#### Scenario: A runtime backend checkpoints an execution
- **WHEN** a conforming runtime pauses, resumes, or hands off work
- **THEN** its checkpoint remains disposable execution state in a declared
  runtime home
- **AND** accepted progress is reconstructed only from OpenSpec, Git facts,
  PlanIR, and attestations

## MODIFIED Requirements

### Requirement: Playbook Projection
ETHOS SHALL normalize repo-local skills into a provider-neutral activation IR
and keep provider-visible packages as digest-bound projections over repository
truth. Changed-scope routing SHALL be consumed by `plan`; package, portfolio,
routing, and projection checks SHALL be consumed by the admitted
`playbooks-v2` proof gate. No playbooks root SHALL exist.

#### Scenario: Playbooks are checked
- **WHEN** `ethos prove --gate playbooks-v2 --json` runs
- **THEN** it evaluates activation metadata, package quality, package digests,
  route ownership, portfolio coverage, and projection drift
- **AND** required gaps remain subordinate to repository source, contracts,
  OpenSpec, and proof semantics

#### Scenario: strict mode rejects placeholder skills
- **GIVEN** a repo-local skill contains only a thin placeholder
- **WHEN** the `playbooks-v2` gate evaluates it
- **THEN** proof reports a required package-quality gap

#### Scenario: strict mode rejects overlapping skill route owners
- **GIVEN** active repo-local skills declare the same exact changed-path route
  glob
- **WHEN** the `playbooks-v2` gate evaluates them
- **THEN** proof reports deterministic duplicate route ownership
- **AND** the diagnostic does not make skills a repository truth center

#### Scenario: strict mode rejects weak skill entrypoint shape
- **GIVEN** a provider-visible skill has a non-trigger description or hides long
  procedure without declared references or scripts
- **WHEN** the `playbooks-v2` gate evaluates it
- **THEN** proof reports a deterministic skill-quality gap

#### Scenario: historical migration fixtures preserve adopter routing evidence
- **GIVEN** a migration fixture contains historical activation metadata
- **WHEN** skill migration replay runs
- **THEN** ETHOS preserves readable routing evidence while reporting current
  contract gaps

#### Scenario: strict mode enforces portfolio coverage
- **GIVEN** activation metadata declares required primary and single-owner
  subjects
- **WHEN** the `playbooks-v2` gate evaluates it
- **THEN** proof reports deterministic gaps for missing or duplicate active
  primary owners
- **AND** `ethos plan --changed --json` selects skills only from explicit path or
  intent evidence and reports unmatched governed scope

#### Scenario: Skill eval metadata is inspected
- **WHEN** an admitted skill package declares evaluation metadata
- **THEN** the gate validates metric names, bounds, treatment identity, and
  evidence references
- **AND** the metadata is reported as package quality metadata
- **AND** evaluation metadata does not replace package digests or proof evidence
