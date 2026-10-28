# ETHOS Quality

## Purpose

ETHOS SHALL make repository quality a deterministic proof concern with one owner
per property, one gate declaration plane, and no command-shaped quality shadow.

## Requirements

### Requirement: Singular Gate Declaration

`system/gates.toml` SHALL be the only product gate and proof-floor declaration.
A gate SHALL bind either one or more concrete Python providers or one external
owner command, never both. Every gate SHALL belong to this one graph without a
secondary registry selector, and no tool catalog SHALL restate gate identity,
profile membership, or execution ownership.

#### Scenario: A gate is loaded

- **WHEN** ETHOS validates or compiles the gate declaration
- **THEN** strict Pydantic contracts reject unknown fields, duplicate IDs,
  duplicate executors, missing dependencies, and unknown proof-set members
- **AND** provider references and external commands remain adapter identities,
  not public CLI commands
- **AND** no second Python registry, registry projection, or tool catalog
  restates the declaration

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
property. Gate identity and proof membership SHALL remain in
`system/gates.toml`; tool-specific behavior and version identity SHALL remain in
the smallest existing native configuration or supply owner.

#### Scenario: Two tools claim the same property

- **WHEN** gate, native configuration, supply, and owner-script declarations are
  audited
- **THEN** the overlap is a required gap unless one tool is explicitly a bounded
  pilot replacing the other
- **AND** a catalog, baseline, hosted dashboard, or convenience wrapper cannot
  become a second authority

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
`.config/checks/coverage/policy.toml`. The required combined line-and-branch
coverage SHALL be at least 95 percent across the declared Python product.
Measurement SHALL NOT redefine the requirement as an aspiration.

#### Scenario: Change proof executes the complete test surface

- **WHEN** the unit-architecture gate completes
- **THEN** it runs the complete declared test surface with warnings as errors and
  emits branch-coverage evidence bound to the exact HEAD
- **AND** default proof, full proof, and local CI run the same dependent
  coverage-floor owner against that evidence without rerunning the tests
- **AND** coverage below the required floor blocks acceptance rather than being
  excused as existing debt or changing the floor
- **AND** authority, CAS, and reducer owners may declare stricter local floors
- **AND** a test that only reaches a branch without asserting behavior is not a
  substitute for capability proof

#### Scenario: A coverage regression exposes unsafe compensation

- **WHEN** an archive result names the repository root, another Change, a
  non-archive path, or a symlink alias
- **THEN** the receipt supplies no deletion authority for that path
- **AND** the Git effect owner refuses root, traversal, linked, and tracked
  removal targets even when called independently of the archive adapter
- **AND** a failed command with an exactly bound archive path may still be
  compensated through the same owner
- **AND** remaining unowned content is preserved and reported as retained
  residue; a restored index alone does not prove compensation complete

#### Scenario: A coverage regression exposes incomplete runtime-consumer observation

- **WHEN** a current consumer root is not a readable real directory, or a nested
  entry is linked, unreadable, neither a directory nor a regular file, or cannot
  be completely enumerated
- **THEN** the existing activation observer reports unknown consumers and blocks
  generation retirement instead of treating an incomplete scan as no references
- **AND** a dangling root link is not a genuinely absent consumer directory
- **AND** initial observation failure preserves the selector, Lease state, and
  runtime generations
- **AND** readable nested receipts retain their referenced generations through
  the same observer for operations, transactions, and ref intents

#### Scenario: A coverage regression exposes destructive start compensation

- **WHEN** Work Lane start fails after recognizing existing resources or while
  creating new resources
- **THEN** compensation applies only to proved creations of that invocation,
  preserving reused worktrees, their contents, refs, and Lease rows
- **AND** a missing worktree effect receipt cannot authorize deletion of a path
  that appeared during the operation
- **AND** new worktree cleanup does not force removal of later user content;
  failed or unknown removal retains the supporting ref and Lease
- **AND** only a newly acquired exact four-field Lease can be revoked through
  the existing revocation owner; expiry drift blocks removal and preserves the ref
- **AND** cleanup failure remains visible rather than becoming a clean rollback

#### Scenario: Accepted runtime expectation observes immutable source objects

- **WHEN** the accepted checkout contains untracked observations or staged
  source/version edits, or the canonical checkout is detached
- **THEN** runtime expectation compiles the configured accepted ref's exact
  commit, tree, and canonical version blob without modifying checkout contents
- **AND** accepted-ref advancement changes the expected identity, while invalid
  accepted version bytes fail closed
- **AND** constructing a runtime still requires the wheel's complete build
  identity to equal that accepted expectation; mutable source cannot be silently
  labeled as accepted

#### Scenario: Coverage exposes obsolete coordination projection semantics

- **WHEN** current peer scopes and candidate progress are observed with valid
  four-field Leases
- **THEN** the collaboration projection reports those facts without inventing
  queue membership, queue age, or mutation-admission order from Lease data
- **AND** unknown or deferred scope takes precedence over overlap; overlap
  requires coordination and disjoint scopes remain independent
- **AND** candidate lag takes precedence over a stale progress interval; neither
  advisory condition mints mutation authority

#### Scenario: Design-integrity failure remains diagnosable

- **WHEN** a tracked canonical design owner, required projection, or root axiom
  document is missing
- **THEN** the existing design-integrity audit returns its exact blocking
  missing-document finding rather than throwing during an auxiliary check
- **AND** derivation comparison uses the same observed document set; an untracked
  document cannot silently become the canonical owner
- **AND** the root README and engineering axioms preserve the canonical
  distinction between transient Commitment and durable Attestation, rather
  than reviving the retired persistent-Commitment model

#### Scenario: Hosted proof crosses an identity boundary

- **WHEN** a hosted provider supplies a locked test environment and executes the
  complete test surface under a less privileged identity
- **THEN** all declared native executables are available before the proof starts
- **AND** run-as control inputs are consumed exactly once at the privilege
  boundary and are absent from the descended test environment
- **AND** the complete lock-bound Node package tree is resolved once at the
  repository session boundary and inherited by OpenSpec, package construction,
  nested tests, and Node-backed quality tools through one absolute coordinate
- **AND** repository-owned caches and other tool entrypoints inherited by
  nested processes use absolute, locked coordinates
- **AND** no nested test or build falls back to an ambient executable, cache, or
  network resolution
- **AND** the resulting evidence remains attributable to that hosted provider
  and exact HEAD

#### Scenario: A parallel test worker is lost

- **WHEN** a pytest worker crashes or a thread timeout terminates it during the
  current proof
- **THEN** the Python test gate records one terminal failure for that proof
- **AND** xdist does not restart a worker or replay the lost test in the same
  proof attempt
- **AND** the failure identifies the lost worker and test
- **AND** the gate does not increase timeout, retry the test, or weaken the
  required test surface.

#### Scenario: The configured floor is weakened

- **WHEN** a policy change would admit a measurement below 95 percent
- **THEN** the executed boundary regression fails independently of the changed
  declaration
- **AND** restoring the required floor rejects a 94 percent measurement and
  accepts a 95 percent measurement when all other evidence preconditions hold
- **AND** excluded product paths, disabled branches, suppressed lines, or tests
  without behavior assertions are not valid ways to satisfy the requirement

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
owner and one primary reason to change. A package directory and its modules
SHALL express a real semantic boundary rather than implementation convenience.
Ambiguous modules, facades, aliases, private cross-module imports, mixed command
owners, empty package shells, and mechanical suffix splits SHALL block proof.

#### Scenario: A generic module has no closed semantic contract

- **WHEN** the module-layout gate observes `core`, `common`, `shared`, `utils`,
  `helpers`, `base`, `manager`, `service`, or another configured ambiguous name
- **THEN** the module must be absorbed, precisely renamed, split on a real
  semantic axis, or deleted
- **AND** splitting only to satisfy ELOC or retaining the old path as a facade
  is not remediation

#### Scenario: An empty package shell is observed

- **WHEN** a package contains only `__init__.py` and has no child package,
  resource boundary, registration boundary, or public import boundary
- **THEN** the package SHALL be deleted and its consumers SHALL import the
  concrete owner or its parent package
- **AND** an empty `__init__.py` SHALL NOT be retained as a marker

#### Scenario: A package contains one implementation module

- **WHEN** a package contains exactly one implementation module and no child
  package or independent package-level boundary
- **THEN** the module SHALL move to the nearest semantic parent and the package
  SHALL be deleted
- **AND** the move SHALL be rejected as a mechanical simplification if the
  package owns a distinct public namespace, resource boundary, registration
  boundary, or independent reason to change

#### Scenario: A package has only an initializer and child packages

- **WHEN** a package contains no implementation module but contains child
  packages
- **THEN** it SHALL be retained only when its path is a deliberate semantic
  namespace or public boundary documented by its consumers
- **AND** otherwise its children SHALL be moved to the nearest real semantic
  parent and the shell SHALL be deleted

#### Scenario: A suffix split is proposed

- **WHEN** one module is split into same-level files differing only by a
  historical suffix such as `_core`, `_helpers`, `_impl`, or `_runtime`
- **THEN** the split SHALL be rejected unless each resulting owner has a
  distinct invariant, consumer boundary, and primary reason to change
- **AND** a real multi-owner boundary SHALL use a semantic subpackage rather
  than a flat suffix family

#### Scenario: Physical layout is audited after a move

- **WHEN** module-layout proof evaluates the repository
- **THEN** every moved symbol has one defining owner, every consumer resolves to
  that owner, and no retired path, facade, or private import remains
- **AND** the audit SHALL report the exact path and owner relation for every
  missing, duplicate, orphan, or conflicting result

### Requirement: Direct Source Budget

Source budget SHALL be measured directly from repository files without worker,
replay, shadow, or self-referential admission runtimes. Coordinates SHALL remain
non-compensatory. The native source-budget declaration SHALL own numeric limits.
Python product and test limits SHALL be required; other coordinates SHALL remain
observations unless explicitly bounded. Size SHALL constrain maintenance cost,
not substitute for semantic preservation, behavior, or the quality floor.

#### Scenario: One budget coordinate exceeds its limit

- **WHEN** an explicitly bounded coordinate exceeds its declared limit
- **THEN** `ethos prove --gate source-budget --json` blocks even if other
  coordinates have unused capacity
- **AND** equality with the limit passes that boundary
- **AND** deletion of necessary semantics or tests, formatting compression, and
  relabeling handwritten source as generated content cannot remediate the gap

#### Scenario: No project-total ceiling is declared

- **WHEN** product and test limits are valid and no aggregate limit is declared
- **THEN** all admitted handwritten categories remain measured and reported
- **AND** the aggregate does not acquire an implicit zero, 90000, or legacy limit
- **AND** explicitly declared optional limits remain enforced
- **AND** missing required limits, unknown coordinates, and malformed numeric
  limits fail closed

#### Scenario: Generated output and historical intent are observed

- **WHEN** generated dependency locks, generated architecture output, and archived
  OpenSpec artifacts are present
- **THEN** they are accounted separately from the maintained-source total
- **AND** their handwritten generators, architecture inputs, active OpenSpec,
  documentation, and configuration remain source
- **AND** existing generation, drift, lifecycle, and cleanup checks still apply

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

Full release proof SHALL build deterministic Python artifacts and exercise the
complete package-only lifecycle through one `local-install-smoke` owner. Help,
version, module origin, package/runtime identity, hooks, continuations and
artifact digests SHALL bind the same stable HEAD. Python tests SHALL verify gate
declarations, orchestration and pure contracts without another wheel install,
runtime materialization or repository lifecycle execution.

#### Scenario: Offline installation succeeds

- **WHEN** `uv run --frozen --offline python -m nox -s install_smoke` completes
- **THEN** one wheel installation SHALL activate an immutable Git-common runtime
  without a source-checkout or ambient `ethos` dependency
- **AND** the acceptance transaction SHALL create one environment, install the
  frozen production dependency closure into it exactly once, and install the
  wheel into that same environment without resolving dependencies again
- **AND** the selected runtime manifest, wheel digest, source commit, source
  tree, distribution version, and runtime digest SHALL agree
- **AND** the selected runtime SHALL remain executable after its bootstrap
  environment is removed and SHALL repair a stale hook projection through its
  own public continuation
- **AND** the installed runtime SHALL start a first Work Lane, expose the exact
  official OpenSpec metadata prewrite continuation, and recover a partially
  completed retirement through the public receipt-bound command
- **AND** the runtime SHALL exclude development-only dependencies
- **AND** disposable state SHALL stay under `build/runtime/**` and be removed
  before a passing receipt is published under `build/evidence/**`
- **AND** cleanup failure, source-checkout imports, network access, HEAD
  movement, or identity drift SHALL fail the gate without a passing receipt

#### Scenario: Full proof selects package acceptance

- **WHEN** the full proof graph executes both `unit-architecture` and
  `local-install-smoke`
- **THEN** package-only lifecycle acceptance SHALL execute exactly once through
  `local-install-smoke`, after its declared build dependency
- **AND** `unit-architecture` SHALL NOT install a wheel, activate a package
  runtime, create a lifecycle worktree, or replay package acceptance
- **AND** the local-install receipt SHALL report the result of every required
  package-only lifecycle assertion for the exact HEAD
- **AND** installed runtime and lane command observations SHALL preserve the
  validated public result, exit code, and captured stderr without introducing
  another policy or lifecycle owner

### Requirement: Supply Chain Evidence

Release proof SHALL produce deterministic package digests, SBOM, provenance,
and provider-specific publication attestations through bounded release owners.
Every generator SHALL be selected through its current unique policy owner; a
mutable tool version embedded in specification prose, documentation, installer
defaults, or generated provider files SHALL NOT become a parallel owner.

#### Scenario: A release artifact is prepared

- **WHEN** terminal full proof and publish readiness run at one immutable HEAD
- **THEN** local package, SBOM, provenance, GitLab, and GitHub observations remain
  separately attributable
- **AND** matching artifact digests are required before a dual-provider release
  is admitted
- **AND** the generator identity and version match the current policy owner

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

### Requirement: Repository semantic ownership is closed

ETHOS SHALL mechanically derive a finite semantic relation from current native
repository carriers and SHALL require every governed semantic identity to have
exactly one current owner and a complete producer, consumer, and selector
relation. The evaluation SHALL preserve provenance until it has classified all
missing, duplicate, orphan, superseded, conflicting, and unknown relations.

#### Scenario: A semantic identity has two current owners

