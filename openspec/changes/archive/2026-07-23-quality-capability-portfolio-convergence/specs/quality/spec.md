## MODIFIED Requirements

### Requirement: Quality Asset Model

ETHOS SHALL model repository assets across code, docs, shell, configuration,
evidence, release artifacts, and adopter profiles. The tracked active-tool
catalog SHALL be the sole declaration of an admitted tool's identity, profile,
configuration, and optional gate boundary; comparative lifecycle decisions
belong only to the tooling roadmap.

#### Scenario: Asset policy is reported

- **WHEN** `ethos quality asset-policy --json` runs
- **THEN** ETHOS reports asset classes, dimensions, and catalog-derived tool
  profiles without executing provider tools

#### Scenario: Tool profiles are catalog-derived

- **WHEN** `ethos quality tool-profiles --json` or
  `ethos quality asset-policy --json` reports quality tool adapters
- **THEN** every adapter is derived from exactly one `system/tools.toml` entry
- **AND** its concern, tool identity, configuration, profile, and optional gate
  agree with that entry
- **AND** catalog membership means the mechanism is admitted and active without
  a repeated lifecycle-state field
- **AND** candidate, deferred, and rejected mechanisms own no runtime catalog
  row
- **AND** no parallel static Python tool-adapter registry supplies conflicting
  tool truth

## ADDED Requirements

### Requirement: Quality capabilities have one ranked mechanism

ETHOS SHALL govern quality tools by capability and SHALL select one active owner
for each capability rather than accumulating overlapping permanent scanners,
formatters, runners, dashboards, or report planes.

#### Scenario: Runtime catalog and decision portfolio are non-overlapping

- **WHEN** `ethos quality tool-profiles --json` reports the tracked catalog
- **THEN** every reported mechanism SHALL be admitted and executable
- **AND** the runtime catalog SHALL contain admitted active mechanisms only
- **AND** a candidate SHALL remain owned by a time-bounded OpenSpec pilot until
  promotion
- **AND** the tooling roadmap SHALL state the unique active or pilot choice and
  the disposition of material alternatives
- **AND** deferred or rejected platforms SHALL own no runtime catalog row,
  config, runner, or proof gate.

### Requirement: Active product tools close the owner-to-proof chain

An active product quality tool SHALL execute through its reusable owner surface,
have a GateDescriptor when it belongs to a trust-bearing proof floor, and appear
in each applicable proof set without provider-specific command duplication.

#### Scenario: Import and dependency gates use their owner scripts

- **WHEN** default or full product proof compiles the gate registry
- **THEN** import boundaries SHALL execute
  `tools/ci/scripts/run-import-linter.sh`
- **AND** dependency hygiene SHALL execute
  `tools/ci/scripts/run-dependency-hygiene.sh`
- **AND** both gate ids SHALL be present in the default and full product proof
  sets
- **AND** provider CI and local CI SHALL continue invoking those same owner
  scripts.

### Requirement: Quality configuration validates its own control surface

ETHOS SHALL validate the syntax and semantic shape of the tracked pre-commit
configuration through the existing config owner gate.

#### Scenario: Pre-commit configuration is validated without external hooks

- **WHEN** `tools/ci/scripts/run-config-lint.sh` runs the full repository config
  profile
- **THEN** it SHALL execute the locked `pre-commit validate-config` command
- **AND** `.pre-commit-config.yaml` SHALL continue using repository-local owner
  scripts only
- **AND** validation SHALL not install or execute third-party hook repositories.

### Requirement: Tool and standard claims match executed implementations

ETHOS SHALL name the scanner, schema, and standard boundary actually executed
and SHALL label partial or local projections without implying external-standard
conformance.

#### Scenario: Vulnerability and release evidence are described exactly

- **WHEN** quality docs, specs, and release metadata describe dependency audit,
  SBOM, or provenance output
- **THEN** Python dependency auditing SHALL name `uv audit`
- **AND** the current SBOM SHALL be labeled an ETHOS lockfile-derived
  `SPDX-lite` projection
- **AND** the current provenance SHALL be labeled an ETHOS-local in-toto-shaped
  statement with SLSA-shaped fields
- **AND** SPDX or SLSA conformance SHALL remain unclaimed until an admitted
  standard adapter proves it.

### Requirement: Candidate tools have a terminal exit

Candidate quality tools SHALL remain report-only until they prove independent
value and SHALL not become an indefinite second implementation.

#### Scenario: Pilot promotion is evidence bound

- **WHEN** a candidate tool is proposed for active adoption
- **THEN** repeated fixed-HEAD runs SHALL produce deterministic normalized output
- **AND** the candidate SHALL find a valid issue not already owned by an active
  gate on at least two real changes
- **AND** its runtime, cache, network, write, license, and supply boundaries SHALL
  be recorded
- **AND** the decision SHALL promote it, absorb its useful rule and retire it, or
  reject it with no active residue.

### Requirement: Python dependency vulnerability audit is lockfile-native

ETHOS SHALL run Python dependency vulnerability auditing through the reusable
owner script and native `uv audit --frozen` lockfile analysis. The gate SHALL
bind its result to `uv.lock`, identify OSV as the advisory service, keep local,
hosted, image, and publication claims separate, and fail closed whenever the
audit cannot produce a valid passing result.

#### Scenario: uv audits the frozen workspace lock

- **WHEN** hosted CI, local CI, or `ethos prove --execute --json` runs the Python
  vulnerability audit gate
- **THEN** ETHOS SHALL invoke
  `tools/ci/scripts/run-python-vulnerability-audit.sh`
- **AND** the runner SHALL execute native `uv audit --frozen` against `uv.lock`
- **AND** the evidence SHALL identify `uv audit`, `uv.lock`, and OSV explicitly
- **AND** the evidence SHALL be local owner-gate evidence under
  `build/evidence/quality/security/`
- **AND** the gate SHALL NOT claim image/package scanning, hosted CI success, or
  remote publication.

#### Scenario: vulnerability or audit failure remains final

- **WHEN** `uv audit` reports a vulnerability, an adverse package status,
  malformed JSON, or any execution failure
- **THEN** the owner script SHALL return a nonzero result
- **AND** it SHALL NOT emit a passing vulnerability-audit summary.

## REMOVED Requirements

### Requirement: Python Vulnerability Audit Gate

**Reason**: The `pip-audit` transport wrapper was replaced by native lockfile
analysis, so the old requirement and its scanner-specific retry contract are no
longer truthful.

**Migration**: Use the lockfile-native Python dependency vulnerability audit
requirement and `tools/ci/scripts/run-python-vulnerability-audit.sh`.
