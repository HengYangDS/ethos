# ETHOS Assistants

## Purpose

ETHOS SHALL expose assistant, MCP, ACP, context, and repo-local skills as thin
projections over repository truth.

## Requirements

### Requirement: Playbook Projection
ETHOS SHALL discover repo-local skills from `.agents/skills/activation.toml`
and keep those skills as routing aids rather than truth stores.

#### Scenario: Playbooks are checked
- **WHEN** `ethos playbooks check --json` runs
- **THEN** ETHOS reports skill records, routing subjects, commands, and
  required gaps from tracked playbook configuration

### Requirement: Projection Boundary
ETHOS SHALL keep assistant, MCP, ACP, hosted CI, workflow runtimes, and external
agent hosts as adapters, method packs, context providers, or thin projections
over repository truth.

#### Scenario: Adapter surfaces are audited
- **WHEN** ETHOS audits product boundaries
- **THEN** adapters do not replace kernel models, schemas, tests, docs, or
  repository source as truth stores
