# ETHOS Proof Hosts

## Purpose

ETHOS SHALL keep proof material, including test fixtures, sample-repository
constructors, package acceptance and host-conformance checks, outside the
shipped runtime packages. It SHALL keep local Git semantics host-portable and
run hosted proof from the checked-out source without letting hosted execution or
provider observation become repository authority.

## Requirements

### Requirement: Governance Lifecycle Fixtures

ETHOS SHALL provide reusable tests and fixtures for complete and malformed
governance lifecycles that cover a Lease-bound Work Lane, an official OpenSpec
Change, proof bound to the exact head, and its archive or closeout transition.

#### Scenario: Complete lifecycle fixture passes

- **WHEN** tests load a complete governance lifecycle fixture
- **THEN** Lease admission, OpenSpec lifecycle validation, exact-head proof and
  the archive or closeout transition all report no required gaps

#### Scenario: Malformed lifecycle fixture fails

- **WHEN** tests load a malformed governance lifecycle fixture
- **THEN** ETHOS reports a specific required gap for a missing, expired or
  foreign Lease, an unproven head or mismatched proof Attestation, or a missing
  or malformed OpenSpec Change

### Requirement: Reference Adopter Boundary Fixtures

ETHOS SHALL test adopter behavior through generic reference-adopter profile
fixtures. The product-boundary gate SHALL report adopter-specific path,
`--adopter` and private-reference literals as required gaps in tests, fixtures
and CI tooling as it does in product source.

#### Scenario: Reference adopter fixture is validated

- **WHEN** tests validate a reference adopter profile fixture
- **THEN** the profile is rendered and validated through the production profile
  declaration
- **AND** it names only a generic adopter identity

#### Scenario: Named adopter literal is rejected in tests

- **WHEN** a test, fixture or CI tooling file names a specific adopter path such
  as `adopters/<name>/` or an `--adopter <name>` value
- **THEN** `ethos prove --gate product-boundary --json` reports an
  `adopter_specific_literal` required gap for that file and line

### Requirement: Hosted provider observations remain evidence-class scoped

ETHOS SHALL capture hosted provider observation envelopes without treating local
tool discovery or provider CLI output as repository proof. Each supported
provider SHALL name a repository-target variable in tracked configuration;
execute mode SHALL invoke its CLI only with that resolved target. The envelope
SHALL derive bounded observation state and gap codes outside repository proof
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
- **AND** execute mode SHALL summarize the envelope state as observed, partial,
  not_configured, or observation_failed with stable observation gap codes, and
  dry-run mode SHALL report state dry_run with verdict unknown
- **AND** it SHALL set hosted GitHub status claimed, hosted GitLab status
  claimed, and remote publication claimed to false

#### Scenario: Unconfigured provider remains a bounded observation

- **WHEN** execute mode has no value for a provider repository-target variable
- **THEN** that provider SHALL report observation_state=not_configured
- **AND** the provider command SHALL NOT execute
- **AND** executed SHALL remain false and provider facts SHALL remain empty
- **AND** the envelope SHALL report a provider_not_configured observation gap
- **AND** the absent provider configuration SHALL NOT become a repository proof
  failure or a hosted success claim

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

### Requirement: Skill Conformance Fixtures

ETHOS SHALL keep skill conformance fixtures outside runtime semantic packages.
Supported input SHALL preserve its declared meaning; unsupported input SHALL
fail explicitly instead of retaining obsolete compatibility behavior.

#### Scenario: placeholder skill is rejected

- **WHEN** conformance checks evaluate a minimal placeholder skill
- **THEN** required package-quality gaps remain observable

#### Scenario: Unsupported activation is not normalized into success

- **WHEN** a fixture supplies an unsupported activation version or retired fields
- **THEN** current validation rejects the original input
- **AND** raw fixture evidence is not rewritten or promoted to current authority

### Requirement: Proof material stays outside shipped packages

ETHOS SHALL keep proof fixtures, sample-repository constructors and package
acceptance fixtures in repository test and CI tooling outside the shipped
runtime package. Built Python and npm packages SHALL contain none of them.

#### Scenario: Built packages exclude proof material

- **WHEN** the wheel, the sdist and the npm launcher package are built from one
  source commit
- **THEN** none of them contains a test fixture, test support module or package
  acceptance fixture
- **AND** the npm launcher package contains only its allowlisted launcher files
  and package manifest

### Requirement: Host conformance keeps local Git semantics exact

Host-conformance fixtures and ETHOS source SHALL declare exact local Git
semantics independent of ambient configuration, repository ownership and text
conversion. Every indexed configuration entry SHALL carry a non-empty key and
value on every supported host. The shared local Git boundary SHALL take
process-environment configuration only from this explicit overlay and SHALL hide
global and system configuration.

#### Scenario: Clean ETHOS checkout has one source tree

- **WHEN** native Linux, macOS, or Windows checks out one exact ETHOS commit and
  reports no source overlay
- **THEN** source build identity equals that commit's exact tree on every host
- **AND** the repository-owned content policy, not ambient Git configuration,
  defines text normalization

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

#### Scenario: Declared trust and identity reach Git exactly

- **WHEN** a caller declares exact repository trust as an indexed configuration
  entry and explicit author and committer identity, and ETHOS then observes
  source identity or creates a commit
- **THEN** Git receives exactly that trust entry and identity through the shared
  subprocess boundary
- **AND** repository-local `user.name` and `user.email` remain unchanged and
  authoritative for identity policy
- **AND** a `safe.directory=*` entry or an incomplete or empty indexed pair fails
  as `git_config_overlay_invalid` before Git runs
- **AND** no ambient user Git configuration participates in the result.
