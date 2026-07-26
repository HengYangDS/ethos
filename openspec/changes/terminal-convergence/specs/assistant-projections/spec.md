## ADDED Requirements

### Requirement: Derived Collaboration Inbox
The shared inbox MUST be a rebuildable projection of unconsumed intent amendments, conflicts, decisions, handoff offers, evidence gaps, and next actions; it MUST NOT become a truth store.

#### Scenario: The local inbox index is deleted
- **WHEN** the repository contract, Git facts, and attestations remain available
- **THEN** ETHOS reconstructs an equivalent inbox projection without semantic loss

### Requirement: Vendor-neutral Handoff And Takeover
A handoff package MUST contain the effective contract, exact HEAD/tree/diff, current facts, open plan nodes, attestations, lease generation, and next admissible action, and MUST exclude vendor transcripts and private session state.

#### Scenario: A Codex task is taken over by a different agent product
- **WHEN** the source task is lost but a valid recovery package exists
- **THEN** the destination reconstructs intent and safe next actions without vendor-specific replay

### Requirement: Protocol-first Agent Surfaces
MCP MUST expose resources, prompts, and guarded tools; A2A MUST cover discovery, delegation, handoff, and takeover; both MUST consume the same language-neutral contracts and permission model.

#### Scenario: An agent protocol adapter is uninstalled
- **WHEN** its files and manifest are removed
- **THEN** the core lifecycle, repository truth, and other protocol adapters remain intact

### Requirement: Optional Execution Substrates Cannot Own Repository Truth
External agent hosts, method packs, and execution runtimes MAY execute or
project OpenSpec and ETHOS contracts, but MUST remain replaceable and MUST NOT
own repository-local intent, design, task, progress, report, or lifecycle state.

#### Scenario: An ignored method-pack progress tree is written
- **WHEN** a writer targets `.superpowers/sdd/tasks/progress.md` or another path
  declared as external shadow authority
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
