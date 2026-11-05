## MODIFIED Requirements

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

#### Scenario: A package that no record routes is reported

- **WHEN** a package directory under the Skills root holds `SKILL.md` and neither an active record nor a retirement routes it
- **THEN** the report names it with `skill_package_unregistered`
- **AND** a partial registry no longer passes while other packages stay routed elsewhere
