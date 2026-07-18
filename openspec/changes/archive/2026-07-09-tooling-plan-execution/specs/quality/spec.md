## ADDED Requirements

### Requirement: Executable tooling adoption gates

ETHOS SHALL activate roadmap tools as quality gates only after every owner
surface exists: tool catalog, config owner, reusable runner, CI or hook
projection, and tests or proof coverage.

#### Scenario: Dependency hygiene is package-local and non-vulnerability evidence

- **WHEN** the dependency hygiene gate runs
- **THEN** ETHOS SHALL invoke `tools/ci/scripts/run-dependency-hygiene.sh`
- **AND** the runner SHALL execute `deptry` per Python distribution rather than
  treating the workspace root as one runtime package
- **AND** the resulting evidence SHALL be local owner-gate evidence
- **AND** it SHALL NOT claim vulnerability scanning or hosted CI success.

#### Scenario: Prose and schema hygiene are report-first gates

- **WHEN** prose spelling or JSON Schema hygiene runs
- **THEN** ETHOS SHALL invoke the reusable owner scripts
- **AND** the prose gate SHALL NOT rewrite digest-bound evidence or archived
  records
- **AND** the schema gate SHALL validate schema documents without replacing
  command payload validation.
