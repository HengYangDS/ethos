# ETHOS Quality

## Purpose

ETHOS SHALL make repository quality a deterministic proof concern with one owner
per property, one gate declaration plane, and no command-shaped quality shadow.

## Requirements

### Requirement: Singular Gate Declaration

`system/gates.toml` SHALL be the only product gate and proof-floor declaration.
A gate SHALL bind either one or more concrete Python providers or one external
owner command, never both.

#### Scenario: A gate is loaded

- **WHEN** ETHOS validates or compiles the gate declaration
- **THEN** strict Pydantic contracts reject unknown fields, duplicate IDs,
  duplicate executors, missing dependencies, and unknown proof-set members
- **AND** provider references and external commands remain adapter identities,
  not public CLI commands
- **AND** no second Python gate registry restates the declaration

#### Scenario: A Python provider gate executes

- **WHEN** `ethos prove --execute --gate <gate-id> --json` selects a provider gate
- **THEN** the provider is invoked directly in the admitted checkout
- **AND** every provider returns a mapping with an explicit `verdict` result and
  required gaps
- **AND** the proof run records the gate, provider identity, diagnostics, and
  closed verdict
- **AND** ETHOS does not call its CLI through a subprocess or in-process loopback

### Requirement: Singular Quality Entry

`ethos prove` SHALL be the only public quality selection and execution surface.
Cyclopts operation declarations own CLI syntax; gate IDs own proof selection.

#### Scenario: A focused check is requested

- **WHEN** a caller runs `ethos prove --gate <gate-id> --json`
- **THEN** ETHOS plans the exact gate and dependency closure
- **AND** `--execute` runs that plan and returns evidence
- **AND** no `ethos quality` command group, generic report-handler DSL, command
  registry, wrapper alias, or re-export facade exists

### Requirement: One Owner Per Property

Ruff, the selected type checker, pytest/coverage, rumdl or markdownlint, dprint or
native carrier formatters, shfmt/ShellCheck, ast-grep, import-linter, dependency
checking, and repository-native semantic checks SHALL each own a disjoint
property.

#### Scenario: Two tools claim the same property

- **WHEN** the tracked tool, gate, and owner-script declarations are audited
- **THEN** the overlap is a required gap unless one tool is explicitly a bounded
  pilot replacing the other
- **AND** a baseline, hosted dashboard, or convenience wrapper cannot become a
  second authority

### Requirement: Warning And Suppression Zero

Local proof, hooks, provider CI, and release proof SHALL treat unapproved warnings
as failures. Production source SHALL not use formatter, lint, type, or coverage
suppressions to hide current defects.

#### Scenario: A command succeeds with a warning

- **WHEN** a governed quality command exits zero but emits an unapproved warning
- **THEN** its gate fails
- **AND** the warning must be removed or represented by an explicit bounded
  decision with a deletion condition

#### Scenario: Production contains a suppression

- **WHEN** quality proof finds `fmt off/on`, `noqa`, type-ignore, coverage-ignore,
  or an equivalent suppression in production source
- **THEN** proof blocks until the construct is deleted or replaced by a truthful
  semantic layout

### Requirement: Python Quality Floor

Python source SHALL pass the canonical Ruff lint/format owner, the selected
strict type owner, import boundaries, dependency hygiene, docstring policy, and
semantic module-layout policy.

#### Scenario: Python proof runs

- **WHEN** default or full proof selects Python quality gates
- **THEN** each gate uses its tracked native configuration and one reusable owner
- **AND** caches and generated outputs stay under ignored `build/runtime/**`
- **AND** no ambient host configuration or second formatter changes the verdict

### Requirement: Capability-Preserving Test Floor

The Python test owner SHALL run bounded parallel tests, warnings as errors,
branch coverage, architecture tests, property tests, and declared concurrency or
CAS tests. Coverage policy SHALL come only from
`.config/checks/coverage/policy.toml`.

#### Scenario: Change proof executes the complete test surface

- **WHEN** the unit-architecture gate completes
- **THEN** it runs the complete declared test surface with warnings as errors and
  emits branch-coverage evidence bound to the exact HEAD
- **AND** pre-existing repository-wide coverage debt does not prevent an
  independently valid Change from landing
- **AND** the Campaign full proof runs the dependent coverage-floor gate against
  that same evidence and enforces the configured hard coverage floor represented
  by the policy's current hard floor
- **AND** authority, CAS, and reducer owners may declare stricter local floors
- **AND** a test that only reaches a branch without asserting behavior is not a
  substitute for capability proof

### Requirement: Native Carrier Quality

Markdown, TOML, JSON, YAML, shell, lockfiles, diagrams, and release metadata SHALL
use one carrier-native formatter or validator and one tracked configuration
owner.

#### Scenario: A carrier is checked