- **WHEN** two current native declarations claim the same governed identity
- **THEN** repository audit reports a duplicate-owner gap naming both sources
- **AND** set deduplication does not hide the conflict

#### Scenario: A required relation is incomplete

- **WHEN** a current producer, consumer, or selector lacks its required
  counterpart
- **THEN** repository audit reports the precise orphan or missing relation
- **AND** the aggregate verdict is not `pass`

#### Scenario: Native carriers supply executable ownership

- **WHEN** repository audit derives executable owners
- **THEN** host executables come from the runtime surface, downloaded tools from
  native supply policy, and script executables only from scripts selected by a
  gate or provider plus their explicit transitive script calls
- **AND** an unselected script or unrelated configuration file does not become
  an owner merely because it exists

#### Scenario: Historical material mentions a retired identity

- **WHEN** an archived Change, evidence record, generated artifact, example, or
  superseded document contains an old identity
- **THEN** it is not admitted as a current owner or consumer
- **AND** exclusion follows structural carrier state rather than a literal
  exception list

#### Scenario: A current specification prohibits a retired command

- **WHEN** an OpenSpec scenario names a retired command only as the object of a
  prohibition or rejection rule
- **THEN** repository audit does not classify that command as a current consumer
- **AND** positive GIVEN or WHEN command subjects remain observable consumers

#### Scenario: A selected carrier cannot be parsed

- **WHEN** a current selected Markdown, TOML, JSON, YAML, or Python carrier
  cannot be parsed by its native parser
- **THEN** repository audit reports that exact carrier as `unknown`
- **AND** the parse failure cannot collapse into an empty passing observation

### Requirement: Controlled supply-chain identities have one owner

Every direct dependency, downloaded tool, runtime, hosted action, and container
image controlled by ETHOS SHALL have exactly one current semantic version owner.
Lockfiles, integrity hashes, generated provider files, and documentation SHALL
be derived or mechanically checked projections of that owner rather than
independent declarations.

#### Scenario: A controlled identity is audited

- **WHEN** repository supply-chain proof inventories current declarations,
  installers, locks, CI projections, and release metadata
- **THEN** each controlled identity resolves to exactly one semantic owner
- **AND** duplicate owners, orphan literals, missing integrity bindings, and
  projection disagreement block proof with their exact paths

### Requirement: Controlled direct inputs use stable current releases

Every controlled direct supply-chain input SHALL resolve to the current stable
release available from its native package manager or authoritative upstream at
verification time. Exact locks, immutable action commits, container digests,
and downloaded-artifact checksums SHALL bind the selected releases.

#### Scenario: A stable release is newer than the declared input

- **WHEN** the authoritative resolver observes a newer stable release for a
  controlled direct input
- **THEN** supply-chain proof reports the declared owner as stale
- **AND** provider projections and integrity material remain invalid until they
  agree with the updated owner

#### Scenario: An upstream has prerelease and stable versions

- **WHEN** the latest upstream version is a prerelease but an earlier stable
  release exists
- **THEN** the stable release remains the selected current version
- **AND** prerelease adoption requires a separate explicit product decision

### Requirement: Environment tools do not become repository authority

Developer environment and binary acquisition tools MAY implement a declared
supply-chain projection only when they replace incumbent machinery and preserve
offline, integrity, runtime, and proof boundaries. They SHALL NOT become a
second dependency graph, task graph, lifecycle, evidence ledger, or installed
ETHOS runtime requirement.

#### Scenario: A tool manager is proposed

- **WHEN** a tool manager can resolve versions but no incumbent owner or
  installer is deleted
- **THEN** the proposal remains a benchmark and is not added to the repository
- **AND** adoption requires a separately proved replacement with net deletion

### Requirement: Full proof covers hosted offline quality owners

ETHOS SHALL include every required offline repository-quality owner used by
hosted acceptance in its canonical full proof set.

#### Scenario: Repository hygiene fails before publication

- **WHEN** tracked source contains a forbidden quality suppression
- **THEN** the exact-HEAD full proof fails through the repository-hygiene gate
- **AND** hosted CI does not become the first observer of that defect.

### Requirement: Full proof validates deterministic hosted projections

ETHOS SHALL include each deterministic repository-owned syntax validator used
by hosted acceptance in its canonical full proof set. The gate SHALL invoke the
existing validator owner directly, bind its exact command and policy identity
into proof evidence, and retain hosted provider execution as a separate evidence
plane.

#### Scenario: A GitHub workflow uses an invalid expression context

- **WHEN** a tracked GitHub Actions projection contains an expression or context
  that the provider rejects deterministically
- **THEN** exact-HEAD full proof fails through the declared GitHub workflow
  syntax gate before publication
- **AND** the gate invokes the repository's existing actionlint owner exactly
  once
- **AND** a local syntax result does not claim that hosted GitHub CI passed.

#### Scenario: A hosted workflow projection is valid

- **WHEN** the tracked template and generated GitHub workflow are equal and the
  declared syntax owner accepts the generated workflow
- **THEN** exact-HEAD full proof records the syntax gate's command identity and
  passing result
- **AND** hosted GitHub CI remains independently observable after publication.

### Requirement: Hosted verification preserves its evidence plane

Hosted CI SHALL execute declared source-quality owners against the exact event
object without requiring a local Work Lane, Lease, candidate checkout, active
Change, or installed mutation hooks. Its result SHALL remain host observation,
not repository acceptance proof, and SHALL retain gate and command failure
facts. Local proof, native package conformance, and provider success remain
independent obligations.

#### Scenario: Hosted checkout has no local lifecycle state

- **WHEN** hosted verification runs at the expected object
- **THEN** the declared default gate set, including coverage-floor, executes with its dependency closure through the existing gate owner
- **AND** official OpenSpec validation runs from the locked repository supply
- **AND** absent local candidate/runtime state does not authorize mutation or invalidate a passing host observation

#### Scenario: Result is stale, malformed, empty, or unsuccessful

- **WHEN** execution fails, HEAD changes, coordinates disagree, required gaps remain, or the observation envelope is invalid
- **THEN** the hosted receipt blocks and preserves the available diagnostics
- **AND** no passing local status or unrelated proof can override that result

#### Scenario: Locked runtime export has no ambient Python

- **WHEN** a package runtime invokes uv with its authenticated interpreter in an offline minimal environment
- **THEN** uv selects that exact interpreter without a download or ambient rediscovery
- **AND** lock, dependency, and runtime identity checks remain enforced

### Requirement: Quality Execution Closure

The declared quality graph SHALL select and execute each required obligation
once for the requested evidence plane. Local CI and repository proof SHALL
reuse the same gate identities, dependency closure and shared runner rather
than maintain independent membership or scheduling state. Offline source
correctness, online freshness, package verification and hosted observation
SHALL remain distinguishable; an unobserved external property SHALL NOT be
reported as a passing local property.

#### Scenario: The same quality plane is invoked from two entrypoints

- **WHEN** local CI and repository proof evaluate the same source and requested
  quality plane
- **THEN** their required gate identities and dependency closure agree
- **AND** each required check executes at most once through its existing owner
- **AND** the result identifies checks outside that evidence plane without
  silently dropping obligations or claiming hosted success

#### Scenario: A prerequisite did not pass

- **WHEN** execution is requested and a gate has a failed, unknown or unexecuted prerequisite
- **THEN** the shared runner does not execute that dependent gate
- **AND** its result is blocked and identifies the unmet prerequisite
- **AND** independent diagnostic checks may continue within the declared budget

#### Scenario: Coverage fails before package delivery

- **WHEN** the required coverage-floor result is not passing
- **THEN** dependent package creation and installation do not execute
- **AND** no success receipt is emitted for the incomplete quality closure

#### Scenario: External observation is unavailable

- **WHEN** a requested online freshness or hosted-observation check cannot
  obtain its declared evidence
- **THEN** the result records unknown or blocked with an actionable cause
- **AND** offline source correctness is neither relabeled as external assurance
  nor made dependent on an undeclared remote

#### Scenario: Readiness is not executed proof

- **WHEN** the graph is projected without execution
- **THEN** all planned results remain unknown with no exit code
- **AND** unmet execution prerequisites are not reported as observed failures

#### Scenario: Fallback evidence must describe the tested source

- **WHEN** local CI is requested against uncommitted source or an invalid selection
- **THEN** it records a non-passing preflight result without executing the closure
- **AND** changes to HEAD, working bytes or policy during execution invalidate the result

#### Scenario: Execution evidence is incomplete or interrupted

- **WHEN** execution is interrupted or has missing, duplicate, mismatched or unsuccessful results
- **THEN** the fallback receipt cannot report success
- **AND** a non-passing record exists before execution and records incomplete observation

### Requirement: Independent test work is distributable

The Python test owner SHALL use native item-level work stealing for parallel
execution without changing selected tests, worker limits, isolation or coverage
requirements. Serial execution SHALL remain supported.

#### Scenario: One module contains the longest independent test scope

- **WHEN** multiple workers execute independent test items in that module
- **THEN** the scheduler can distribute its pending items across workers
- **AND** the collected test identities and required outcomes remain unchanged

### Requirement: Hosted test feedback is visible and source bound

Both hosted projections SHALL publish test-owned JUnit and coverage artifacts,
including outputs available after failure. GitLab SHALL declare native test and
coverage reports. GitHub SHALL expose a native job summary with the exact source,
proof outcome and available test observations. Reporting SHALL NOT mint proof,
hide failed execution or fabricate successful missing observations.

#### Scenario: A hosted test fails

- **WHEN** a test run produces failing JUnit results
- **THEN** available reports remain uploaded and inspectable
- **AND** the hosted job retains its non-passing execution result

#### Scenario: Test observations are unavailable

- **WHEN** JUnit or coverage output is missing or malformed
- **THEN** the summary explicitly identifies unavailable observations
- **AND** it does not substitute zero tests or a passing coverage result

### Requirement: Dependency-ready execution without unrelated barriers

The shared runner SHALL execute each admitted gate at most once when its actual
prerequisites have completed, without awaiting unrelated readers. It SHALL
respect bounded capacity, exclusive writers, deterministic result order and
failed-dependency blocking. Scheduler state SHALL be transient.

#### Scenario: A ready child has an unrelated slow peer

- **WHEN** one prerequisite finishes while an unrelated reader remains active
- **THEN** its ready child can use free capacity before that reader finishes
- **AND** returned evidence order is independent of completion order

#### Scenario: A writer becomes ready

- **WHEN** a declared writing gate is ready while readers are active
- **THEN** the runner drains active readers before executing the writer alone
- **AND** no new check overlaps that writer

#### Scenario: An invalid plan is supplied

- **WHEN** the graph has a cycle, missing dependency, duplicate node or invalid capacity
- **THEN** validation rejects it before any check executes

#### Scenario: A dependency fails or remains unknown

- **WHEN** a prerequisite does not return pass with exit code zero
- **THEN** its dependent and transitive dependents are blocked without execution
- **AND** independent diagnostics may complete

### Requirement: Inexpensive source failures precede heavy verification

The sole gate registry SHALL declare lint, schema, configuration, type, per-file
size and aggregate source-budget readiness before the heavy test gate. Public
proof and local CI SHALL consume that same dependency closure without a parallel
phase registry.

#### Scenario: A cheap source-readiness check fails

- **WHEN** a declared prerequisite of the test gate is failed or unknown
- **THEN** test execution, coverage consumption and dependent package delivery do not run
- **AND** the result names the failed prerequisite instead of fabricating test failures

#### Scenario: All source-readiness checks pass

- **WHEN** the requested graph is valid and its readiness prerequisites pass
- **THEN** all selected tests and existing coverage and delivery obligations remain required
- **AND** dry-run still projects unknown rather than claiming executed success

### Requirement: Package identity tests consume locked build supply

Package identity and source-distribution tests SHALL execute with the declared
locked interpreter and its installed build dependencies. An empty ambient cache
SHALL NOT change their verdict when that supply is complete.

#### Scenario: Ambient build cache is empty

- **WHEN** package identity tests run offline with an empty cache
- **THEN** direct and source-distribution builds use the locked environment
- **AND** exact source identities and bundled Node package parity are verified

### Requirement: Native verification tool supply

Native verification tools SHALL use one materialization owner reading their
versioned, digest-bound declarations. Supply SHALL use controlled cache storage,
never system installation or ambient executable trust. Preparation SHALL verify
regular archive members, executable bytes and version; serialize concurrent
writers and atomically replace only the selected executable. Invalid supply
SHALL preserve prior bytes and remove owned preparation scratch.

#### Scenario: Clean supported runner

- **WHEN** a supported runner lacks an ambient scanner or budget executable
- **THEN** preparation verifies and installs both declared tools in owned cache storage
- **AND** callers receive their exact directories without administrator privileges

#### Scenario: Invalid or unavailable supply

- **WHEN** the archive, digest, executable version or platform is invalid or unavailable
- **THEN** verification fails before tests with the original supply diagnostic
- **AND** prior executable bytes remain unchanged and owned scratch is removed
- **AND** stale passing receipts and test reports cannot represent this attempt

#### Scenario: Verified cached archive

- **WHEN** the declared archive exists in the project cache
- **THEN** preparation verifies it again before restoring the executable
- **AND** changed cached executable bytes are not trusted as the declared supply

#### Scenario: Unchanged verified executable

- **WHEN** the cached executable is a regular executable with bytes matching the verified archive
- **THEN** preparation rechecks its version without rewriting or replacing the file
- **AND** reuse still rejects a corrupt archive or failed version observation

#### Scenario: Damaged cached executable

- **WHEN** the cached executable is missing, altered, non-executable or a symbolic link
- **THEN** preparation validates a replacement before atomically installing it
- **AND** it does not write through the symbolic link or change its target

#### Scenario: Repeated or concurrent preparation

- **WHEN** multiple invocations request the same declared tool identity
- **THEN** a bounded lock serializes preparation and verified unchanged bytes are reused
- **AND** invocation count does not create additional archives or executable generations

#### Scenario: Cache path escapes through a link

- **WHEN** a selected cache path is symlinked or otherwise unsafe
- **THEN** preparation rejects it before writing or replacing external content

#### Scenario: Linked worktrees reuse native supply

- **WHEN** two worktrees share one Git common directory and no explicit CI cache root is selected
- **THEN** their locked native tool supply uses the same Git-common cache
- **AND** concurrent preparation uses one bounded lock and downloads at most once
- **AND** the verified archive remains available after one worktree is retired.

#### Scenario: Explicit CI cache ownership remains selected

