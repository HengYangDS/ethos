## ADDED Requirements

### Requirement: Agentic issue intake preserves repository truth boundaries

ETHOS SHALL treat external issue trackers, managed-agent platforms, automation
canvases, and coding-agent runtimes as adapters or projections unless a future
accepted decision explicitly changes their binding class.

#### Scenario: External signal enters intake without authorizing mutation

- **WHEN** an external issue, board event, scheduled automation, webhook, agent
  comment, PR/MR, or task state is observed
- **THEN** ETHOS SHALL normalize it as an intake envelope or issue candidate
- **AND** it SHALL NOT authorize tracked mutation, land, accepted-root closeout,
  publication, or release by itself.

#### Scenario: Agent backend produces candidate material

- **WHEN** a coding-agent backend produces a patch, branch, PR/MR, task log, or
  completion status
- **THEN** ETHOS SHALL treat it as candidate material or evidence candidate
- **AND** repository truth SHALL require HEAD-bound evidence, bounded claim, and
  judged chronicle before promotion.

### Requirement: Agent dispatch requires explicit admission boundary

ETHOS SHALL require a dispatch envelope before any agent backend performs
mutating repository work under ETHOS governance.

#### Scenario: Dispatch envelope bounds execution

- **WHEN** ETHOS dispatches work to an agent backend
- **THEN** the dispatch envelope SHALL bind the change id, owner, target root,
  Work Lane or import branch, expected head, allowed paths, forbidden paths,
  backend capability profile, required gates, evidence requirements, rollback
  plan, and publication boundary
- **AND** normal edits SHALL NOT target the accepted root or candidate worktree.

### Requirement: Bounded repository evolution moves repeated failures upstream

ETHOS SHALL define bounded repository evolution as evidence-bound improvement
of earlier constraints, not autonomous authorization.

#### Scenario: Repeated failure becomes upstream guardrail

- **WHEN** the same invalid state recurs after late discovery
- **THEN** ETHOS SHALL prefer an upstream rule, hook, scaffold, template, schema,
  or default after diagnosis, carrier, evidence, claim, and chronicle
- **AND** it SHALL NOT silently rewrite authority, proof, publication, or release
  policy because an agent run recommended it.
