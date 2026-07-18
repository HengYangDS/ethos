## ADDED Requirements

### Requirement: Hosted CI tool supply is deterministic enough to support quality proof

Hosted CI jobs that require downloaded binary tools MUST use repository-owned
installer scripts with a shared cache, resumable artifact download, bounded retry
policy, and archive validation before the tool is installed.

#### Scenario: A binary tool installer runs in hosted CI

- **WHEN** a hosted CI job needs gitleaks or Node
- **THEN** the job invokes a repository-owned installer script
- **AND** the installer downloads through the shared CI artifact helper
- **AND** the artifact is cached under `build/cache/ci-tools/`
- **AND** the installer validates the cached archive before reuse