- **WHEN** a CI invocation selects an explicit tool cache root
- **THEN** native supply uses that root instead of the Git-common default
- **AND** archive and executable verification remain unchanged.

### Requirement: Source-bound runtime fixtures

Runtime fixtures SHALL execute isolated children from their own Python prefix
and selected source, sharing declared dependencies without inheriting another
checkout's package projection. Executed child-origin checks SHALL establish
this binding; parent imports and fixture file existence are insufficient.

#### Scenario: Distinct parent source

- **WHEN** the selected source differs from the parent interpreter's checkout
- **THEN** an isolated child reports the fixture prefix and selected module path
- **AND** dependencies remain shared without weakening runtime inventory checks

### Requirement: Explicit archive fixture clocks

Archive collision fixtures SHALL use one explicit clock and matching archive
path for each scenario, independent of collection time and wall-clock rollover.

#### Scenario: UTC date boundary

- **WHEN** collision scenarios execute on either side of the declared UTC midnight
- **THEN** real Git collisions preserve existing bytes or reject preservation conflicts
- **AND** absent collisions remain valid without altering production date semantics

### Requirement: Declared file-size policy is strict and observable

ETHOS SHALL compile an optional file-size policy through the rules configuration
owner. Declared ceilings SHALL be positive integers, without coercion, unknown
fields or per-file exemptions. Omitted role limits SHALL inherit the declared
default. An absent declaration SHALL impose no hidden generic ceiling; malformed
declarations SHALL block rather than become absent.

#### Scenario: Invalid or coercible policy

- **WHEN** a present declaration has invalid TOML, shape, field names or limits
- **THEN** the public size gate blocks with a policy-path-bound cause
- **AND** booleans, strings, floats, zero and negative values are not limits
- **AND** continuation derives exact prewrite without granting write authority

#### Scenario: Optional policy is absent

- **WHEN** a generic repository has no file-size declaration
- **THEN** the report states not configured without imposing a runtime ceiling
- **AND** this does not authorize removing repository-required governance policy

#### Scenario: Valid ceiling is enforced

- **WHEN** a measured file equals its declared role ceiling
- **THEN** that boundary passes and one additional effective line blocks
- **AND** unused capacity elsewhere cannot compensate for the violation

#### Scenario: Invalid and unavailable source differ

- **WHEN** a source has invalid Python syntax or encoding
- **THEN** the report blocks with the path and cause rather than a fallback count
- **AND** an inaccessible required source or policy remains unknown
- **AND** neither failure is reported as measured zero or a valid absent input

### Requirement: Version metadata has an effective interpretation owner

ETHOS SHALL enforce necessary version boundaries through their owning readers.
A portable gate declaration SHALL accept only its supported format. Executable
policy shipped inside one immutable package SHALL share that package identity;
unused native configuration labels SHALL be removed instead of given artificial
validators solely to justify their presence.

#### Scenario: Unsupported gate declaration is supplied

- **WHEN** a gate registry declares an unsupported or malformed version
- **THEN** the native loader rejects it before any gate executes
- **AND** the supported declaration still produces its original dependency graph

#### Scenario: Native configuration label has no interpretation consumer

- **WHEN** a version label does not affect native parsing, interpretation or compatibility
- **THEN** removing it preserves the relevant native behavior
- **AND** tool release versions, package locks and integrity digests remain intact

#### Scenario: Package-local policy has one identity

- **WHEN** topology policy is loaded from its immutable package
- **THEN** no independent policy version can override the interpreting package
- **AND** malformed policy and checkout overrides remain rejected

### Requirement: Python visibility follows semantic ownership

ETHOS SHALL enforce private-module and private-symbol ownership across every
governed Python consumer. Import spelling and aliases SHALL NOT widen access.
A shared public operation SHALL expose a real consumer capability rather than
rename internal coupling. Tool coverage claims SHALL match exercised behavior.

#### Scenario: Private module crosses an owner boundary

- **WHEN** a consumer outside the private module's immediate semantic package imports it
- **THEN** the existing layout gate rejects the dependency for either import spelling
- **AND** legitimate direct package-internal consumers remain allowed

#### Scenario: Private symbol crosses a module boundary

- **WHEN** another module imports a private symbol, including an aliased or relative import
- **THEN** the existing visibility owner reports the defining and consuming modules
- **AND** protocol dunder names are not mistaken for private implementation names

#### Scenario: Resource defaults are interpreter-owned

- **WHEN** a caller changes CWD or supplies an incompatible adopter-local schema
- **THEN** native default gates and skill schema meaning remain bound to their interpreter
- **AND** an explicit missing gate declaration fails instead of choosing a fallback

### Requirement: Native dependency audit covers every declared lock ecosystem

The dependency-security owner SHALL audit each declared Python and npm lock with
the selected native tool, preserve per-ecosystem observations, and bind its verdict
to unchanged source, manifests, locks and audit policy. A vulnerability blocks;
missing or invalid evidence is unknown. The same gate SHALL guard package delivery without making offline tests
depend on online advisory availability or claiming hosted assurance.

#### Scenario: npm is vulnerable while Python passes

- **WHEN** the native uv report passes and the native npm report identifies a vulnerable dependency
- **THEN** the aggregate audit blocks and retains both reports
- **AND** dependent package delivery does not run; offline tests remain independently available

#### Scenario: Observation fails or scope is incomplete

- **WHEN** an input is missing or a native audit times out, fails or returns malformed or inconsistent evidence
- **THEN** that ecosystem cannot pass and reports its exact unavailable boundary
- **AND** the other declared ecosystem is still observed within its bound

#### Scenario: Input changes during an audit

- **WHEN** a bound source, manifest, lock or policy changes before the result is recorded
- **THEN** the result is non-passing and cannot be reused as current proof

#### Scenario: Complete native checks pass

- **WHEN** both native audits return valid clean observations over unchanged declared inputs
- **THEN** the aggregate audit passes with exact identities and raw evidence
- **AND** it makes no claim that hosted CI, deployment or user benefit has succeeded

### Requirement: Exact commit proof binds observed execution source

An exact-commit proof SHALL bind matching working content and index to its commit
before execution and revalidate their correspondence after execution, at issuance
and at selection of the new result. Missing or changed inputs SHALL prevent a
passing exact-commit result without altering the user's source or index.

#### Scenario: Source or index changes during a successful gate

- **WHEN** a gate returns success but tracked source, policy, index or non-ignored inputs differ from the bound commit
- **THEN** exact-commit proof is refused and the source mismatch remains observable
- **AND** no passing new Attestation is selected and no source content is restored or discarded

#### Scenario: Exact execution begins with dirty source

- **WHEN** a request would execute exact-commit proof over a different checkout or index
- **THEN** source admission refuses before executing the gates
- **AND** exploratory host observations remain distinct from repository proof

#### Scenario: Clean source produces ignored output

- **WHEN** the gates leave the bound source and index unchanged while writing ignored diagnostic output
- **THEN** source admission permits the otherwise valid proof

#### Scenario: Historical evidence lacks execution binding

- **WHEN** a proof lacks the required source correspondence in its carried plan
- **THEN** it cannot satisfy the new exact-source proof contract
- **AND** its historical record remains unchanged

#### Scenario: Adversarial isolation is required

- **WHEN** an authority requires protection from hostile writers between source observations
- **THEN** sampled source equality alone does not establish that stronger guarantee

### Requirement: Proof validation is independent of optional intent

Every proof-execution TransitionPlan SHALL validate the same supported semantic
fields whether its transient Commitment is present or absent. Immutable Mapping
containers SHALL NOT bypass validation.

#### Scenario: Unsupported Facts are rejected in both proof modes

- **WHEN** a proof plan carries an unsupported Facts field with or without Commitment
- **THEN** compilation rejects the model gap before any proof or Git effect

### Requirement: Secret admission requires credential evidence

Secret scanning SHALL recognize supported credential forms and credential-bearing
assignments without treating unrelated content-addressed Git identities as
credentials solely because a provider name appears elsewhere in the source.

#### Scenario: Referenced source identity is not a provider credential

- **WHEN** research names a provider and contains valid Git commit and tree IDs
- **THEN** the native scanner accepts that non-credential source

#### Scenario: Credential forms remain rejected

- **WHEN** source contains a provider-prefixed token or an unprefixed token assignment
- **THEN** the same native scanner rejects it without a file-specific exception

### Requirement: Hosted verification owns its native test prerequisites

Hosted verification SHALL prepare each native executable required by its tests
through the existing version-bound installer before executing the test gate.
Preparation SHALL belong to the invoking process, not another job. A failed
prerequisite SHALL prevent test execution, retain its diagnostic and remove stale
proof and test outputs without weakening assertions or increasing concurrency.

#### Scenario: Another job has prepared the scanner

- **WHEN** a clean verify job runs native scanner regressions after a separate
  secrets job passed
- **THEN** verify prepares the declared scanner in its own execution environment
- **AND** the unchanged real scanner assertions execute with that supply

#### Scenario: A required executable cannot be prepared

- **WHEN** either scanner or budget-tool preparation fails
- **THEN** proof does not execute and the supply failure is reported
- **AND** previous passing proof and test artifacts cannot be reused

### Requirement: Test attempt completion is committed last

The Python test owner SHALL invalidate previous completion under its existing
evidence lock before preparation. Completion SHALL be published only after
execution, owned cleanup and source freshness succeed. A fresh single attempt
SHALL discard earlier incomplete output. Cleanup SHALL unlink owned references
without changing external referent content or permissions.

#### Scenario: A same-source rerun fails or is interrupted

- **WHEN** preparation, execution, cleanup or final source observation fails
- **THEN** no prior completion marker can certify this attempt
- **AND** the coverage-floor owner refuses the incomplete evidence

#### Scenario: Partial results precede a fresh single attempt

- **WHEN** a previous attempt left worker fragments, shard results or reports
- **THEN** the single-attempt owner clears those outputs before executing tests
- **AND** the new result does not silently include the previous test population

#### Scenario: Owned cleanup encounters external references

- **WHEN** an owned cleanup target is a directory link or contains linked files
- **THEN** cleanup removes only the owned entries
- **AND** external referent content, mode and modification time remain unchanged

### Requirement: Hook declarations are selected immutable package data

The selected immutable package SHALL own one validated hook declaration.
Inspection SHALL read that manifest-bound declaration without a child process
or caller-source substitution. Missing data SHALL request successor installation;
unreadable or invalid data SHALL leave admission unarmed. Activation SHALL
preserve existing rollback and exact failure diagnostics.

#### Scenario: A predeclaration package is selected

- **WHEN** a selected package has no declarative hook contract
- **THEN** the reader reports missing support and derives the successor installation command
- **AND** it neither reinstalls the old package nor starts its historical query

#### Scenario: A package declaration is inspected

- **WHEN** native launchers are inspected from a selected package
- **THEN** the one declaration owner renders exact bytes without importing package policy
- **AND** no child process is started merely to read constants

#### Scenario: A declaration read fails during activation

- **WHEN** selected declaration data cannot be read after activation begins
- **THEN** the existing transaction restores prior selector, configuration and state
- **AND** public output retains the declaration failure instead of reporting armed hooks
- **AND** no implicit observation retry or effect replay occurs

#### Scenario: Selected declaration bytes drift

- **WHEN** selected declaration bytes differ from their runtime inventory
- **THEN** runtime currentness fails before the changed declaration can arm hooks
- **AND** neither cached values nor the invoking package declaration substitute

### Requirement: Projection acceptance obligations have one source

The terminal quality contract SHALL reference each required semantic invariant
and original principle source. Every obligation SHALL declare its scope, required
evidence and distinguishing rejection condition. Undefined parallel check IDs,
missing obligations, duplicate ownership and unknown source references SHALL
block export before expensive verification.

#### Scenario: Named checks have no proposition

- **WHEN** a contract lists required report IDs without defined source obligations
- **THEN** export fails with the exact undefined boundary
- **AND** passing geometry, identifiers or report counts cannot satisfy it

#### Scenario: Complete obligations share a semantic acceptance family

- **WHEN** every required graph invariant maps once to a source-backed family
- **THEN** export retains its proposition, source, evidence and rejection boundary
- **AND** the family does not duplicate or override product meaning

### Requirement: Faithfulness is judged on the declared medium and scope

A projection SHALL preserve source meaning across its declared artifact scope.
Static views require readable visible witnesses; multipage views require explicit
visible navigation and scoped coverage. Independent semantic review SHALL bind
the exact source, artifact, medium, reviewer and counterexamples. Structural
validation SHALL NOT be presented as that review or owner acceptance.

#### Scenario: Metadata covers an unreadable statement

- **WHEN** an ID is mapped but required meaning exists only in hidden content
- **THEN** semantic acceptance remains unsatisfied
- **AND** a valid mapping or geometric report cannot replace rendered review

#### Scenario: A coherent atlas distributes source meaning

- **WHEN** multiple visible pages jointly cover the declared source scope
- **THEN** each omission, aggregation and navigation route is explicit
- **AND** page-local success does not imply full-atlas faithfulness

#### Scenario: A presentation or shared view is intentionally partial

- **WHEN** a story, presentation, share or export declares a limited source scope
- **THEN** its visible relationships retain necessary guards, identities and authority boundaries
- **AND** it need not repeat unrelated product detail or claim complete coverage
- **AND** hidden document prose or leaving the mode cannot supply a missing condition

### Requirement: Comparison uses a qualified predecessor without weakening acceptance

A predecessor SHALL bind exact artifacts, source scope, applicable policy and
verified acceptance evidence before serving as a comparison floor. The candidate
SHALL satisfy current absolute obligations independently. Missing predecessor
qualification SHALL yield no comparative claim, not a fabricated regression,
automatic improvement or weakened floor.

#### Scenario: An old PASS lacks applicable evidence

- **WHEN** a predecessor's identity, scope or acceptance cannot be verified
- **THEN** it does not qualify as the comparison floor
- **AND** current absolute quality and semantic obligations remain required

#### Scenario: A candidate changes its own acceptance rule

- **WHEN** a candidate loosens policy to approve itself against a predecessor
- **THEN** trusted prior policy and explicit source review govern the transition
- **AND** the candidate's new rule does not certify its own acceptance

### Requirement: Source Identity Observation Is Bounded And Coordinate-Consistent

Source-build identity SHALL bind one observed commit and the complete effective
non-ignored overlay without changing the caller's index or working files. The
observation SHALL finish within one declared time budget or retain a typed
failure. HEAD movement during observation SHALL prevent a successful identity.

