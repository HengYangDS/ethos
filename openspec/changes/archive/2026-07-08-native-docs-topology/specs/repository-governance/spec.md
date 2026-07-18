## ADDED Requirements

### Requirement: Native Documentation Topology

ETHOS SHALL organize governed documentation by function and authority rather
than by `current`/`future` directory names.

#### Scenario: Common docs kernel is audited

- **WHEN** `ethos quality docs-topology --json` runs
- **THEN** ETHOS requires the common docs kernel: `docs/README.md`,
  `docs/decisions/`, `docs/evidence/`, `docs/history/`, and `docs/reference/`
- **AND** the required kernel is invariant across single-repository, monorepo,
  and multi-repository governed subjects
- **AND** product or adopter extension roots remain optional and domain-bounded
- **AND** required kernel docs expose supported state metadata instead of using
  `current` or `future` as state values

#### Scenario: `current`/`future` roots do not become truth lanes

- **WHEN** ETHOS audits docs topology or scaffolds an adopted repository
- **THEN** ETHOS does not require physical `current` or `future` roots, and
  does not accept `current` or `future` as documentation state values
- **AND** present repository truth is proven by HEAD, authority order, contracts,
  evidence, claims, and proof rather than by directory name
- **AND** unlanded intent belongs in OpenSpec changes, plans, research, or
  decision revisit triggers rather than in a generic future truth store

#### Scenario: Product pseudo-lanes do not become common kernel

- **WHEN** ETHOS reports product extension roots
- **THEN** architecture, concepts, governance, plans, research, start, and
  metadata roots may appear as product extensions
- **AND** contract and evolution labels do not become mandatory replacement
  roots for the removed `current`/`future` lanes
