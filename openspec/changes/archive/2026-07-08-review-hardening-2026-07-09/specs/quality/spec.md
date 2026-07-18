## ADDED Requirements

### Requirement: Proof gates are fail-closed for CI and hooks

ETHOS proof gates SHALL be consumable by CI, git hooks, and shell chains without
requiring every caller to parse JSON manually.

#### Scenario: failed proof gate fails the process

- **WHEN** a proof command emits a blocking verdict
- **THEN** CI and hooks can reject the operation from the process exit code
- **AND** the JSON verdict remains available for diagnostics

### Requirement: Evidence and claims are HEAD-bound

ETHOS quality and readiness surfaces SHALL bind active claims and evidence
freshness to current Git HEAD before treating them as current truth.

#### Scenario: active claim was proven against another head

- **WHEN** status, plan, report, or quality freshness reads active claim evidence
- **THEN** the read model compares the claim head to current repository HEAD
- **AND** stale evidence is surfaced as a gap rather than reused as current proof

### Requirement: Scorecards expose hard-floor and coordination risk

ETHOS report scorecards SHALL expose nominal score, effective score, read-model
identity, hard-quality gaps, and coordination risk separately.

#### Scenario: hard quality or coordination risk exists

- **WHEN** `ethos report --json` summarizes repository readiness
- **THEN** the summary identifies the governed report read model
- **AND** hard quality gaps and coordination risk are counted explicitly
- **AND** effective score reflects those hard floors rather than presenting a
  misleading green nominal score alone

### Requirement: Local-ci fallback projects owner scripts from target root

ETHOS local-ci fallback evidence SHALL derive invoked owner scripts from the
actual target repository's local-ci script.

#### Scenario: publish is run with an explicit root from another cwd

- **WHEN** `ethos publish --root <repo> --json` assembles local-ci fallback
- **THEN** owner scripts come from `<repo>/.config/ci/scripts/run-local-ci.sh`
- **AND** the local-submit package and fallback evidence agree
- **AND** hosted CI status remains unclaimed

### Requirement: Release supply-chain evidence binds tools, secrets, SBOM, and attestation

ETHOS release-profile quality gates SHALL bind tool downloads, secret scanning,
transitive dependencies, and release attestation materials to current repository
truth.

#### Scenario: supply-chain evidence is emitted for release readiness

- **WHEN** release quality surfaces emit SBOM or release attestation evidence
- **THEN** the SBOM includes workspace packages and lockfile transitive packages
- **AND** the SBOM records the `uv.lock` digest and package layer counts
- **AND** release attestation includes SLSA materials for Git HEAD, evidence,
  `uv.lock`, and SBOM digest
- **AND** the gitleaks installer validates cached archives with pinned SHA-256
- **AND** the secrets gate scans both current tree and Git history