#### Scenario: HEAD moves while the overlay is observed

- **WHEN** HEAD changes after the initial source coordinate is read
- **THEN** identity observation rejects the mixed observation rather than returning
  the first commit paired with an independently selected later baseline.

#### Scenario: A native source query reaches its deadline

- **WHEN** a Git step exhausts the source observation's total deadline
- **THEN** the result retains command, root, timeout and available process evidence,
  removes its owned temporary index, and does not report a valid identity.

#### Scenario: Local overlay and index-only flags differ

- **WHEN** staged, unstaged, untracked, deleted or mode-changed content is present
- **THEN** the observer retains native full-overlay meaning, does not use a
  metadata-only shortcut, and preserves the caller's index bytes.

### Requirement: Closeout Projections Observe Only Their Required Facts

A closeout command or bootstrap projection SHALL consume the existing exact ref
and worktree topology owners without re-running unrelated runtime or Lease
admission. This reduction SHALL NOT replace the fresh checks performed before an
actual effect or reuse prior authorization.

#### Scenario: A command needs only the accepted worktree and candidate object

- **WHEN** the closeout projection derives its exact target command
- **THEN** the command uses the configured roles and current required coordinates
  without invoking the complete workspace-status collector.

#### Scenario: Candidate changes before an accepted effect

- **WHEN** candidate advances after the earlier closeout observation
- **THEN** fresh effect admission rejects stale coordinates despite any already
  rendered command or bootstrap projection.

### Requirement: Native Validation Outcomes Preserve Failure Meaning

ETHOS SHALL require both successful native validation execution and a readable
full validation result before accepting it. A failed exit SHALL remain a failure
without item diagnostics. Any invalid item SHALL remain a failure even when the
process exits successfully. Malformed consumed fields SHALL prevent acceptance.

#### Scenario: Failed execution has no item-level explanation

- **WHEN** the native validator exits unsuccessfully with empty or missing items
- **THEN** the public report retains a validation failure and its original result.

#### Scenario: A successful exit contradicts an invalid item

- **WHEN** the native process exits zero but one item has valid set to false
- **THEN** the public report rejects that item rather than accepting the exit code.

#### Scenario: The reported collection cannot establish item validity

- **WHEN** items or their consumed identity and validity fields are malformed
- **THEN** the public report identifies unreadable validation rather than omitting them.

### Requirement: Informational Native Findings Remain Informational

ETHOS SHALL preserve successful empty full reports and valid items containing
informational findings. It SHALL consume the official validity decision instead
of converting every issue into an error or reimplementing native spec semantics.

#### Scenario: Official validation succeeds with informational findings

- **WHEN** a successful full result contains only valid items with INFO findings
- **THEN** ETHOS accepts that validation while retaining the original findings.

#### Scenario: Official validation has no items

- **WHEN** a successful native full result declares an empty items collection
- **THEN** ETHOS accepts the empty validation without inventing an invalid Change.

### Requirement: Publication Results Preserve Observed Partial Effects

ETHOS SHALL retain observed applied peers independently of uncertainty about
remaining peers. An unknown later observation SHALL preserve partial execution
in the result, CLI summary and Attestation. Retry SHALL reobserve exact refs and
avoid pushing an already matching peer again.

#### Scenario: A later peer becomes unobservable

- **WHEN** one peer is confirmed applied and the next peer observation fails
- **THEN** the verdict remains unknown, progress is partial, and applied and pending peers remain explicit.

#### Scenario: No peer has been applied

- **WHEN** an unavailable preflight prevents every push
- **THEN** the result reports no performed publication rather than inventing progress.

#### Scenario: A successful push lacks its post-observation

- **WHEN** a push exits successfully but its required remote observation fails
- **THEN** the result retains the attempt and unknown outcome without claiming confirmed application.

### Requirement: Hook Runtime Validation Follows Effect Admission

ETHOS SHALL fully validate the selected immutable runtime before admitting a prepared branch update and reuse that observation only within its invocation. Only the prepared state of a reference transaction is governed: other states SHALL not start the runtime, and a prepared transaction without a governed update SHALL not inventory it. Malformed prepared input and damaged admission authority SHALL remain failures.

#### Scenario: A transaction only reports its outcome

- **WHEN** Git reports the preparing, committed or aborted state of a reference transaction, or prepares one without a governed update
- **THEN** the hook completes successfully without validating an unused runtime.

#### Scenario: One prepared batch contains multiple governed refs

- **WHEN** a prepared transaction changes multiple branch refs
- **THEN** one full runtime observation precedes the existing policy decision for each ref.

#### Scenario: Prepared admission selects a damaged runtime

- **WHEN** runtime validation fails before a prepared branch update
- **THEN** the hook rejects the transaction before executing its ref policy.

### Requirement: Identity Inspection Does Not Require Command Dispatch

ETHOS SHALL resolve and render invoking identity without loading unrelated
command dispatch. Native version output SHALL preserve human and JSON forms and
the existing source and runtime validation. Real registration, dispatch and
identity-observation failures SHALL retain their public error boundaries.

#### Scenario: Only the invoking version is requested

- **WHEN** the native CLI receives the global version flag
- **THEN** it renders identity without importing the command framework.

#### Scenario: Source observation fails during identity inspection

- **WHEN** identity observation encounters a Git failure or changing source
- **THEN** the public result preserves the exact error and continuation instead of a traceback or speculative reinstall.

### Requirement: Native Hook Execution Loads Only Required Semantics

Native Git hooks SHALL execute their package-owned protocol independently of interactive CLI dispatch. A reference transaction state other than prepared, and prepared input without a governed effect, SHALL not initialize admission dependencies. Actual admission SHALL use the existing policy owners and fresh runtime checks, without persistent reuse of authority. The superseded transport SHALL be removed.

#### Scenario: A native notification has no admission obligation

- **WHEN** a generated hook receives a reference transaction state other than prepared, or prepared input for unrelated refs
- **THEN** it completes without initializing the CLI or admission machinery.

#### Scenario: A native protocol envelope is malformed

- **WHEN** prepared reference-transaction input, or another hook's input, cannot be parsed as its expected protocol
- **THEN** the invocation fails without treating absent admission as permission.

#### Scenario: A prepared batch requires admission

- **WHEN** the hook receives one or more governed prepared updates
- **THEN** it fully validates the current runtime once before applying existing policy to each update.

#### Scenario: Prepared authority is damaged

- **WHEN** the selected runtime or required admission dependency is unavailable
- **THEN** the native hook rejects the update rather than using a notification fast path.

### Requirement: Provider behavior evidence counts native subtests

The product Python behavior provider SHALL capture pytest's report-log events with its JUnit and coverage reports, and SHALL validate JUnit totals against those events, so passing subtests that JUnit counts but does not emit are explained rather than rejected.

#### Scenario: A test passes its subtests

- **WHEN** the locked pytest run passes a test with subtests
- **THEN** the behavior evidence verifies
- **AND** its test total counts each subtest

#### Scenario: The event report is missing

- **WHEN** pytest writes JUnit but no event report
- **THEN** the behavior evidence blocks as `test_event_report_missing`

### Requirement: Provider coverage binds every committed Python subject

The product Python behavior provider SHALL bind each file in its coverage report to a committed Python subject of the repository, and SHALL require coverage only of product source subjects, so tests that execute committed tooling do not block the behavior evidence.

#### Scenario: A test executes committed tooling

- **WHEN** a passing test executes a committed Python file whose role is tooling
- **THEN** the behavior evidence verifies

### Requirement: Provider static analysis uses the shared line width

The product Python static provider SHALL run Ruff isolated from repository configuration with a line length of 100 columns, the shared formatter width of governed repositories.

#### Scenario: A line reaches the shared width

- **WHEN** an authored Python line is 100 columns long
- **THEN** the static evidence does not report `E501` for it

#### Scenario: A line exceeds the shared width

- **WHEN** an authored Python line is 101 columns long
- **THEN** the static evidence blocks with `E501`

### Requirement: Exact audit dispositions preserve strict delivery

The existing dependency-audit owner MAY admit explicitly selected local
development against a human-authorized disposition for the exact advisory,
locked package artifact, nodes, dependency snapshot and explicitly approved host.
Native observations SHALL remain unchanged; unselected development, CI, release,
installation and distribution SHALL retain the strict decision for every finding
that an official stable release fixes.

#### Scenario: A bundled component has no independent integrity

- **WHEN** native `inBundle` ownership identifies a component without child integrity
- **THEN** the disposition binds the containing independently locked artifact
  through the package-lock ownership chain and retains exact component version
  and node paths
- **AND** missing bundle ownership or artifact integrity remains unavailable,
  never an invented child identity

#### Scenario: Local permission has an accountable finite boundary

- **WHEN** the existing owner evaluates an explicitly selected local-development disposition
- **THEN** it requires an accountable owner, approval reference, rationale,
  approved host and finite offset-aware expiry
- **AND** native findings, counts, exit status and raw evidence remain unchanged
- **AND** an absent disposition grants no permission

#### Scenario: Unselected and delivery consumers remain strict

- **WHEN** default proof, security or build gates, CI, installation or distribution
  evaluate the source without an explicitly authorized local-development selection
- **THEN** they retain the same owner's strict production-release decision
- **AND** declared CI refuses the local-development selector rather than
  inheriting a host-local approval

#### Scenario: One advisory affects multiple npm package aggregates

- **WHEN** a complete native npm report refers transitively to one approved advisory
- **THEN** the owner resolves every aggregate reference to its concrete advisory roots
- **AND** exact active coverage may permit local development without changing the native blocked verdict
- **AND** production and release remain blocked without separate evaluators or package-name exclusions

#### Scenario: Authorization or observation cannot establish local permission

- **WHEN** approval expires, an advisory or locked identity changes, aggregate resolution fails, or required observation is unavailable
- **THEN** the local decision cannot pass and preserves the distinct expiry, identity or observation boundary
- **AND** a fresh attempt cannot renew approval through an earlier receipt timestamp
- **AND** changed source inputs, adverse Python evidence and interrupted attempts remain nonpassing

#### Scenario: Direct native release does not inherit local permission

- **WHEN** an explicit release build or install is requested through Nox
- **THEN** the same audit owner evaluates strict production-release scope before the release effect
- **AND** a local-development permission cannot authorize that effect

### Requirement: Findings without a stable upstream fix do not block

The dependency-audit owner SHALL report, without blocking any scope, a native
finding that no official stable release fixes yet. Fixable or unobserved findings
SHALL keep blocking until the supply is upgraded or an exact disposition applies.
Adverse Python package statuses are not advisories and SHALL keep the strict result.

#### Scenario: Every owning artifact already is its latest stable release

- **WHEN** every locked npm artifact that ships a finding, the bundling package for
  an `inBundle` component, already is its registry latest release, or a Python
  advisory's native fix versions name no newer stable release
- **THEN** the decision passes and lists the finding as unfixed upstream
- **AND** native findings, counts, exit status and raw evidence remain unchanged

#### Scenario: An upgrade can fix the finding or the observation is missing

- **WHEN** an owning artifact is behind its latest stable release, a Python advisory
  names a newer stable fix version, or the registry observation is missing or malformed
- **THEN** the finding blocks until the supply is upgraded or an exact disposition applies

#### Scenario: Landing reevaluates the captured observation

- **WHEN** landing or a Git hook reevaluates a captured audit
- **THEN** it reads the same-attempt upstream observation without network access
- **AND** an exact disposition keeps precedence over the unfixed-upstream report

### Requirement: Object coordinates share one typed native observation

ETHOS SHALL derive object identity and type from the same validated native batch
row. Commit and tag consumers SHALL reuse that observation rather than resolve
the same object again. Peeling SHALL bind the observed object ID, not a mutable
ref. Later reads, signature trust and effect authorization SHALL remain fresh.

#### Scenario: A selected tag moves during observation

- **WHEN** the tag ref changes after its initial native row is read
- **THEN** peeling and tree observation retain the originally selected object
- **AND** a later invocation observes the changed ref rather than a cached verdict

#### Scenario: Native object evidence is incomplete

- **WHEN** a query is absent, dangling, malformed or of the wrong object kind
- **THEN** existing absence, observation-failure and kind distinctions remain enforced
- **AND** SHA-1 and SHA-256 follow the same typed batch owner

#### Scenario: Native revision syntax exceeds the batch framing

- **WHEN** a valid revision expression contains whitespace
- **THEN** Git resolves it before the typed batch without a replacement revision parser

### Requirement: Resolved rule identity has one active definition

ETHOS SHALL admit at most one definition and version for each rule id in a
resolved RuleSet. A repository delta SHALL NOT shadow an active baseline identity.
Conflicts SHALL reach compilation and plan selection as explicit gaps, without
selecting a winner or returning a partial executable rule set.

#### Scenario: Duplicate identity is not composition

- **WHEN** active definitions repeat an id, even with identical contents or different versions
- **THEN** the typed contract rejects the set and the compiler reports the conflicting id
- **AND** rule selection returns the gap instead of executable selections

#### Scenario: Distinct rules retain shared execution

- **WHEN** distinct applicable rule identities require the same native gate
- **THEN** both rule meanings remain visible while existing gate deduplication is preserved

### Requirement: Quality applicability preserves carrier and native semantics

ETHOS SHALL resolve applicable quality obligations from accepted carrier facts
and native tool selection, not extensions alone. Frozen provenance SHALL retain
integrity obligations; generation SHALL NOT exempt actual build inputs.
Unknown required discovery SHALL NOT become empty successful coverage.

#### Scenario: Artifact provenance changes verification, not authority

- **WHEN** the native profile relates authored, generated and locked upstream code to its actual source owners
- **THEN** applicable behavior obligations remain and exact generated or upstream bytes require the existing product integrity provider
- **AND** labels, versions, filenames, or producer success alone cannot supply authenticity
- **AND** one gate may report both code axes without duplicating execution

#### Scenario: Native source observation is incomplete or over budget

- **WHEN** a declared source is missing, changed, oversized, or outside the supported observation boundary
- **THEN** the public result retains an explicit source-integrity gap and no Attestation is selected
- **AND** allocation and archive framing, metadata, count, and expansion limits apply to the complete invocation
- **AND** native parser termination, cache availability, or partial member equality cannot certify the unobserved remainder

#### Scenario: An artifact claim has no native source relationship

