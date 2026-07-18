## ADDED Requirements

### Requirement: Global Executable Source Budget And Compression Debt

ETHOS SHALL measure maintained executable source across product code, tests,
tools, shell, JavaScript, declarations, schemas, templates, and tracked derived
projections, and SHALL reject an unbounded source increase that lacks an explicit
compression-debt record.

#### Scenario: A migration reports global source deltas

- **WHEN** `ethos quality source-budget --json` evaluates a governed repository
- **THEN** it reports the baseline identity, current HEAD, global and carrier
  metrics, independent inventory status, terminal budgets, and active debt
- **AND** the metric does not exclude a tracked executable carrier merely because
  its logic moved from Python into TOML, CEL, Jinja, generated output, tests, or
  tools
- **AND** each active debt record names the added surface, owner, replacement,
  expiry, deletion wave, and expected net deletion
- **AND** a stale, missing, expired, or over-budget debt record is a required gap

### Requirement: Executable Carrier Admission

ETHOS SHALL admit an executable carrier or tool only when its semantic owner,
format or canonicalization policy, parser, semantic validation, behavior proof,
runtime-cache home, supply-chain owner, and gate are declared.

#### Scenario: An undeclared executable carrier is rejected

- **WHEN** a tracked executable carrier extension or tool declaration is added
- **THEN** ETHOS verifies it against the fail-closed carrier policy
- **AND** it reports a required gap when the carrier has no complete quality and
  supply-chain contract
- **AND** provider projections invoke owner scripts rather than restating the
  carrier policy inline

### Requirement: Local Provider Execution Is Not Workflow Listing

ETHOS SHALL distinguish workflow discovery from local provider execution and
SHALL not treat a listed job as passing parity evidence.

#### Scenario: A selected emulatable job is verified locally

- **WHEN** a configured GitHub or GitLab local-provider job is evaluated
- **THEN** ETHOS executes the selected formal job through `act` or
  `gitlab-ci-local`
- **AND** the evidence binds the current HEAD, job, tool versions, image mapping,
  redacted inputs, and execution verdict
- **AND** an unsupported hosted-only job is reported as hosted-observation-only,
  not as a locally passing job
