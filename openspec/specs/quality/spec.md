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

### Requirement: Terminal projection export preserves complete source meaning

The terminal exporter SHALL bind one exact commit and tree, retain semantic
attributes and graph contracts, and reject stale source bindings. The product
contract remains the sole product meaning owner. The target design SHALL be
identified as a target rather than an implementation claim.

#### Scenario: Whole-product meaning survives export

- **WHEN** the current terminal architecture is exported
- **THEN** interpretation, formation and adoption, capability contracts,
  collaboration outcomes, bounded verification and integration, actual-use
  feedback, recovery and exit remain represented with source provenance
- **AND** Commitment remains transient and accepted intent remains OpenSpec-owned

#### Scenario: Native source drift is not hidden by fixtures

- **WHEN** any selected source changes without semantic reconciliation
- **THEN** the actual-source export regression rejects the digest mismatch
- **AND** isolated synthetic fixture success cannot substitute for that result

### Requirement: Required visual assertions have readable static witnesses

Every required node and relation SHALL select a main-static copy witness or a
meaning-preserving aggregate. Export SHALL reject missing and hidden-only
witnesses. Renderer acceptance SHALL measure actual painted glyphs, transforms,
strokes and arrowheads; metadata or hover alone SHALL NOT satisfy coverage.

#### Scenario: Hidden witness cannot satisfy required meaning

- **WHEN** a required assertion is omitted or its only witness is hidden
- **THEN** source export rejects the disposition
- **AND** a readable aggregate is allowed without duplicating every kernel node

#### Scenario: Compression never erases product meaning

- **WHEN** an old text-count budget conflicts with complete product meaning
- **THEN** readability and semantic completeness remain hard constraints
- **AND** word or object reduction is only an optimization among feasible layouts

### Requirement: Hook contract queries preserve bounded observation failures

A selected immutable runtime's pure launcher query SHALL avoid unrelated
selection and policy initialization. Deadline expiration SHALL leave admission
unarmed and retain exact process diagnostics through activation and public
output. Fresh explicit observation may recover; the observer SHALL NOT replay
effects or reinstall on timeout alone.

#### Scenario: Query deadline expires

- **WHEN** the selected hook-contract child exceeds its deadline
- **THEN** the public binding reports the timeout, argv, binary, cwd and captured
  streams without an uncaught exception
- **AND** admission remains unarmed and guidance requests fresh observation

#### Scenario: Pure query has a bounded import closure

- **WHEN** a cold selected package renders its immutable launcher contract
- **THEN** it does not initialize runtime selection or repository policy
- **AND** the generated bytes remain identical for the same native platform

#### Scenario: Activation query expires after selection

- **WHEN** activation's post-selection hook query exceeds its deadline
- **THEN** the existing transaction restores prior selector, configuration and state
- **AND** public JSON retains exact query evidence and requests status, not reinstall
- **AND** no implicit query retry or effect replay occurs

### Requirement: Package identity tests consume locked build supply

Package identity and source-distribution tests SHALL execute with the declared
locked interpreter and its installed build dependencies. An empty ambient cache
SHALL NOT change their verdict when that supply is complete.

#### Scenario: Ambient build cache is empty

- **WHEN** package identity tests run offline with an empty cache
- **THEN** direct and source-distribution builds use the locked environment
- **AND** exact source identities and bundled Node package parity are verified

### Requirement: Hosted budget tool supply

Hosted verification SHALL prepare the declared source-budget cross-check
executable from versioned, digest-bound native supply before executing gates.
Both Forge projections SHALL consume the same preparation owner without system
installation or reliance on undeclared host executables.

#### Scenario: Clean supported runner

- **WHEN** a supported runner has no ambient cross-check executable
- **THEN** preparation verifies the declared archive and executable version
- **AND** hosted gates receive the project-local executable on their effective PATH

#### Scenario: Invalid or unavailable supply

- **WHEN** the archive, checksum, executable version or supported target is unavailable or invalid
- **THEN** verification fails before tests with the original supply diagnostic
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
owner. Declared ceilings SHALL be positive integer multiples of one hundred,
without coercion, unknown fields or per-file exemptions. Omitted role limits
SHALL inherit the declared default. An absent declaration SHALL impose no hidden
generic ceiling; malformed declarations SHALL block rather than become absent.

#### Scenario: Invalid or coercible policy

- **WHEN** a present declaration has invalid TOML, shape, field names or limits
- **THEN** the public size gate blocks with a policy-path-bound cause
- **AND** booleans, strings, floats, zero and fractional hundreds are not limits
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