- **WHEN** a tracked code carrier claims a generated or snapshot role without a valid native source-contract member
- **THEN** the common subject owner reports its exact missing source relationship before native quality execution
- **AND** lint-clean bytes, labels and authored diagnostics cannot replace that prerequisite or supply an analysis exemption
- **AND** valid generated and upstream relationships retain authenticity and applicable runtime obligations

#### Scenario: A local lock reference and a native cache digest are valid

- **WHEN** an npm lock uses an in-root normalized parent reference or multiple supported SRI digests
- **THEN** the product preserves native lock-relative and strongest-available digest semantics
- **AND** one descriptor-bound reader observes the selected bytes without following repository-relative links or executing candidate configuration
- **AND** invalid member types remain typed validation failures through policy and public consumers

#### Scenario: Native inventory failure is not an empty repository

- **WHEN** Git file discovery fails because its index or transport is unreadable
- **THEN** size and other inventory-backed checks report unavailable input, not a passing empty set
- **AND** a genuinely empty valid repository remains distinct and admissible

#### Scenario: Early source scope includes candidate Python

- **WHEN** a governed worktree adds a nonignored Python file before staging it
- **THEN** the early size check measures that candidate instead of silently omitting it
- **AND** staging the same bytes cannot change the size verdict

#### Scenario: Markdown execution cannot silently shrink its scope or rules

- **WHEN** the declared tracked Markdown set is nonempty but a native glob selects none, or a nested configuration disables the required rule
- **THEN** the public gate reports the missing selection or effective-rule conflict instead of passing
- **AND** valid tracked Markdown remains checked by one effective configuration

#### Scenario: Declared system schema is malformed

- **WHEN** a system contract selects a syntactically readable but invalid JSON Schema
- **THEN** the public report returns a structured failed or unknown schema observation
- **AND** a native `SchemaError` cannot escape and erase the report

#### Scenario: Native discovery and explicit selection have different scopes

- **WHEN** native package discovery excludes a frozen source snapshot
- **THEN** the snapshot retains its provenance obligations rather than live-package checks
- **AND** explicit native selection is evaluated under its own declared scope
- **AND** relabeling implementation as evidence cannot silently remove hard obligations

#### Scenario: A native role owner projects carrier facts

- **WHEN** an adopter supplies repository-native role assignments
- **THEN** ETHOS SHALL bind them to the selected Git tree and account for every tracked carrier exactly once
- **AND** unresolved or conflicting roles SHALL remain unknown rather than remove an applicable obligation
- **AND** ETHOS SHALL validate the projection without copying the adopter's role parser or making it a second owner

#### Scenario: Source tests and artifact-qualified tests have different inputs

- **GIVEN** a native owner selects source tests separately from tests that require an installed package or release artifact
- **WHEN** ETHOS verifies source quality
- **THEN** it executes or consumes the selected source tests in the declared locked toolchain without inventing file-name exclusions
- **AND** artifact-qualified tests remain required at their input boundary, not run early or silently dropped
- **AND** a passing native command without per-subject evidence is insufficient, while verified evidence from that execution does not require a duplicate run

### Requirement: Formatting ownership names executable nonmutating checks

Each maintained carrier's declared formatter and format check SHALL resolve to
available native commands. The check SHALL not mutate source, and a write command
SHALL not be accepted as its own verification. Ownership metadata alone SHALL
not certify tool reachability or equivalent effective policy.

#### Scenario: A declared formatter session is absent

- **WHEN** a format owner names a Nox session that the native session list does not expose
- **THEN** the public ownership check reports the unreachable command instead of passing
- **AND** the valid formatter/check pair remains usable after owner repair

#### Scenario: A check writes or disables its rule

- **WHEN** the declared check equals a formatter write command or its effective config omits the required rule
- **THEN** the public check rejects that declaration and preserves the source bytes
- **AND** a genuine nonmutating check over the selected carrier passes

### Requirement: Native Python type checking covers executable support

The product quality gate SHALL use the type checker's native selection to cover
product code, repository tools, shared test support, architecture tests and the
root test runner. A successful check over only product source SHALL NOT claim
type coverage for those other carriers. Intentionally ill-typed unit-test
inputs remain subject to their runtime assertions, not a blanket static waiver.

#### Scenario: An executable support carrier has an invalid type

- **WHEN** a declared tool or test-support module contains a type error
- **THEN** the native type check reports the selected file and the required quality gate blocks
- **AND** an unavailable checker, invalid configuration or malformed diagnostic result cannot become a pass

### Requirement: Adopters share applicable quality obligations

ETHOS SHALL compile a common, versioned quality floor from observed repository
facts before selecting native checks. A repository profile MAY add domain
constraints and map native evidence, but omission, renaming or a candidate's
own changed policy SHALL NOT remove an applicable common obligation. The floor
SHALL express observable properties and explicitly accepted portable limits,
not ETHOS-specific paths, tools or code budgets.

#### Scenario: Binding is not quality qualification

- **WHEN** a valid new or existing repository has no checks for applicable obligations
- **THEN** adoption MAY report its binding effect, but readiness, proof and integration SHALL report the missing obligations rather than quality success
- **AND** an empty native proof floor or a passing command with no relevant evidence SHALL NOT satisfy them

#### Scenario: Native implementations differ but obligations do not

- **WHEN** two repositories use different native tools and layouts for the same applicable property
- **THEN** both are judged against the same scope and evidence contract
- **AND** neither must copy ETHOS's package layout or self-hosted gate commands

#### Scenario: Several native checks cover one property

- **WHEN** an applicable property spans several carrier or tool scopes
- **THEN** fresh admitted reports SHALL jointly cover every applicable subject
- **AND** a gate name, aggregate pass, or one report for only part of that scope SHALL NOT discharge the property
- **AND** shared native execution SHALL be reused rather than repeated for each rule

#### Scenario: Applicability follows repository facts

- **WHEN** a repository contains code, only documentation, or a versioned release target
- **THEN** code correctness, reader navigation, and release-version obligations apply to their respective observed subjects
- **AND** absent, ambiguous or unavailable required discovery is not treated as an empty successful check

#### Scenario: A candidate weakens its own quality policy

- **WHEN** a candidate removes a required check or narrows its source scope
- **THEN** the trusted prior floor still judges the candidate until an independently admitted policy transition replaces it
- **AND** local and hosted consumers reject a result set that omits a required obligation

### Requirement: Current Markdown stays within one navigable topic

Every tracked, current, hand-authored Markdown documentation file in ETHOS or a governed repository, including an active OpenSpec Change's proposal, design, tasks and delta specs, SHALL contain at most 512 nonblank physical lines, the repository paradigm's Markdown ceiling. The release-contract changelog, accepted OpenSpec specifications, the immutable OpenSpec archive and declared generated output SHALL retain their own carrier-specific checks.

#### Scenario: A current topic exceeds the ceiling

- **WHEN** a tracked current authored Markdown document exceeds 512 nonblank lines
- **THEN** the quality floor reports that exact source and blocks acceptance
- **AND** frontmatter, code fences, tables and quoted material count
- **AND** adding blank lines or relabeling current content as history does not
  satisfy the requirement

#### Scenario: Release history grows without a document-length limit

- **WHEN** the release-contract changelog exceeds 512 nonblank lines in total
  or within a single version section
- **THEN** the documentation length rule does not block that release history
- **AND** release-format obligations remain independent; a same-named ordinary
  document still exceeds the ceiling at 513 nonblank lines

#### Scenario: An active Change artifact exceeds the ceiling

- **WHEN** an active Change's design or delta spec has 513 nonblank lines
- **THEN** the quality floor reports that exact artifact and blocks acceptance
- **AND** passing official strict validation does not satisfy the requirement

#### Scenario: A normative OpenSpec carrier exceeds the document ceiling

- **WHEN** an accepted specification or an archived Change artifact exceeds 512
  nonblank lines
- **THEN** the documentation length rule does not block it solely for that count
- **AND** official OpenSpec validation, warnings, and semantic capability review
  retain their own authority

#### Scenario: A complex topic needs more space

- **WHEN** one topic cannot fit without losing necessary meaning
- **THEN** it is divided at coherent semantic responsibilities with a README
  route and repaired links, while retaining the original owner relationship
- **AND** arbitrary numbered fragments, copied paragraphs or hidden content
  do not count as progressive disclosure
- **AND** still-live obligations from a shortened source have an identified
  surviving canonical owner; exact Git recoverability alone does not prove
  semantic preservation

### Requirement: Release protection projects configured branch roles

ETHOS SHALL derive protected branch membership from the configured branch-role
policy for common and product release observations. Raw release declarations
SHALL remain distinct from resolved protection; missing optional declarations
SHALL NOT add product-packaging obligations.

#### Scenario: No copied branch declaration is needed

- **WHEN** a repository supplies configured roles and omits release branch copies
- **THEN** common and product observations project the same protected branches
- **AND** inline and registry-backed quality profiles preserve that meaning

#### Scenario: Copied or malformed policy cannot override roles

- **WHEN** release policy is malformed or its copied branches contradict the roles
- **THEN** observation and trusted-prior-policy publication admission reject it
- **AND** copied branch order cannot change the role-derived projection

### Requirement: Complete verification throughput preserves assurance

ETHOS SHALL use 900 seconds as the temporary complete-proof acceptance threshold
on the declared reference workstation at a measured, qualified worker count.
The measurement SHALL include preparation,
all selected gates and cleanup, retaining at least 95-percent combined Python
line and branch coverage and every existing behavioral acceptance obligation.

#### Scenario: Complete performance acceptance

- **WHEN** an optimized exact-source full proof is measured
- **THEN** its elapsed time is at most 900 seconds
- **AND** all required gates pass without narrower acceptance or hidden prework
- **AND** cold-computation and warm measurements are identified separately

#### Scenario: More workers improve verified throughput

- **WHEN** identical inputs at a higher worker count preserve results and isolation
- **THEN** ETHOS may adopt the faster count and qualify the complete proof there
- **AND** the two-worker baseline remains a comparison, not an execution ceiling
- **AND** process-loss recovery remains a separately tested obligation

#### Scenario: Subsequent throughput improvement

- **WHEN** the temporary complete-proof threshold is met
- **THEN** ETHOS evaluates the 600-second direction using measured remaining work
- **AND** that optimization direction does not block otherwise qualified delivery
- **AND** neither infeasibility nor completion is inferred from local speedups

#### Scenario: A later gate prevents whole-proof completion

- **WHEN** an executing proof has completed checks before a later gate fails or stalls
- **THEN** its existing diagnostic stream has already flushed their outcomes and timings
- **AND** events bind the exact source and plan while distinguishing scheduling from execution
- **AND** events never claim repository proof, replace the final result or pollute JSON stdout
- **AND** dry-run projection emits no executed-progress events

#### Scenario: Status reuses one observation but never stale runtime currentness

- **WHEN** public status projects workspace binding and hook readiness
- **THEN** both consume one fresh runtime observation for that invocation
- **AND** a later invocation independently detects changed selector or package bytes
- **AND** corruption blocks readiness and restoring valid bytes permits recovery
- **AND** mutation effects still obtain their own fresh admission

#### Scenario: Runtime inventory reduces duplicate work without omitting content

- **WHEN** runtime integrity observes the current filesystem
- **THEN** one traversal reuses entry metadata while hashing every regular file and internal link
- **AND** unreadable subtrees, unsupported entries and escaping links reject the observation
- **AND** valid inventories preserve exact content and permission identities across traversal order
- **AND** later observations detect changed bytes without cached readiness

### Requirement: Resource coordination preserves complete proof

Gate execution SHALL compose dependencies with declared shared and exclusive
resource-domain claims. Unknown access SHALL retain conservative coordination.
Resource claims SHALL NOT grant mutation authority or assert filesystem sandboxing.
Positive per-gate CPU reservations SHALL bound concurrent work against the
executor's observed capacity; they are scheduling claims, not CPU affinity.

#### Scenario: Independent required checks overlap

- **WHEN** selected source readiness passes and ready gates have compatible resource claims
- **THEN** the shared executor may run them concurrently within its capacity
- **AND** exact artifact consumers still wait for their producer
- **AND** results remain in canonical plan order without duplicate execution

#### Scenario: A writer conflicts with an active consumer

- **WHEN** exclusive access overlaps an active resource or its ancestor domain
- **THEN** those gates do not overlap
- **AND** an unspecified writer retains global exclusion
- **AND** a waiting writer does not prevent other compatible ready work from progressing

#### Scenario: Low-capacity hosts do not co-schedule heavy checks

- **WHEN** two otherwise compatible gates each reserve two units
- **THEN** they run once without overlap at capacity three
- **AND** they may overlap at capacity four when dependencies and locks permit
- **AND** one gate whose reservation exceeds capacity still runs alone

#### Scenario: Scheduling capacity does not redefine quality ownership

- **WHEN** a candidate whose history the running build shares changes a CPU reservation, a command or a gate in `system/gates.toml`
- **THEN** the predecessor and candidate keep the product registry owner without comparing bytes with an installed copy
- **AND** the candidate's execution policy still binds every changed obligation
- **AND** a repository without that history receives the adopter quality floor, even for a verbatim copy of the product registry

#### Scenario: Source proof disagrees with the installed ref guard

- **WHEN** a candidate proof passes but the selected installed runtime cannot compile the same exact policy
- **THEN** read-only landing reports the predecessor's gap before a ref intent or CAS
- **AND** the effect-time Git hook still rechecks fresh state independently

#### Scenario: Construction does not establish quality acceptance

- **WHEN** a package check succeeds but a required test or coverage check fails
- **THEN** complete proof remains blocked
- **AND** construction need not wait for unrelated test output it does not consume
- **AND** every selected source preflight and final proof obligation remains required

#### Scenario: Native resource claims require bounded qualification

- **WHEN** a gate declares complete resource coordination domains
- **THEN** its native owner accounts for source, outputs, scratch and shared supply
- **AND** the declaration is bound into proof policy and checked with overlap and conflict cases
- **AND** the real combined workload verifies artifact identities, source stability and cleanup
- **AND** invocation-local coordination does not replace native cross-process locks or fresh effect admission

### Requirement: Owned temporary resources converge after owner loss

Test, package and runtime scratch SHALL have an exact producer, consumer and
retention boundary. Normal finalization and bounded dead-owner recovery SHALL
reclaim only proved-owned, unreferenced bytes; missing liveness or ownership
SHALL remain UNKNOWN rather than authorize deletion.

#### Scenario: Repeated process death does not accumulate scratch

