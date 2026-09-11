## REMOVED Requirements

### Requirement: Playbook Projection

**Reason**: Development-generation modes and historical migration replay no
longer describe the supported skill contract.

**Migration**: Skill portfolio validation retains package, route, coverage,
evaluation and boundary checks through one owner; invalid old input is rejected.

## ADDED Requirements

### Requirement: Skill portfolio validation

ETHOS SHALL expose repo-local skill portfolio validation through the stable
`skills` gate. One skill owner SHALL validate original activation inputs,
package quality, routing, composition and retirement, then project explicit
verdicts and gaps. Skills remain below repository truth.

#### Scenario: Skills are checked through one owner

- **WHEN** `ethos prove --gate skills --json` runs
- **THEN** it uses the same portfolio owner as repository audit and planning
- **AND** the report has no development-generation mode or duplicate compliance score

#### Scenario: Placeholder and weak entrypoint are rejected

- **WHEN** a skill lacks required content or a usable trigger and entrypoint
- **THEN** the report retains precise package-quality failures

#### Scenario: Overlapping route owners are rejected

- **WHEN** active skills declare conflicting routes or duplicate primary owners
- **THEN** the report identifies those conflicts without granting skill authority

#### Scenario: Missing portfolio coverage is reported

- **WHEN** declared required primary subjects have no active owner
- **THEN** the report exposes missing coverage and the exact owner map

#### Scenario: Unsupported activation remains invalid

- **WHEN** old or future activation input does not satisfy the supported schema
- **THEN** the original input is rejected rather than normalized into compatibility

#### Scenario: Skill evaluation metadata remains evidence

- **WHEN** a package declares evaluation metrics, treatment identity and evidence references
- **THEN** the same package owner validates them without converting them into task progress

## MODIFIED Requirements

### Requirement: Projection Boundary

ETHOS SHALL keep assistant, MCP, ACP, hosted CI, workflow runtimes, external
agent hosts, and provider-visible skill packages as adapters, method packs,
context providers, or projections over repository truth.

#### Scenario: projection drift is audited

- **WHEN** `ethos prove --gate skills --json` runs
- **THEN** it reports package and registry drift without accepting host metadata as authority
