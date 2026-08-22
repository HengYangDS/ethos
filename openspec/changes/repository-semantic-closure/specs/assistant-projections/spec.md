## MODIFIED Requirements

### Requirement: Playbook Projection

ETHOS SHALL discover repo-local skills from ETHOS activation registry inputs,
normalize them into a provider-neutral skill activation IR, and keep
provider-visible skill packages as digest-bound projections over repository
truth rather than truth stores.

#### Scenario: Playbooks are checked

- **WHEN** `ethos prove --gate playbooks-v2 --json` runs
- **THEN** ETHOS reports normalized V2 registry metadata, package quality,
  package digest state, routing coverage, projection drift, portfolio coverage,
  portfolio design diagnostics, and required or advisory gaps

#### Scenario: strict mode rejects placeholder skills

- **GIVEN** a repo-local skill contains only a thin placeholder
- **WHEN** `ethos prove --gate playbooks-v2 --json` runs
- **THEN** ETHOS reports a required gap for official skill package quality

#### Scenario: strict mode rejects overlapping skill route owners

- **GIVEN** active repo-local skills declare the same exact changed-path route
  glob in activation metadata
- **WHEN** `ethos prove --gate playbooks-v2 --json` runs
- **THEN** ETHOS reports a deterministic `skill_portfolio_path_glob_duplicate`
  required gap
- **AND** the payload exposes `portfolio_design` diagnostics without making
  skills a repository truth center

#### Scenario: strict mode rejects weak skill entrypoint shape

- **GIVEN** a provider-visible skill entrypoint has a non-trigger description or
  hides long procedure in `SKILL.md` without `references/` or `scripts/`
- **WHEN** `ethos prove --gate playbooks-v2 --json` runs
- **THEN** ETHOS reports a deterministic skill quality required gap

#### Scenario: historical migration fixtures preserve adopter routing evidence

- **GIVEN** a migration fixture contains v1 activation metadata
- **WHEN** Skills V2 migration replay runs
- **THEN** ETHOS preserves readable routing evidence while reporting V2
  migration gaps

#### Scenario: strict mode enforces portfolio coverage

- **GIVEN** activation metadata declares required primary subjects and
  single-owner subjects
- **WHEN** `ethos prove --gate playbooks-v2 --json` runs
- **THEN** ETHOS reports deterministic required gaps for missing active primary
  owners and duplicate active primary owners
- **AND** the check payload exposes the portfolio coverage contract and owner
  map without treating skills as repository truth above source, tests, schemas,
  docs, OpenSpec, claims, evidence, or command JSON

#### Scenario: Skill eval metadata is inspected
- **WHEN** a skill package declares eval metadata
- **THEN** ETHOS validates the metric names, pass@k bounds, instability-gap bounds, treatment id, and evidence refs
- **AND** the metadata is reported as package quality metadata
- **AND** eval metadata does not replace package digests, proof commands, claims, or evidence
