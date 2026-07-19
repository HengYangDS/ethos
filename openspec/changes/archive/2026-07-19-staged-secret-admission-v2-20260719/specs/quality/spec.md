## ADDED Requirements

### Requirement: Commit-time staged secret admission fails closed under the repository-owned tool contract

The tracked ETHOS pre-commit hook MUST run the repository-owned staged-secret
runner against the Git index before Ruff formatting or ordinary ETHOS write
admission. The runner MUST use the repository-selected gitleaks version and
policy, MUST fully redact matched values, and MUST NOT install tools, access the
network, scan history, or write quality evidence.

#### Scenario: Staged secret stops downstream admission

- **WHEN** a non-empty staged index matches the active `.gitleaks.toml` policy
- **THEN** the staged-secret runner MUST return a blocking result
- **AND** the hook MUST stop before Ruff and `ethos.cli hook admit pre-tool`
- **AND** stdout and stderr MUST NOT contain the matched value.

#### Scenario: Clean staged content preserves the existing hook path

- **WHEN** the staged-secret runner accepts the non-empty staged index
- **THEN** the hook MUST continue to the existing staged-Python Ruff check
- **AND** it MUST continue to repository-root-bound ETHOS write admission.

#### Scenario: Missing or incompatible scanner fails closed without host mutation

- **WHEN** the selected gitleaks executable is missing or reports an incompatible version
- **THEN** the runner MUST fail with a stable non-secret diagnostic naming the expected version
- **AND** the hook MUST NOT install a binary, invoke a package manager, access the network, or continue downstream.

#### Scenario: Full secret proof remains a separate owner path

- **WHEN** local or hosted quality proof scans the tracked tree and Git history
- **THEN** it MUST continue through the existing full secret gate and evidence path
- **AND** the commit-time runner MUST NOT claim that full-tree or history proof occurred.
