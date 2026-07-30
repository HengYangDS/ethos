## ADDED Requirements

### Requirement: Adopter Release Metadata Remains Profile Bounded

ETHOS SHALL NOT infer product release semantics from the presence of a generic
tool configuration file, and SHALL report supported runtime-files identity
without requiring Python package metadata.

#### Scenario: Runtime-files adopter is audited

- **WHEN** an adopted repository has `pyproject.toml` without `[project]`
- **AND** one `[tool.<name>]` table declares `distribution = "runtime-files"`
  and a contained `version-source`
- **THEN** generic coupling and schema audits do not execute ETHOS product-only
  release policy
- **AND** direct release inspection reads the table name and declared version
  file as release identity
- **AND** malformed or unsupported metadata is returned as a structured gap,
  not a Python traceback
- **AND** invalid release-policy TOML is likewise returned as a structured gap
