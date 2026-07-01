## MODIFIED Requirements

### Requirement: Playbook Projection

ETHOS SHALL discover repo-local skills from ETHOS activation registry inputs,
normalize them into a provider-neutral skill activation IR, and keep
provider-visible skill packages as digest-bound projections over repository
truth rather than truth stores.

#### Scenario: Playbooks are checked

- **WHEN** `ethos playbooks check --json` runs
- **THEN** ETHOS reports normalized V2 registry metadata, package quality,
  package digest state, routing coverage, projection drift, and required or
  advisory gaps

#### Scenario: strict mode rejects placeholder skills

- **GIVEN** a repo-local skill contains only a thin placeholder
- **WHEN** `ethos playbooks check --mode v2-strict --json` runs
- **THEN** ETHOS reports a required gap for official skill package quality

#### Scenario: historical migration fixtures preserve adopter routing evidence

- **GIVEN** a migration fixture contains v1 activation metadata
- **WHEN** Skills V2 migration replay runs
- **THEN** ETHOS preserves readable routing evidence while reporting V2
  migration gaps

### Requirement: Projection Boundary

ETHOS SHALL keep assistant, MCP, ACP, hosted CI, workflow runtimes, external
agent hosts, and provider-visible skill packages as adapters, method packs,
context providers, or projections over repository truth.

#### Scenario: projection drift is audited

- **WHEN** `ethos quality projection-drift --json` runs
- **THEN** ETHOS reports package, registry, generator, and projection drift
  records without accepting host metadata as authority