- **WHEN** normal, exceptional and killed invocations repeat with fixed inputs and concurrency
- **THEN** successor and idle maintenance bound dead-root count, bytes, inodes and reclamation delay
- **AND** live workers, shared uv supply and caller-owned basetemp survive
- **AND** contention, PID reuse, path replacement, links and read-only inodes cannot cause unsafe cleanup

#### Scenario: Long-running resource acceptance is independently observed

- **WHEN** source-bound real workloads are observed across 24- and 48-hour windows
- **THEN** growth, orphan age, high-water usage, cleanup latency and indexing cost remain within declared limits
- **AND** a short green test or one manual sweep does not satisfy this observation

### Requirement: Test failure bounds pending verification work

Parallel verification SHALL bound per-worker queued work independently of suite
size. Worker loss or an ordinary assertion failure SHALL stop pending work,
retain its native diagnostic, and allow the surviving gate owner to reclaim
owned scratch without replay. Native failure history MAY prioritize cases but
SHALL NOT narrow the required collection or authorize success.

#### Scenario: Native worker exits with a large pending collection

- **WHEN** one worker exits while many collected cases remain pending
- **THEN** surviving workers drain only their bounded in-flight assignment
- **AND** the gate fails without re-executing the crashed case or recording success
- **AND** the surviving owner removes its owned basetemp

#### Scenario: All workers remain healthy

- **WHEN** the same declared collection runs without worker loss
- **THEN** every collected case executes exactly once and the gate succeeds
- **AND** equivalent-workload timing remains separate from failure latency

#### Scenario: An ordinary assertion fails with pending cases

- **WHEN** a test assertion fails before the declared collection finishes
- **THEN** workers drain only their bounded in-flight assignment
- **AND** the gate records no success and removes owned scratch

#### Scenario: Failure ordering is warm or absent

- **WHEN** native pytest failure history identifies a previously failing case
- **THEN** that case is scheduled before later ordinary work
- **AND** successful warm and empty-cache attempts each execute the complete collection once

### Requirement: Verification preparation preserves its measured subject

ETHOS SHALL complete the selected proof's required source-side checks before
behavior tests or delivery, including carrier ownership, repository/product boundaries, docs,
dependencies, formats and secrets. Test preparation SHALL preserve executing-module
identity across workers so coverage remains attributable. Initial generated-artifact
drift SHALL block expensive work; the same owner SHALL check post-execution drift again.

#### Scenario: Focused offline verification is selected

- **WHEN** the caller selects offline tests or the offline default proof
- **THEN** readiness ordering does not select otherwise unrequested online checks
- **AND** full proof and delivery retain their declared security requirements

#### Scenario: A selected online source check fails

- **WHEN** the selected proof includes an online source check that fails or is unknown
- **THEN** dependent behavior and delivery do not execute
- **AND** their results retain the failed prerequisite rather than claiming execution

#### Scenario: A transition lacks its required proof

- **WHEN** land or archive admission finds missing proof or only a weaker default proof
- **THEN** its continuation requests executed full proof for the exact subject
- **AND** explicit Change selection is preserved without an intermediate weaker run

#### Scenario: A source observer depends on executed behavior

- **WHEN** an observation transitively consumes test or package results
- **THEN** it remains downstream and does not become its own prerequisite
- **AND** a passing selected graph remains executable without additional gates

#### Scenario: A native adapter has no admitted carrier home

- **WHEN** the carrier gate rejects a candidate adapter's placement
- **THEN** the dependent test suite is not executed
- **AND** its result identifies the failed prerequisite without claiming execution

#### Scenario: Generated residue exists before verification

- **WHEN** the repository already contains generated files outside their admitted homes
- **THEN** repository audit reports the existing artifact owner's failure
- **AND** tests, coverage, packaging and installed acceptance do not start

#### Scenario: Verification creates new generated residue

- **WHEN** initial artifact observation passes but executed checks create misplaced output
- **THEN** the existing post-execution artifact gate rejects it
- **AND** early readiness is not reused as evidence of the later filesystem state

#### Scenario: Runtime supply variants share one test worker

- **WHEN** package and source supply fixtures run before runtime verification
- **THEN** the imported runtime module retains its original source identity
- **AND** subsequent executed verification remains observable to coverage

### Requirement: Hosted supply preparation precedes expensive verification

Hosted verification SHALL prepare its declared scanner, budget and SBOM supply
through the existing supply owners before starting proof. Preparation failure
SHALL preserve native diagnostics and exit status, invalidate previous attempt
reports, and produce a failed hosted observation without executing proof.
Package execution SHALL still validate supply in its own current environment.

#### Scenario: A declared tool cannot be prepared

- **WHEN** scanner, budget or SBOM preparation fails
- **THEN** expensive proof does not start and the native failure remains observable
- **AND** old proof, test and coverage reports cannot describe the new attempt
- **AND** the hosted receipt identifies failed supply without issuing an Attestation

#### Scenario: Prepared supply permits exact-source verification

- **WHEN** every required preparation succeeds
- **THEN** verification executes against the requested exact source
- **AND** a retained adopter runtime selector cannot redirect source CI to older code
- **AND** the later package boundary retains its own executable validation

#### Scenario: Linux runner reuses locked immutable supply

- **WHEN** a new GitLab checkout begins on a cold ARM64 runner
- **THEN** its image is selected by published OCI digest, not a mutable tag or local cache hit
- **AND** the image's input hashes match the checkout's Python and Node locks before provisioning or proof
- **AND** APT, PyPI and npm registry access are not required by the quality job
- **AND** missing or mismatched supply fails before any quality result is issued

#### Scenario: One selected Forge remains executable without its peer

- **GIVEN** two selected Forges project the same exact source and required CI graph
- **WHEN** one Forge's registry and release endpoints are unavailable and the other's runner has no local image or tool cache
- **THEN** the available Forge executes every required job from its own verified supply or independent sources
- **AND** the selected source, supply materials and resulting evidence remain bound to that Forge's run
- **AND** missing bytes or a peer-dependent fetch blocks before proof rather than accepting a warm-cache or other-Forge result

#### Scenario: Unqualified image is not published

- **WHEN** a newly built image cannot bootstrap a fresh checkout without network access
- **THEN** the build job fails before pushing that image
- **AND** the previously published digest remains available for diagnosis or rollback

#### Scenario: Native provisioning exceeds its execution deadline

- **WHEN** a native tool emits partial output before its bounded preparation times out
- **THEN** the supply entrypoint reports both available streams and the exact failed command
- **AND** owned descendants terminate before preparation scratch is removed
- **AND** a preceding successful tool cannot be mistaken for the failed attempt

### Requirement: Native read batching preserves official semantics

ETHOS SHALL execute each bounded read batch through the selected official
OpenSpec package without copying its command parser or caching mutable results.
Every result SHALL bind its ordered input, native exit status and output.
Incomplete transport SHALL preserve failure evidence without claiming execution.

#### Scenario: A read requires current executable verification

- **WHEN** the existing batch owner resolves the locked official tool for a read
- **THEN** the same native process verifies the imported official program version before parsing commands
- **AND** metadata drift, missing tools and version mismatch refuse the read without a second parser or cached verdict
- **AND** archived or preobserved intent that executes no read retains standalone executable verification
- **AND** later observations read current inputs again and each effect retains fresh admission

#### Scenario: An official command exits before the batch ends

- **WHEN** the native program exits during one read
- **THEN** completed frames preserve their native output and exit status
- **AND** unexecuted commands return an explicit interrupted result
- **AND** no effect command is admitted to the read batch

#### Scenario: A bounded output frame encounters pipe backpressure

- **WHEN** official output exceeds the receiving pipe's available capacity
- **THEN** the transport preserves every byte and input order as the reader drains
- **AND** retry remains bounded by the existing command deadline
- **AND** a stalled or closed reader fails without replaying a partially written frame
- **AND** native early exit still preserves completed output and marks the remaining tail

#### Scenario: Intent changes between public observations

- **WHEN** a later public plan observes changed OpenSpec inputs
- **THEN** it invokes the current official reader again
- **AND** an earlier successful observation cannot hide invalid current intent

### Requirement: Observation reuse preserves freshness and result identity

ETHOS SHALL reduce redundant computation using exact inputs and explicit
observation boundaries. Reuse SHALL preserve corruption detection and fresh
effect admission. Clearing derived caches SHALL change computation cost only,
not the verdict or selected effect.

#### Scenario: Relevant input changes

- **WHEN** source, rules, runtime, trust or coordinated state relevant to a
  decision changes
- **THEN** a prior cached result grants no current authorization
- **AND** only still-applicable immutable computation may be reused

#### Scenario: Complete source identity

- **WHEN** source includes staged, unstaged, untracked, deleted or executable-mode
  changes, including paths with index optimization flags
- **THEN** optimized observation preserves the native effective tree
- **AND** the caller's index and unrelated resources remain unchanged

### Requirement: Repository proof reuse preserves accepted meaning

Repository transitions SHALL independently validate each proof's source,
acceptance, policy, execution binding, integrity and applicability. Equivalent
accepted meaning may have distinct authoring and repository execution facts.
A prepared transition SHALL retain its carried proof identity and require that
exact proof to remain admitted; adding equivalent evidence SHALL NOT rewrite the
request or require repeating execution.

#### Scenario: Accepted authoring lane has retired

- **WHEN** an exact accepted source has a valid proof from a retired authoring lane
- **THEN** release preview and native ref admission use repository-transition proof semantics
- **AND** creating new authoring effects still requires current lane coordination

#### Scenario: A prepared release gains equivalent evidence

- **WHEN** another valid proof is recorded for the same accepted source and meaning
- **THEN** the original request and signed tag bytes remain reusable after fresh admission
- **AND** withdrawal, corruption, expiry or conflicting selected meaning still blocks

#### Scenario: Git reports failure around a ref effect

- **WHEN** the native ref process exits unsuccessfully
- **THEN** its command, working directory, output, exit code and plan/effect identities remain observable
- **AND** only a successful ref readback may classify the result as unchanged
- **AND** uncertain completion retains recovery intent without blind effect replay

### Requirement: Interrupted commands retain effect and process ownership boundaries

A synchronous command interrupted while its caller remains alive SHALL stop its
owned descendants before reporting completed cleanup. The original failure and
available output SHALL remain observable. Process-group control SHALL identify
its platform and containment limits; it SHALL NOT imply recovery after loss of
the supervisor or containment of deliberately detached processes.

#### Scenario: POSIX command timeout or caller cancellation

- **WHEN** a running command has a ready descendant in its owned process group
- **AND** its caller observes a timeout or cancellation
- **THEN** the group is terminated without signalling the caller's group
- **AND** inherited output pipes do not leave the descendant running
- **AND** the original exception and captured timeout output remain available

#### Scenario: Native executable verification times out

- **WHEN** a version-check executable has a ready descendant and exceeds its deadline
- **THEN** the shared process owner closes its process group before returning failure
- **AND** the verified archive and previous executable retain their existing protections
- **AND** transport and verification do not define competing cancellation semantics

#### Scenario: A parallel proof caller is interrupted

- **WHEN** the proof caller is interrupted while worker threads own native commands
- **THEN** the shared process owner cancels those groups before the executor joins its workers
- **AND** late command creation is denied within the cancelled invocation
- **AND** the original interruption remains observable without a passing proof claim
- **AND** an independent subsequent invocation has fresh command ownership

#### Scenario: A test supervisor is killed

- **WHEN** a worker exits without executing its cleanup
- **THEN** a passing direct-command timeout test does not prove worker recovery
- **AND** native supervisor-loss and platform acceptance remain required

### Requirement: Runtime verification failure preserves generation ownership

A newly created runtime generation SHALL remain unaccepted until its required
verification succeeds. If verification fails or the caller is interrupted,
its creator SHALL remove that owned generation and propagate the failure,
without deleting or changing a previously accepted generation.

#### Scenario: Verification times out after the staging rename

- **WHEN** verification of a newly exposed generation times out or is interrupted
- **THEN** the failed generation and owned staging are removed
- **AND** the original failure propagates without claiming successful activation
- **AND** the previously accepted generation retains its exact bytes

### Requirement: Native metadata comparisons preserve observation semantics

ETHOS SHALL compare mutable file metadata before and after reading through the
same native observation channel. Path and open-handle observations SHALL refer
to the same file identity, without equating platform-specific timestamp meanings.
Unsafe kinds and replaced files SHALL remain rejected without leaking handles.

#### Scenario: Stable Windows path and handle timestamps differ

- **WHEN** path stat and descriptor stat expose different stable ctime meanings
- **THEN** unchanged native merge metadata remains readable
- **AND** changes within either channel or replacement of the named file are rejected
- **AND** read-induced access-time changes do not masquerade as content mutation

### Requirement: Verified supply survives later activation failure

The native supply owner SHALL retain an archive only after its declared digest
and executable member are verified. Later executable-version failure SHALL
preserve that verified download while leaving the previous executable unchanged.
Every reuse SHALL revalidate the archive; retained bytes do not grant acceptance.

#### Scenario: A downloaded executable fails its version check

- **WHEN** archive verification succeeds and executable verification fails or times out
- **THEN** exactly the verified archive remains available for a later attempt
- **AND** the old executable is unchanged and temporary preparation is removed
- **AND** retrying failed executable verification does not redownload the archive

#### Scenario: Archive content is invalid

- **WHEN** its digest, member identity or member type is invalid
- **THEN** the download is not retained as verified supply
- **AND** cached corruption remains rejected before executable activation

#### Scenario: A disposable checkout is replaced

- **WHEN** a runner selects its declared project-scoped persistent tool cache
- **THEN** replacement checkouts reuse matching verified supply without another download
- **AND** concurrent preparation shares the existing lock and exact archive validation
- **AND** corruption, unsafe paths and executable damage retain their normal admission checks
- **AND** native bootstrap cache selection preserves the required version and host platform

### Requirement: Owned removal minimizes permission effects

Runtime and test-output cleanup SHALL share one filesystem removal owner for
quiescent, exclusively owned paths. It SHALL prepare each real directory once
and modify only permissions required for deletion. External referents SHALL
retain bytes, permissions and modification time; caller-specific admission and
native failure reporting SHALL remain effective.

#### Scenario: Writable or sealed owned directories are removed

- **WHEN** an admitted tree contains writable or owner-inaccessible directories
- **THEN** cleanup removes the tree and changes only missing directory permissions
- **AND** POSIX regular-file modes are unchanged before unlinking
- **AND** repeated cleanup of the absent path succeeds

#### Scenario: Links or deletion failures occur

