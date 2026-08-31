# ETHOS Proof Hosts

## Purpose

ETHOS SHALL keep conformance, parity, sample repository, schema compatibility,
and migration replay proof separate from runtime packages.

## Requirements

### Requirement: Proof Separation
ETHOS SHALL host conformance fixtures and parity proof helpers outside the
runtime semantic packages.

#### Scenario: Conformance package is inspected
- **WHEN** tests inspect `proof-hosts`
- **THEN** it contains proof fixtures and sample helpers rather than runtime
  command semantics

### Requirement: Product Migration Closure Proof
ETHOS SHALL prove product migration closure through conformance tests, local
build smoke, npm launcher smoke, OpenSpec validation, parity evidence, and
execution-backed ETHOS proof.

#### Scenario: Closure proof runs
- **WHEN** product migration closure is verified
- **THEN** unit and architecture tests pass
- **AND** all Python packages build wheel and sdist locally
- **AND** npm launcher smoke and dry-run pack pass without publishing
- **AND** OpenSpec validation and ETHOS proof report no required gaps

### Requirement: Governance Lifecycle Fixtures
ETHOS SHALL provide reusable tests and fixtures for complete and malformed
governance lifecycles.

#### Scenario: Complete lifecycle fixture passes
- **WHEN** tests load a complete governance lifecycle fixture
- **THEN** claim admission, OpenSpec lifecycle review, proof evidence, and
  promotion target validation all report no required gaps

#### Scenario: Malformed lifecycle fixture fails
- **WHEN** tests load a malformed governance lifecycle fixture
- **THEN** ETHOS reports specific required gaps for missing claim binding,
  missing promotion target, missing executed proof, or malformed OpenSpec
  carrier state

### Requirement: Reference Adopter Boundary Fixtures
ETHOS SHALL test adopter parity through generic profiles instead of product-package
adopter terminology.

#### Scenario: Reference adopter fixture is validated
- **WHEN** tests validate a reference adopter profile fixture
- **THEN** adopter-specific terms remain in the fixture or evidence
- **AND** product runtime packages remain provider-neutral

### Requirement: Skills V2 Conformance Fixtures

ETHOS SHALL keep Skills V2 conformance, migration replay, and parity fixtures
outside runtime semantic packages.

#### Scenario: placeholder skill is rejected

- **WHEN** Skills V2 conformance tests run against a minimal placeholder
  `SKILL.md`
- **THEN** the fixture reports required quality gaps

#### Scenario: adopter migration replay remains readable

- **WHEN** Skills V2 migration replay tests run against ETHOS v1, a reference-adopter v1, and
  external style activation records
- **THEN** each input normalizes into the provider-neutral IR without losing
  historical fixture fields

### Requirement: Hosted provider observations remain evidence-class scoped

ETHOS SHALL capture hosted provider observation envelopes without treating local
tool discovery or provider CLI output as repository proof. Each supported
provider SHALL name a runtime repository-target variable in tracked
configuration, and execute mode SHALL invoke the provider CLI only with the
resolved explicit repository target. The envelope SHALL derive bounded provider
observation state and gap codes without adding those gaps to repository proof
requirements.

#### Scenario: Provider observation envelope is captured

- **WHEN** hosted provider observation runs in dry-run or execute mode
- **THEN** the evidence SHALL name GitHub and GitLab provider observation state
- **AND** it SHALL include the Git head, remote URL, command, tool availability,
  target variable, resolved target, target configuration state, and execution
  state
- **AND** execute mode with a configured target SHALL add the provider-native
  --repo selector to the GitHub or GitLab command
- **AND** execute mode SHALL normalize provider facts such as latest observed
  head, status, conclusion, ref, and URL when the provider CLI returns them
- **AND** the envelope SHALL summarize provider states and stable observation
  gap codes as observed, partial, not_configured, or observation_failed
- **AND** it SHALL explicitly set hosted GitHub status claimed, hosted GitLab
  status claimed, and remote publication claimed to false unless separate
  hosted facts are promoted through the publication evidence class

#### Scenario: Unconfigured provider remains a bounded observation

- **WHEN** execute mode has no value for a provider repository-target variable
- **THEN** that provider SHALL report observation_state=not_configured
- **AND** the provider command SHALL NOT execute
- **AND** executed SHALL remain false and provider facts SHALL remain empty
- **AND** the envelope SHALL report a provider_not_configured observation gap
- **AND** the absent provider configuration SHALL NOT become a repository proof
  failure or a hosted success claim

### Requirement: Host conformance controls repository-local Git semantics

ETHOS SHALL make portable host-conformance assertions independent of ambient
Git configuration, repository ownership, and text-conversion defaults by
declaring the exact repository-local semantics required by each fixture.
Indexed Git configuration passed through the process environment SHALL contain
a complete key/value pair for every declared entry on every supported host.
The shared Git execution boundary SHALL preserve only that explicit overlay
while continuing to hide ambient global and system configuration.

#### Scenario: CRLF bytes are tested on a Windows-style Git configuration

- **WHEN** the adopter fixture stages a CRLF byte sequence while
  `core.autocrlf=true`
- **THEN** its tracked fixture policy preserves the exact bytes in the index
- **AND** the working tree and staged blob round-trip identically.

#### Scenario: Hosted Git subprocess receives a portable configuration overlay

- **WHEN** host-conformance invokes Git on Windows, macOS, or Linux
- **THEN** every indexed `GIT_CONFIG_KEY_n` has a corresponding non-empty
  `GIT_CONFIG_VALUE_n`
- **AND** global and system configuration remain hidden
- **AND** credential prompting remains disabled.

#### Scenario: Hosted proof drops process identity

- **GIVEN** a hosted runner owns the checkout and then executes repository proof
  under a different declared UID and GID
- **WHEN** ETHOS observes source identity or creates a deterministic test commit
- **THEN** Git receives the runner-declared exact repository trust and explicit
  author/committer identity through the shared subprocess boundary
- **AND** repository-local `user.name` and `user.email` remain authoritative for
  identity policy
- **AND** no ambient user Git configuration, broad trust rule, or per-test
  exception participates in the result.

### Requirement: Hosted repository proof preserves source authority

Hosted repository proof SHALL execute the proposal checkout's locked source
environment without first installing or selecting repository-local mutation
hooks or an accepted package runtime. Repository source audit SHALL not treat
the host's hook/runtime projection as proof of source correctness.

#### Scenario: Proposal commit differs from accepted runtime source

- **GIVEN** a hosted checkout contains a proved proposal commit whose source
  identity differs from the repository's accepted package runtime
- **WHEN** the repository proof job executes
- **THEN** proof runs directly from the checkout's locked source environment
- **AND** no hook/runtime activation is attempted before proof
- **AND** the source proof is not rejected solely because a local mutation
  runtime is absent or bound to the accepted commit.

#### Scenario: Local mutation readiness remains independently observable

- **WHEN** a user inspects a mutable local checkout
- **THEN** status reports its selected hook/runtime currentness
- **AND** repository source audit neither hides nor assumes that separate local
  mutation-readiness fact.