- **WHEN** config, docs, shell, or format proof runs
- **THEN** deterministic format, syntax, schema, links, anchors, and shell safety
  are checked by the declared native owner
- **AND** the gate does not rewrite governed content during proof

### Requirement: Semantic And Physical Isomorphism

Repository-owned code SHALL place each narrow concept with one truth or effect
owner and one primary reason to change. Ambiguous modules, facades, aliases,
private cross-module imports, and mixed command owners SHALL block proof.

#### Scenario: A generic module has no closed semantic contract

- **WHEN** the module-layout gate observes `core`, `common`, `shared`, `utils`,
  `helpers`, `base`, `manager`, `service`, or another configured ambiguous name
- **THEN** the module must be absorbed, precisely renamed, split on a real
  semantic axis, or deleted
- **AND** splitting only to satisfy ELOC or retaining the old path as a facade is
  not remediation

### Requirement: Direct Source Budget

Source budget SHALL be measured directly from repository files without worker,
replay, shadow, or self-referential admission runtimes. Coordinates SHALL remain
non-compensatory.

#### Scenario: One budget coordinate exceeds its limit

- **WHEN** `ethos prove --gate source-budget --json` evaluates the repository
- **THEN** the result is `block` even if unrelated coordinates are below budget
- **AND** a budget increase cannot substitute for deletion or an explicit product
  capability decision

### Requirement: Generated Artifact Boundary

Generated caches, build outputs, local state, machine evidence, and curated
records SHALL remain physically distinct and deterministically classifiable.

#### Scenario: Generated content appears in a governed source location

- **WHEN** the generated-artifacts provider observes tracked or ignored drift
  outside its declared semantic home
- **THEN** proof blocks with the exact path and expected disposition
- **AND** generated content cannot become source, current evidence, or release
  truth merely because a file exists

### Requirement: Compatibility Residue Is Forbidden

Production source SHALL not retain shims, wrappers, aliases, re-exports,
fallback implementations, or deprecated parallel paths unless the current user
explicitly requires a bounded compatibility window. The module-layout and
product-boundary gates are the only owners of this property; no standalone
compatibility gate or command exists.

#### Scenario: Compatibility residue is found

- **WHEN** the module-layout or product-boundary gate scans production source
- **THEN** every residue is a hard gap
- **AND** the terminal fix moves callers to the one selected owner and deletes the
  old path in the same cutover

### Requirement: Evidence Is Head And Policy Bound

Executed proof SHALL bind the exact HEAD, tree, Commitment, TransitionPlan digest,
gate policy identity, provider or command identity, output, and closed verdict.
Focused proof MAY merge same-HEAD gate evidence but SHALL NOT satisfy promotion
until the complete required floor is present.

#### Scenario: A gate implementation changes after proof

- **WHEN** proof policy or repository-owned provider or script source changes
- **THEN** the previous proof becomes stale
- **AND** land, publish, and protected ref movement remain blocked until fresh
  proof exists for the immutable target HEAD

### Requirement: Local And Hosted Planes Stay Separate

Local proof, local provider emulation, GitLab CI, GitHub Actions, publication, and
release SHALL remain independently identified evidence planes.

#### Scenario: Local proof passes while a provider is unavailable

- **WHEN** every local gate passes but GitLab or GitHub has no fresh observation
- **THEN** local proof is pass and the unavailable provider remains unknown
- **AND** no local runner or emulator self-promotes to hosted success

### Requirement: Fresh Offline Installation

The full release proof SHALL build deterministic Python artifacts and install
them into a fresh offline environment through one owner. Installed command help,
version, module origin, and artifact digests SHALL bind to the same stable HEAD.

#### Scenario: Offline installation succeeds

- **WHEN** `uv run --frozen --offline python -m nox -s install_smoke` completes
- **THEN** disposable state stays under `build/runtime/**`
- **AND** evidence stays under `build/evidence/**`
- **AND** source-checkout imports, network access, HEAD movement, or artifact
  digest drift fail the gate

### Requirement: Supply Chain Evidence

Release proof SHALL produce deterministic package digests, SBOM, provenance,
and provider-specific publication attestations through bounded release owners.

#### Scenario: A release artifact is prepared

- **WHEN** terminal full proof and publish readiness run at one immutable HEAD
- **THEN** local package, SBOM, provenance, GitLab, and GitHub observations remain
  separately attributable
- **AND** matching artifact digests are required before a dual-provider release
  is admitted

### Requirement: Performance Evidence Is Not A Default Gate

Same-machine timing or token measurements SHALL remain diagnostic unless a real
consumer, reproducibility contract, provider-neutral protocol, and admission
policy justify a gate.

#### Scenario: The retired performance stack is inspected

- **WHEN** gate and tool declarations are audited
- **THEN** no performance gate, policy, runner, baseline, or compatibility alias
  exists
- **AND** a future proposal must replace an identified owner or close a proven
  gap rather than add a parallel metric plane
