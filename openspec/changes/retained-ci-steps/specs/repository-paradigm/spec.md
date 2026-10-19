## MODIFIED Requirements

### Requirement: Repository orchestration is native

Repository-owned orchestration, including the common verbs, gates, CI steps and release steps, SHALL run through native tool commands or tasks of the toolchain owner, so that the same invocation works on every platform the repository supports. Each CI step SHALL invoke one such command unless a complete, current retention record names it as official installer or operating-system glue by exact text, owner, reason, platforms and evidence; review judges the evidence.

#### Scenario: A gate runs through a repository script

- **WHEN** a repository gate or CI step runs `tools/ci/run-secrets-scan.sh`
- **THEN** the paradigm reports repository-owned shell orchestration, with a native command or toolchain-owner task as the canonical repair.

#### Scenario: A CI step embeds a shell program

- **WHEN** a CI step contains a shell conditional or loop
- **THEN** the paradigm reports inline shell orchestration.

#### Scenario: Necessary glue is retained with a complete record

- **WHEN** the retention record names a CI step's Forge file, job and the digest of its exact text, with a catalogued class, owner, reason, platforms and evidence
- **THEN** the step conforms, whatever YAML quoting or block style carries that text.

#### Scenario: Retained glue changes

- **WHEN** the text of a recorded step changes, or a job that the record lists no longer carries it
- **THEN** the paradigm reports the step as inline shell and the record as stale.

#### Scenario: A record is incomplete

- **WHEN** a record lacks its evidence or names an uncatalogued class
- **THEN** the paradigm reports the record and admits no step through it.

#### Scenario: A gate cannot be retained

- **WHEN** a gate hands a shell program to an interpreter
- **THEN** the paradigm reports inline shell orchestration, whatever the retention record lists.