- **WHEN** an owned output contains a symbolic link or shares a regular-file inode
- **THEN** generic cleanup preserves external referents and runtime admission retains its stronger rejection
- **AND** a native deletion failure remains observable under the caller's declared policy

### Requirement: Package validation output has bounded custody

Install-smoke archives SHALL be owned by that invocation, not retained as
release assets. Successful or failed validation SHALL remove their bytes.
Evidence SHALL retain the verified digest without claiming a surviving path;
publication retains a separate explicit artifact owner.

#### Scenario: Repeated validation across source revisions

- **WHEN** install smoke packages a runtime and checks shared supply
- **THEN** the archive exists while consumed and is removed before evidence is written
- **AND** a failed supply check also removes it without producing passing evidence
- **AND** repeated revisions do not accumulate native validation archives

### Requirement: Archive preserves relative reference meaning

Archive projection SHALL resolve supported local Markdown destinations against
the exact source document and derive their archived or canonical locations.
Only destination bytes and declared source bindings may change. Recognition
SHALL reject missing or escaping targets, arbitrary edits and unsupported
reference semantics rather than certify unchanged bytes as unchanged meaning.

#### Scenario: Documents and delta requirements move

- **WHEN** official archive moves documents with repository and Change-local references
- **THEN** links, images and definitions retain their intended targets
- **AND** untouched text, code, titles and line endings remain identical
- **AND** canonical deltas use the locked official builder and derived source bindings

#### Scenario: Exact postimage or completion fails

- **WHEN** a referenced target disappears or a postimage contains unauthorized edits
- **THEN** recognition rejects that postimage before acceptance
- **AND** native effect failure preserves the existing compensation boundary
- **AND** repeated completed recognition performs no duplicate effect

### Requirement: Governed local links resolve to deliverable targets

The maintained-document link check SHALL distinguish a target present on the
host from a target delivered with the selected Git tree or an explicitly
declared published artifact. The native link parser owns syntax; the repository
observation owner supplies exact membership. An ignored or untracked local file
SHALL NOT make a tracked document's broken delivered link pass.

#### Scenario: Host-only target cannot validate a tracked document

- **WHEN** a tracked Markdown link resolves locally only to ignored or untracked bytes
- **THEN** the public check reports the target as unavailable to the declared delivery
- **AND** the same link passes when its target is tracked or has a verified published-artifact contract

#### Scenario: Local link safety is preserved

- **WHEN** a target is missing, escaping, linked outside the repository or changes during observation
- **THEN** the check retains a precise failure or UNKNOWN rather than treating host existence as delivery
- **AND** a valid in-tree target remains admissible without a second Markdown parser

### Requirement: Archive proof scope retains validated effect paths

A nonempty repository proof scope SHALL retain validated archive effect paths
that disappear from its net baseline diff. Source deletions SHALL remain
attributed independently of Git rename detection. Empty scope SHALL NOT select
unrelated historical archive authority.

#### Scenario: A Change creates and archives a document

- **WHEN** a source document is created and removed within the integrated range
- **THEN** postarchive proof still includes its validated effect obligation
- **AND** incomplete proof coverage remains rejected

### Requirement: Stable supply preserves the supported dependency closure

Supply updates SHALL select verified stable versions through their existing
owners and preserve the supported Python line. Native locks, package contents,
CI templates and generated projections SHALL agree. An incompatible upstream
release SHALL remain an explicit unresolved constraint, not an ignored dependency
or a false latest-version claim.

#### Scenario: Latest upstream conflicts with a required dependency

- **WHEN** the native resolver rejects a stable upstream version
- **THEN** the compatible closure remains selected and the exact conflict is reported
- **AND** other independently compatible updates continue through their normal acceptance

### Requirement: Quality capabilities initialize only when selected

Quality session discovery SHALL preserve its declared interface without loading
or validating unrelated capabilities. Each selected consumer SHALL resolve its
required tools and source-bound supply through the existing owners. A later
operation SHALL revalidate changed inputs; an already selected operation retains
its explicit input binding.

#### Scenario: An unrelated Node supply is unavailable

- **WHEN** native session listing or Python lint runs without prepared Node supply
- **THEN** the operation succeeds without resolving that unrelated capability
- **AND** a selected Markdown check rejects missing required supply

#### Scenario: Supply changes after one operation is selected

- **WHEN** a delivery operation binds valid supply and the configuration or lock later changes
- **THEN** subsequent selection rejects missing or mismatched supply
- **AND** the earlier operation retains its original explicit binding
- **AND** no prior successful validation authorizes the later operation

### Requirement: Hosted verification has one execution owner

A hosted attempt SHALL cover the declared quality dependency graph through its
shared execution owner. Native job partitions SHALL preserve every required
obligation, dependency and source binding. Compatible evidence MAY be reused
without repeating checks; aggregate-only forwarding SHALL NOT substitute for
actual execution or required artifact validation.

#### Scenario: A nonexecuted provider envelope adds no hosted assurance

- **WHEN** CI has not explicitly requested a post-run provider observation
- **THEN** it does not launch a dry-run session before the real quality graph
- **AND** later provider status remains a separate, fresh observation

### Requirement: One test attempt provides reconstructable reports

The Python test owner SHALL emit JUnit, coverage and Allure results from one
execution. Allure 3 SHALL derive human and Agent views from those results without
rerunning tests. Missing, stale or incomplete required reports SHALL fail the
relevant test or hosted acceptance; rendering never changes a test verdict.

#### Scenario: A failed test still has a diagnostic report

- **WHEN** pytest records passing, failing and skipped cases in one attempt
- **THEN** Allure 3 can rebuild a human report and Agent query from the retained results
- **AND** the original pytest failure remains a failure

#### Scenario: Stale results cannot describe a new attempt

- **WHEN** a new test attempt begins or its source binding changes
- **THEN** old results and rendered views are invalidated
- **AND** missing or count-mismatched results cannot satisfy report admission

#### Scenario: Opaque parameters do not invent retries

- **WHEN** distinct pytest cases carry binary parameters with the same display representation
- **THEN** Allure retains their distinct logical test identities
- **AND** it does not present those cases as retries of one test

#### Scenario: GitHub execution is independent of workstation runners

- **WHEN** GitHub executes the selected quality workflow
- **THEN** its jobs select GitHub-hosted runners without workstation labels or inherited-hook overrides
- **AND** local emulation derives its platform mapping from the selected workflow job
- **AND** ephemeral hosted tool storage is not presented as cross-job persistence
- **AND** GitLab uses a separate digest-bound image, not an assumed runner-local cache

#### Scenario: Complete partitioned execution succeeds

- **WHEN** every required partition executes successfully against the selected source and policy
- **THEN** final admission requires their complete, nonduplicated result union and artifact validation
- **AND** the published wheel and SBOM bytes originate from that verified execution
- **AND** platform conformance and provider-only obligations retain their distinct execution

#### Scenario: External availability cannot starve repository proof

- **WHEN** an upstream link returns an adverse HTTP response other than temporary unavailability
- **THEN** the external-health observation remains nonpassing and retains its exact report
- **AND** the required repository proof and its JUnit, coverage, wheel and SBOM artifacts execute independently
- **AND** a failing upstream site is not presented as a valid link or a repository proof failure

#### Scenario: Temporary upstream unavailability is not a broken link

- **WHEN** an upstream link answers 503 Service Unavailable
- **THEN** the external-health observation accepts it as temporary unavailability
- **AND** a rate-limited or timed-out request is retried rather than accepted

#### Scenario: A link-checker diagnostic fails the link observation

- **WHEN** Lychee exits zero but writes a diagnostic to stderr, such as its hint that it followed a redirect
- **THEN** the link observation fails and retains the diagnostic
- **AND** the document links to the resolved target of the redirect instead

#### Scenario: Offline supply does not disable online assurance

- **WHEN** a hosted image prepares locked tool dependencies from its digest-bound cache
- **THEN** bootstrap performs no external fetch and leaves no job-wide offline flag
- **AND** network-required vulnerability checks may query their declared upstream and fail closed if unavailable

#### Scenario: A required result cannot establish success

- **WHEN** a result or required upload fails, is cancelled, skipped, missing, malformed or UNKNOWN
- **THEN** final admission cannot report success
- **AND** native diagnostics and available reports remain inspectable
- **AND** unchanged failure is not retried or hidden by a longer deadline

#### Scenario: Exact HEAD does not describe the executing source

- **WHEN** required source is missing from the selected commit or the worktree, index or policy drifts
- **THEN** exact-commit qualification is refused before execution or at the post-execution fence
- **AND** an exploratory working-tree observation cannot satisfy an exact-commit obligation

#### Scenario: A native tool reports an adverse diagnostic with exit zero

- **WHEN** native structured output contains a warning or error despite a zero exit
- **THEN** its owning adapter refuses success and retains the diagnostic
- **AND** informational output alone is not classified as a warning
- **AND** shell formatting and shell semantics are both checked by their declared native tools

#### Scenario: A proof check claims success with contradictory execution evidence

- **WHEN** a passing check carries a nonzero exit, warning, adverse diagnostic or required gap
- **THEN** shared execution admission refuses success before proof artifact creation
- **AND** normalization cannot erase the adverse signal to produce an admissible proof
- **AND** dependency scheduling and later proof validation use the same success predicate

#### Scenario: Unprivileged hosted link checking

- **WHEN** a prepared hosted checkout runs its full graph without system write access
- **THEN** link checking uses the declared locked binary wheel in that environment
- **AND** no separate installer writes host executable directories
- **AND** valid local links pass and missing targets produce a failing observation

#### Scenario: Specification validation has no ambient executable

- **WHEN** a prepared checkout has locked OpenSpec supply but no OpenSpec command on PATH
- **THEN** the gate invokes the existing verified official command resolver
- **AND** governance and gate consumers apply the same native result interpretation
- **AND** empty or informational valid results pass while invalid items, failed execution and unreadable output block
- **AND** missing official supply blocks without substituting another executable

### Requirement: Declared native outputs bind one gate attempt

A gate MAY declare `native_outputs` naming each report its native command writes, with its
producing session and a format: `junit-xml`, `cobertura-xml`, `lcov`, `sarif`, or an optional
Python producer report (`nox-json`, `pytest-jsonl`, `python-runtime-json`). ETHOS SHALL capture
them from one owned attempt for the gate's verification providers. Missing, duplicate, malformed or
session-inconsistent outputs SHALL NOT satisfy the gate.

#### Scenario: An adopter profile declares native reports

- **WHEN** a profile or gate registry declares valid native outputs for a gate
- **THEN** the declaration validates against the published gate schema
- **AND** the verification provider receives the reports of that exact attempt

#### Scenario: A declared report is absent or inconsistent

- **WHEN** a declared report is missing, duplicated, malformed or bound to another session
- **THEN** the gate cannot pass and reports the exact native output gap

#### Scenario: A gate declares no Nox report

- **WHEN** a gate declares JUnit, coverage and SARIF outputs without a Nox report
- **THEN** the declaration validates and its reports are judged from that attempt alone

#### Scenario: A gate declares a Nox report

- **WHEN** a gate declares one Nox report
- **THEN** its command writes that report to the declared path
- **AND** every declared output names a session of that report, and each such session succeeded

#### Scenario: A removed format is declared

- **WHEN** a declaration names `coverage-xml` or `ruff-json`
- **THEN** validation refuses it before any execution

### Requirement: A native attempt supplies its own observer

A native attempt that declares a Python runtime report SHALL give its command the
invoking immutable runtime's exact wheel as one hashed direct reference in
`ETHOS_NATIVE_OBSERVER_REQUIREMENT`, and SHALL remove any inherited value. The
installed observer SHALL run one exact Ruff argv from the session child and record
that child's interpreter with the launch.

#### Scenario: An installed runtime runs a native gate

- **WHEN** an installed runtime starts an attempt that declares a Python runtime report
- **THEN** the command receives `ethos @ <wheel file URI>#sha256=<digest>` for that runtime's wheel
- **AND** the retained attempt receipt names the supplied requirement

#### Scenario: The session child observes its own Ruff launch

- **WHEN** a session child runs `python -m ethos.domain.quality.nox run` with a Ruff argv after `--`
- **THEN** the operation returns Ruff's exit code and records that interpreter with the single launch
- **AND** the Nox parent environment needs no ETHOS installation

#### Scenario: No exact wheel is available

- **WHEN** the invoking package is a source checkout
- **THEN** the attempt supplies no requirement
- **AND** a selected runtime whose package wheel is absent or changed refuses before launch

### Requirement: Configuration selection preserves requested coverage

Configuration checks SHALL discover candidate files through native Git and
resolve their validation responsibility through the existing ownership compiler.
Explicit absent or differently owned targets SHALL NOT become empty success.
Default diagnostics MAY omit files deleted from the current candidate; exact
committed execution SHALL retain its independent source-correspondence check.

#### Scenario: A new configuration is outside the former filename list

- **WHEN** tracked or nonignored candidate configuration contains a native failure
- **THEN** default selection checks it and preserves the native failure
- **AND** ignored files and official external carriers remain with their owners

#### Scenario: The caller requests an absent or differently owned file

- **WHEN** an explicit target is missing, deleted or delegated to another owner
- **THEN** selection fails with the target and applicable owner guidance
- **AND** valid relative and absolute targets receive the same validation

### Requirement: Native tool supply has one declaration and bounded bootstrap

Development and CI SHALL consume the same mise tool selections and platform
locks. Ecosystem dependency locks SHALL remain with their package managers.
Observation SHALL NOT install tools. Provisioning SHALL preserve current
executables on failure, retain native diagnostics, and remove owned scratch.

#### Scenario: A clean runner has no mise installation

- **WHEN** the existing bootstrap executes with no prepared native mise
- **THEN** the version-bound official installer runs in owned staged storage with a deadline
- **AND** only a successfully verified executable is published
- **AND** preparation of locked gate tools completes before gate execution
- **AND** every same-invocation consumer uses that exact prepared executable without rediscovering PATH or an obsolete cache directory

#### Scenario: Operator-managed mise is newer than the declared minimum

- **WHEN** an existing stable operator executable meets the native minimum version
- **THEN** preparation reuses it without installing or replacing another executable
- **AND** staged bootstrap supply still requires its exact declared version
- **AND** older, prerelease, malformed or warning-bearing observations cannot pass

#### Scenario: Native Windows observation inherits another PowerShell's modules

- **WHEN** ACL or process observation starts native Windows PowerShell through an intermediate process
- **THEN** its child environment excludes the inherited module search path
- **AND** the parent environment, native error and timeout boundaries remain intact

#### Scenario: Native preparation fails or is interrupted

- **WHEN** download, archive validation, executable validation or execution times out or fails
- **THEN** the previous executable remains unchanged and owned descendants are drained
- **AND** unapproved version diagnostics prevent publication
- **AND** verified cache reuse preserves identity without repeating downloads

### Requirement: Native adoption preserves declared byte identity

Adoption SHALL bind its write plan to exact UTF-8 bytes independently of host
newline translation. Retained authored bindings SHALL preserve their original
bytes and matching digest. New writes and compensation SHALL share the existing
atomic writer, without claiming multi-file crash atomicity.

#### Scenario: Native text mode would translate line endings

- **WHEN** an admitted adoption writes new bindings on a platform with CRLF text mode
- **THEN** actual file digests equal the declared write-plan digests
- **AND** CLI, SDK and MCP retain the same exact-byte acceptance

#### Scenario: Authored bindings use a different newline convention

- **WHEN** valid existing bindings contain LF, CRLF or CR bytes
- **THEN** adoption keeps those bytes and reports their exact digests
- **AND** a later binding-write failure restores any earlier empty binding or removes its new file

### Requirement: Native compilers preserve exact policy and projection inputs

CUE compilation SHALL consume the declared exact input closure and independently
compare generated outputs. CEL predicate declarations SHALL compile to Boolean
expressions. Candidate-supplied observations SHALL NOT certify candidate output.

#### Scenario: An interpreter loads a module rather than another executable

- **WHEN** a declared command invokes a Python module, directly or through a native wrapper
- **THEN** observation retains the interpreter executable and the module's import dependency separately
- **AND** an undeclared import is rejected without an executable-name exception
- **AND** module-like arguments after a script, code or terminating option do not invent imports

#### Scenario: Candidate projection bytes agree with a forged local copy

- **WHEN** both copies disagree with the CUE source or candidate code supplies its own observation
- **THEN** the independent output comparison rejects the discrepancy
- **AND** staged admission uses index inputs rather than unrelated worktree bytes

#### Scenario: An expression cannot serve as a predicate

- **WHEN** a CEL declaration is invalid, unbound or not statically Boolean
- **THEN** declaration loading rejects it before runtime policy evaluation
- **AND** valid declared predicates retain their existing runtime semantics

#### Scenario: The bootstrap projection is edited independently

- **WHEN** installer bytes differ from the selected native generator output
- **THEN** the existing projection gate rejects the drift
- **AND** the documented lexical normalization and native shell formatting remain deterministic

### Requirement: Provider execution preserves the bound implementation

A proof binding repository provider source SHALL execute that source or a package
with the same source commit and tree. A mismatched invoking package SHALL be
rejected before any gate executes. Package-supplied adopter checks without
repository implementation bindings remain valid.

#### Scenario: Old runtime would mix with candidate toolchain

- **WHEN** a graph binds candidate provider source but the loaded package is older
- **THEN** execution reports the provider/source mismatch before external checks start
- **AND** no Attestation or passing host observation is produced
- **AND** recovery selects the admitted checkout's locked execution environment

#### Scenario: Matching execution and ordinary adoption

- **WHEN** providers execute from the candidate checkout or its matching package
- **THEN** ordinary gate execution remains available
- **AND** packaged-only adopter providers do not inherit a source-checkout requirement
- **AND** current effect admission and trusted-prior control replacement remain separate

#### Scenario: A reused CI checkout retains an older installed runtime

- **WHEN** a Forge job validates the checked-out source's integration range
- **THEN** its declared Python module executes the source implementation directly
- **AND** the installed product dispatcher still honors ordinary adopter runtime selection

#### Scenario: A pull request offers a synthetic merge object

- **WHEN** GitHub supplies a synthetic merge SHA for a pull-request run
- **THEN** source checkout, host conformance and proof execute the authored PR head
- **AND** the commit-range check validates that head against the PR base
- **AND** push and manual-dispatch runs continue to execute their triggering commit
- **AND** review and integration admission remain separate from this source check

### Requirement: Canonical decoding reuse preserves fresh observation

Attestation decoding reuse SHALL be keyed by exact bytes and bounded by total
retained input bytes. Large valid members SHALL remain reusable within that
budget. Oversized or evicted members SHALL still validate. Current membership,
source, Lease and effect authorization SHALL NOT be cached as permission.

#### Scenario: Warm and evicted reads select the same meaning

- **WHEN** the same valid bytes are read cold, warm or after eviction
- **THEN** the reader returns the same validated meaning without repeated warm decoding
- **AND** changed or deleted refs remain observable on every read
- **AND** corrupt replacement bytes cannot inherit an earlier valid member identity

### Requirement: JavaScript behavior is executed rather than merely declared

The full gate graph SHALL execute package-owned JavaScript behavior separately
from formatting. The locked toolchain SHALL bind Node and npm to one supply;
owned disposable state SHALL be reclaimed on success and failure. Formatting
metadata SHALL reference the executable owner, not imply execution by listing it.

#### Scenario: Formatted JavaScript has failing behavior

- **WHEN** the package test command exits unsuccessfully
- **THEN** the required behavior gate fails and preserves its native diagnostic
- **AND** formatting success cannot substitute for that result

#### Scenario: Native package checks run without host npm

- **WHEN** the JavaScript behavior gate runs with the locked toolchain
- **THEN** nested package checks use the same npm CLI and Node executable
- **AND** success and failure both remove owned temporary npm state

#### Scenario: Independent package behavior starts with other heavy checks

- **WHEN** JavaScript behavior and Python or package checks use disjoint owned outputs
- **THEN** the gate scheduler may execute them concurrently after their real prerequisites pass
- **AND** a writer that claims the shared supply still excludes the JavaScript behavior gate

### Requirement: Native quality evidence is judged by property

A verification provider SHALL judge declared native reports by property, not producer. Behavior
passes only when every JUnit report has a test case and no failure or error, and each applicable
file a Cobertura or LCOV report measures was executed. Static analysis passes only when SARIF has
no warning or error and its inventory lists each file it covers. A provider SHALL claim only the
files its evidence covers.

#### Scenario: Tests pass and the measured files ran

- **WHEN** every JUnit report passes and coverage shows each measured applicable file executed
- **THEN** behavior passes and claims exactly those files

#### Scenario: A measured file never ran

- **WHEN** coverage measures an applicable file with executable lines and none of them ran
- **THEN** behavior blocks for that file

#### Scenario: A test failed or none ran

- **WHEN** a JUnit report has a failure or error, or contains no test case
- **THEN** behavior blocks

#### Scenario: SARIF reports a finding

- **WHEN** a SARIF result is a warning or an error
- **THEN** static analysis blocks with that result
- **AND** a note alone does not block

#### Scenario: SARIF scope is unknown

- **WHEN** a SARIF run does not list its analyzed artifacts and no declared same-session Python
  runtime recorded the files its checker read
- **THEN** static analysis blocks because its scope is unknown

#### Scenario: Evidence covers some applicable files

- **WHEN** a native report covers only some applicable files
- **THEN** the provider claims only those files
- **AND** the quality obligation stays unproven until other admitted evidence covers the rest

#### Scenario: A gate declares no native outputs

- **WHEN** a quality verifier runs for a gate without native outputs
- **THEN** ETHOS runs its own check for each language it supports
- **AND** files in other languages stay unclaimed instead of blocking that gate
- **AND** a gate whose applicable files are all in such languages blocks

### Requirement: Native supply resolution leaves no host mise state

Resolving native tool supply SHALL run mise in safe mode over a disposable directory and SHALL keep mise's state in that directory. Resolution thus runs no repository task, hook or template and records nothing in the host's mise state. Provisioning into a disposable root SHALL keep mise's state in that root.

#### Scenario: A resolution completes

- **WHEN** ETHOS resolves a repository's declared version files, a locked tool or a locked environment
- **THEN** the host's mise state is unchanged and no repository task ran
- **AND** the resolved executables are those of the locked selection

### Requirement: Locked execution keeps native mise policy

The environment that ETHOS gives an admitted repository command SHALL expose the locked tools with configuration isolation, locked and offline selection, no automatic installation and no prompts. It SHALL NOT carry resolution's safe mode, disposable state or trust, and a caller's explicit safe mode and state directory SHALL apply. Trust SHALL remain mise's decision: ETHOS SHALL NOT trust a configuration, edit a trust record or override a native refusal.

#### Scenario: An admitted command runs repository tasks

- **WHEN** an admitted command runs a repository task that runs another task through native mise
- **THEN** both tasks run with the locked tools

#### Scenario: The caller selected safe mode

- **WHEN** the caller's environment selects mise's safe mode
- **THEN** native mise still refuses to run repository tasks

#### Scenario: An untrusted configuration needs trust

- **WHEN** an admitted command reads an untrusted repository configuration that needs trust through a mise command that does not trust it
- **THEN** nothing in that configuration runs and ETHOS records no trust for it

#### Scenario: An admitted command runs a host command

- **WHEN** an admitted command runs a host command such as `git` or `tar`
- **THEN** its PATH holds the locked tools ahead of the host's own command baseline, and nothing else from the caller's PATH
- **AND** on Windows that baseline holds the system command directories and the shell-free Git launcher, but no shell and not the current directory

### Requirement: Disposable mise copies carry only native trust

Resolution and provisioning SHALL carry to their disposable copy of the exact declared bytes only the trust that native mise, under the caller's own trust inputs, already reports for the repository's configuration, and only for that invocation. They SHALL write no trust record and SHALL NOT trust a configuration that native mise does not report as trusted. A resolution refused for an untrusted configuration SHALL name native `mise trust` as the next action.

#### Scenario: A trusted configuration locks a trust-keyed install

- **WHEN** native mise reports the repository's configuration as trusted, and it locks a tool whose installed copy is keyed by trust-only lock metadata such as an aube entry
- **THEN** resolution selects that installed copy
- **AND** no repository code runs and no trust record is written

#### Scenario: A trusted configuration provisions a locked tool

- **WHEN** native mise reports the repository's configuration as trusted, and ETHOS provisions a locked tool whose archive is not cached
- **THEN** the one native install in the disposable copy reads that copy's lock
- **AND** no trust record is written

#### Scenario: An untrusted configuration

- **WHEN** native mise does not report the repository's configuration as trusted
- **THEN** resolution carries no trust to its copy and its result is unchanged
- **AND** a refusal names `mise trust` as the next action

### Requirement: Offline fixture builds need no unlocked build supply

Tracked Python fixture projects that offline quality tests build SHALL use uv's bundled build backend, through a requirement that the running uv satisfies, so a build needs nothing beyond the locked fixture supply. When that supply is complete, the state of uv's shared cache SHALL NOT change their verdict.

#### Scenario: The shared index lists an uncached build release

- **WHEN** another uv command has refreshed the shared index after a build dependency published a release, and offline tests build a fixture project
- **THEN** the build uses uv's bundled backend and downloads nothing

#### Scenario: The cache is empty

- **WHEN** a tracked fixture project is built offline from an empty uv cache
- **THEN** the build succeeds

### Requirement: Isolated Python static analysis judges the declared target

The product's Python static provider SHALL keep its isolated common rules,
which repository ignores cannot narrow, and SHALL judge authored Python at the
repository's declared version: its accepted Ruff `target-version`, following
`extend` inside the repository, otherwise the `requires-python` lower bound. A
missing, malformed or conflicting declaration, or a nested one giving checked
code another target, SHALL be a gap; neither the checker default nor ETHOS's
interpreter decides it.

#### Scenario: No target is declared

- **GIVEN** a repository's accepted Ruff configuration declares no
  `target-version` and its `pyproject.toml` declares no `requires-python` lower
  bound
- **WHEN** the isolated static check runs
- **THEN** it reports `python_target_undeclared` before running Ruff
- **AND** no file is judged at the checker's default target.

### Requirement: The per-test bound detects hangs

The Python test gate SHALL bound each test by one declared hang limit, set well above the slowest healthy test's duration inside a full proof at the admitted host load. A test MAY declare a shorter limit to time one specific operation. No test SHALL declare a limit at or above the declared one.

#### Scenario: A heavy test runs inside a busy full proof

- **WHEN** a test that takes 51 s alone takes 123 s inside a full proof at the admitted host load
- **THEN** its own assertions decide its result, not the hang limit

#### Scenario: A test stops making progress

- **WHEN** a test makes no progress
- **THEN** it fails at the declared limit and reports its stack

#### Scenario: A test raises its own limit

- **WHEN** a test declares a limit at or above the declared one, or a limit that is not a literal
- **THEN** the architecture regression fails

### Requirement: Hosted check names are stable identities

Each job that a hosted CI projection generates SHALL take its name from its matrix coordinates and fixed text alone. A supply or tool version change SHALL NOT rename a job, so the required checks that a forge declares keep naming the jobs that report them.

#### Scenario: A locked runtime version changes

- **WHEN** the locked Node version changes
- **THEN** every projected job keeps its name

#### Scenario: A matrix job is projected

- **WHEN** a job runs over the `os` and `python` axes
- **THEN** its name is formed from those two axes and fixed text, such as `ubuntu-latest / Python 3.12`

### Requirement: The reference-transaction launcher starts the runtime only for prepared states

The generated reference-transaction launcher SHALL exit successfully for any transaction state other than prepared before it reads the runtime selection. A launcher template without that guard SHALL stay valid, so a launcher generated by an earlier runtime keeps working with that runtime until its repository reinstalls hooks.

#### Scenario: A ref update starts the runtime once

- **WHEN** `git update-ref` moves a branch in a repository with generated hooks
- **THEN** the reference-transaction launcher starts the runtime only for the prepared state

#### Scenario: A commit starts the runtime only for prepared states

- **WHEN** `git commit` advances a branch
- **THEN** the reference-transaction launcher starts the runtime only for that commit's prepared transactions

#### Scenario: A terminal state leaves no trace

- **WHEN** the hook protocol receives a governed update in the preparing, committed or aborted state
- **THEN** it exits successfully and ETHOS state, journals and attestations are unchanged

#### Scenario: The guard runs through Git's shell

- **WHEN** Git runs the generated launcher for a state other than prepared on any supported platform
- **THEN** the launcher exits successfully before it reads the runtime selection

#### Scenario: An earlier runtime's template is read

- **WHEN** status reads the hook declaration of a selected runtime whose template has no guard
- **THEN** its launchers render as before and status reports no launcher drift
