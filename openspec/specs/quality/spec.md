# ETHOS Quality

## Purpose

ETHOS SHALL define quality, determinism, documentation quality, proof policy,
and asset-governance semantics as a first-class product capability.
## Requirements
### Requirement: Quality Asset Model

ETHOS SHALL model repository assets across code, docs, shell, configuration,
evidence, release artifacts, and adopter profiles. The tracked tool catalog
SHALL be the sole declaration of a quality tool's identity, profile, adoption
state, configuration, and optional gate boundary.

#### Scenario: Asset policy is reported

- **WHEN** `ethos quality asset-policy --json` runs
- **THEN** ETHOS reports asset classes, dimensions, and catalog-derived tool
  profiles without executing provider tools

#### Scenario: Tool profiles are catalog-derived

- **WHEN** `ethos quality tool-profiles --json` or
  `ethos quality asset-policy --json` reports quality tool adapters
- **THEN** every adapter is derived from exactly one `system/tools.toml` entry
- **AND** its concern, tool identity, configuration, profile, adoption state,
  and optional gate agree with that entry
- **AND** the tools contract requires an adoption state of `active`,
  `candidate`, `deferred`, or `rejected`
- **AND** no parallel static Python tool-adapter registry supplies conflicting
  tool truth

### Requirement: Python Lint and Format Ratchet

ETHOS SHALL enforce Python lint and format through Ruff and SHALL keep explicitly
frozen ignored-rule debt visible and non-increasing.

#### Scenario: Ruff gate blocks current hard rules and ignored-rule growth

- **WHEN** hosted CI or `ethos prove --execute --json` runs the Python lint gate
- **THEN** ETHOS invokes `tools/ci/scripts/run-python-lint.sh`
- **AND** that owner script runs Ruff check and Ruff format with explicit
  `.config/checks/ruff/ruff.toml`, plus the Ruff ignored-rule ratchet script
- **AND** Ruff runtime cache lives under ignored `build/runtime/tool-cache/ruff`, not root `.ruff_cache/`
- **AND** the Ruff ratchet uses the same tracked Python file set as Ruff check and
  Ruff format, so packages, tools, tests, agent scripts, and CI adapters obey one
  repository-wide Python law
- **AND** each baseline in `.config/checks/ruff/ratchet.toml` must equal the
  current finding count for that ignored rule, not a slack maximum
- **AND** the gate fails both when findings exceed a baseline and when findings
  fall below a stale baseline, forcing debt reductions to be recorded
- **AND** a rule whose finding count reaches zero is removed from the ignored-rule
  ratchet and returns to the hard Ruff rule set
- **AND** a rule baseline may be lowered when findings are removed, but may not
  increase without an explicit quality debt decision

### Requirement: Gate Descriptor Model

ETHOS SHALL describe quality gates with asset classes, dimensions, execution
mode, evidence class, trust-bearing classification, tool adapter, file-write
policy, network policy, and version source. Gate descriptors, ordered runtime
and quality views, and product/adopter proof floors SHALL compile from one
strict, immutable, declaration-first registry rather than parallel Python
registries.

#### Scenario: Gate descriptors are reported

- **WHEN** `ethos quality gates --json` runs
- **THEN** every gate includes the quality descriptor fields required by the
  gate schema

#### Scenario: Gate registry has one declaration owner

- **WHEN** runtime proof planning or quality-gate reporting loads the gate registry
- **THEN** `system/gates.toml` is the repository declaration owner
- **AND** `packages/ethos-core/pyproject.toml` projects it into the wheel as
  `ethos_core/data/gates.toml`
- **AND** frozen Pydantic v2 contracts reject unknown fields, empty commands,
  duplicate gate ids per view, unavailable dependencies, and unknown proof-set ids
- **AND** Python compiles the declaration to runtime and quality projections but
  does not restate gate records or proof floors as hand-written registries

#### Scenario: Adopter-native gates extend the typed runtime registry

- **GIVEN** an adopted repository declares native code-correctness gate ids
- **WHEN** proof planning compiles the repository gate registry
- **THEN** each native id must have a complete descriptor under the profile
  proof table, including an executable command
- **AND** validated descriptors extend the runtime registry and participate in
  action-graph validation, policy digest, and proof-run conformance checks
- **AND** an id-only, invalid, duplicate, or product-conflicting descriptor emits
  an `adopter_gate_descriptor_*` required gap instead of raising an exception,
  guessing a command, overriding a product gate, or silently skipping the gate

### Requirement: Proof Policy Lattice

ETHOS SHALL distinguish planned, readiness, executed, proven, blocked,
accepted-risk, and waived-nonblocking proof states.

#### Scenario: Trust-bearing consumers require proven evidence

- **WHEN** `ethos quality proof-policy --json` runs
- **THEN** only `proven` is marked trust-bearing for claim, land, publish,
  release, and repository governance consumers

### Requirement: Documentation Quality Profile

ETHOS SHALL make documentation faithfulness, expressiveness, and elegance
mechanically checkable through metadata, visible reader sections, glossary,
links, anchors, and command examples.

#### Scenario: Docs profile is reported

- **WHEN** `ethos quality docs --json` runs
- **THEN** ETHOS reports docs quality profile checks alongside governed docs
  registry health

### Requirement: Parallel Timeout-Bound Test Gate

ETHOS SHALL run the default Python test gate through a reusable owner script that
supports bounded parallel execution, timeout protection, slow-test visibility,
JUnit output, branch coverage, and the configured hard coverage floor.

#### Scenario: default Python test gate is bounded and parallel-capable

- **WHEN** hosted CI or `ethos prove --execute --json` runs the Python test gate
- **THEN** ETHOS invokes `tools/ci/scripts/run-python-tests.sh`
- **AND** pytest policy requires `pytest-timeout` and strict config/marker handling
- **AND** the owner script honors `ETHOS_TEST_WORKERS`, defaulting to parallel workers
- **AND** the owner script reports slow test durations and writes JUnit output under `build/evidence/quality/tests/pytest`
- **AND** pytest runtime cache lives under ignored `build/runtime/tool-cache/pytest`, not `.config/`
- **AND** benchmark and Allure reporting remain planned or opt-in unless admitted as active gates

### Requirement: Configuration and Script Quality Gates

ETHOS SHALL make configuration and runner-script quality executable through
reusable owner scripts rather than provider-specific CI inline policy, and the
same owner scripts SHALL participate in the default ETHOS proof floor.

#### Scenario: Python tool policy is owned outside the repository root

- **WHEN** the Python lint or Python test gate executes
- **THEN** ETHOS invokes the reusable owner scripts under `tools/ci/scripts/`
- **AND** Ruff policy is read from `.config/checks/ruff/ruff.toml`
- **AND** pytest configuration is read from `.config/checks/pytest/pytest.ini`
- **AND** the repository root does not contain `ruff.toml` or `pytest.ini`
- **AND** adopter CI scaffolds do not assume the product repository's Ruff, pytest,
  or owner-script surfaces

#### Scenario: Product docs may reference bounded owner scripts

- **WHEN** `ethos quality command-examples --json` scans active product docs
- **THEN** ETHOS admits documented `tools/ci/scripts/*.sh` examples as bounded
  repository-owned runner-script surfaces
- **AND** arbitrary `tools/**` command roots remain unknown command examples

#### Scenario: TOML and YAML configuration gates execute through owner scripts

- **WHEN** hosted CI or `ethos quality toml --json` / `ethos quality yaml --json` runs
- **THEN** ETHOS invokes the reusable configuration lint script
- **AND** TOML files are parsed, checked for exactly one final newline, checked
  for trailing whitespace, formatted with the configured Taplo policy, and linted
  with Taplo
- **AND** YAML files are linted with the configured Yamllint policy
- **AND** `.gitlab-ci.yml` does not duplicate Taplo or Yamllint policy inline

### Requirement: Structural Blank-Line Contract

ETHOS SHALL use one blank line as the only separator between adjacent semantic
blocks in active governed text carriers. It SHALL reject leading, trailing, and
repeated blank-line runs through the carrier's native formatter where one owns
the language, or through the shared structural reader otherwise. Python SHALL
remain governed only by Ruff's language-native formatting contract.

#### Scenario: Active configuration has repeated blank lines

- **WHEN** an active governed configuration or provider projection contains two
  or more consecutive blank lines
- **THEN** its owning quality command fails with a line-addressed diagnostic

#### Scenario: Shell embeds another language

- **WHEN** a Shell carrier contains a heredoc body
- **THEN** the structural reader checks the outer Shell layout without applying
  the Shell blank-line contract inside the embedded body

#### Scenario: Shell quality executes through the owner script

- **WHEN** hosted CI or `ethos quality shell --json` runs
- **THEN** ETHOS invokes the reusable shell lint script
- **AND** ShellCheck policy is read from `.config/checks/shell/.shellcheckrc`
- **AND** `.gitlab-ci.yml` does not duplicate ShellCheck policy inline

#### Scenario: Tool catalog exposes active configuration gates

- **WHEN** `system/tools.toml` is inspected
- **THEN** TOML, YAML, and shell concerns are marked active with their owning
  config path and reusable gate script
- **AND** planned tool entries do not masquerade as active gates

#### Scenario: Default proof consumes the active quality floor

- **WHEN** `ethos prove --json` builds its default action graph
- **THEN** the graph includes TOML, YAML, shell, Python lint, Python type,
  docstring, module-layout, Python size, unit/coverage, and format-policy gates
- **AND** CI, pre-commit, and proof invoke reusable owner scripts instead of
  copying tool command policy into provider projections

#### Scenario: Report exposes hard quality-floor gaps

- **WHEN** a product hard quality gate such as Python size, module layout,
  coverage, type policy, or public-surface docstrings reports required gaps
- **THEN** `ethos report --json` includes those gaps in its blocking
  `required_gaps`
- **AND** the report state is not ready
- **AND** the report payload includes a `hard_quality_floor` read model with the
  contributing gate verdicts
- **AND** next actions point to the concrete standalone quality command instead
  of implying full proof can close the gap

#### Scenario: Coverage quality read model reports the active floor

- **WHEN** `ethos quality coverage --json` runs
- **THEN** ETHOS reports the coverage policy source, current hard floor, aspirational
  floor, branch coverage requirement, configured source paths, configured
  `fail_under`, owner script, and latest coverage artifact summary when present
- **AND** the command reports required gaps when policy or config is missing,
  `fail_under` diverges from the hard floor, branch coverage is disabled while
  required, the latest artifact is missing or malformed, or latest coverage is
  below the hard floor
- **AND** when the Python test owner script holds the coverage evidence write
  lock and the latest artifact is temporarily absent, the command reports the
  writer as in-progress advisory state rather than a stale coverage failure
- **AND** the command remains read-only and does not replace the reusable Python
  test gate owner script

### Requirement: Repository Hygiene Gate

ETHOS SHALL make repository-shape hygiene visible through one owner script and a
separated policy file so host-local residue, text-shape drift, merge markers,
large tracked files, malformed JSON, and forbidden stash guidance cannot hide in
Git, global ignores, provider projections, or hook-local behavior.

#### Scenario: Hidden root host-local residue fails closed

- **WHEN** `tools/ci/scripts/run-repository-hygiene.sh` runs
- **THEN** the gate reads `.config/checks/repository-hygiene/policy.toml` as the
  policy owner
- **AND** globally ignored root host-local files such as `.DS_Store`,
  `Thumbs.db`, and `Desktop.ini` fail with a required hygiene error
- **AND** the gate reports the residue without deleting, stashing, or promoting
  it into repository truth
- **AND** CI providers, pre-commit hooks, and local CI call the owner script
  instead of duplicating the policy body.

### Requirement: Generated Artifact Topology Gate

ETHOS SHALL keep generated artifact placement auditable so source,
configuration, semantic documentation, repository root, runtime state,
generated proof output, and curated evidence remain distinct authority
surfaces.

#### Scenario: Root generated drift remains blocked while ignored test residue is local

- **WHEN** `ethos quality generated-artifacts --json` scans repository root paths
- **THEN** tracked or unignored generated outputs in repo root fail with
  `generated_artifact_repo_root_drift:<path>`
- **AND** ignored and untracked root `.coverage*`, `coverage.xml`, and `junit.xml`
  are reported as ignored local test residue rather than required gaps
- **AND** unrelated root generated outputs such as `proof.json` remain blocked
- **AND** the command remains read-only and does not clean files as part of the
  verdict

#### Scenario: Semantic generated homes are enforced

- **WHEN** `ethos quality generated-artifacts --json` scans ignored local state
- **THEN** root tool cache homes such as `.import_linter_cache/`,
  `.import-linter-cache/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`,
  `.tox/`, `.nox/`, `.uv-cache/`, and root `dist/` fail even when ignored
- **AND** retired flat generated homes such as `build/cache/` and
  `build/runtime/gitlab-ci-local/` fail
- **AND** allowed generated homes are semantic: `.cache/local-state/`,
  `.ethos/state/`, `build/runtime/tool-cache/<tool>/`,
  `build/runtime/work/<provider>/`, `build/evidence/`, `build/ethos/`, and
  `build/artifacts/<kind>/`
- **AND** the command reports lifecycle classes for `runtime_cache`,
  `machine_evidence`, `local_artifact`, and `curated_evidence`.

#### Scenario: Generated artifact producer entrypoints are audited

- **WHEN** `ethos quality generated-artifacts --json` runs
- **THEN** the command reports an `entrypoint_audit` over active CI projections,
  reusable owner scripts, package entrypoints, and tool configuration
- **AND** pytest entrypoints must use `.config/checks/pytest/pytest.ini`, route
  pytest cache to `build/runtime/tool-cache/pytest`, and write coverage/JUnit
  machine evidence under `build/evidence/quality/tests/`
- **AND** Ruff and import-linter entrypoints must route runtime cache under
  `build/runtime/tool-cache/ruff` and `build/runtime/tool-cache/import-linter`
- **AND** package build entrypoints must write to `build/artifacts/<kind>`
- **AND** `gitlab-ci-local` entrypoints must route provider state to
  `build/runtime/work/gitlab-ci-local`
- **AND** cleanup commands may remove denied residue but do not make a producer
  that recreates denied homes compliant.

#### Scenario: Product proof seals topology after runtime-producing gates

- **WHEN** the default product proof executes its quality gates
- **THEN** `generated-artifacts` runs after the Ruff and Python test gates
- **AND** root `.pytest_cache/` and `.ruff_cache/` remain denied at the final
  topology verdict
- **AND** the Python test gate removes those denied root caches at both entry
  and EXIT cleanup
- **AND** standalone `ethos quality generated-artifacts --json` remains
  read-only and fails closed on surviving root cache drift.

#### Scenario: Runtime-producing quality owners stay semantically bound and portable

- **WHEN** the product runs its type, lint, Ruff-ratchet, or Bandit owner
  gates from a governed checkout
- **THEN** `ty` resolves third-party imports against
  `build/runtime/venv`, never an ambient host or root `.venv`
- **AND** each owner gate preserves its tracked Python-file scope under the
  macOS-provided Bash 3.2
- **AND** no owner gate requires a newer shell or silently weakens its file
  selection to obtain portability.

### Requirement: No Compatibility Residue Gate

ETHOS SHALL enforce destructive cutover by blocking compatibility residue in
production source after migration closeout.

#### Scenario: Production compatibility residue is blocked

- **WHEN** `ethos quality no-compat --json` runs
- **THEN** ETHOS scans product production source roots
- **AND** it reports required gaps for compatibility shims, deprecated surfaces,
  legacy wrappers, dynamic export forwarding, and import-path shells
- **AND** it does not scan test fixtures that intentionally contain blocked
  examples
- **AND** the default product proof floor includes the no-compat gate

### Requirement: Python Module Layout Gate

ETHOS SHALL gate Python module layout as a quality property so semantic
sub-packages, package-root visibility, suffix-flat debt, flat-directory debt,
ordinary-module facade debt, same-directory flat-growth, baseline growth, and
import-alias compatibility residue cannot grow through normal write paths.

#### Scenario: Semantic module layout is reported and enforced

- **WHEN** `ethos quality module-layout --json` runs
- **THEN** ETHOS reports suffix-module, suffix-flat, flat-directory, private import
  alias, package `__init__.py` facade, ordinary module facade, flat-growth, and
  baseline-growth findings against
  `.config/checks/module-layout/policy.toml`
- **AND** new findings outside the ratchet baseline fail the gate
- **AND** the ratchet baseline declares `baseline_gap_limit`, fails unless the
  current allowed-baseline count exactly matches that limit, and fails when
  baseline entries no longer correspond to current findings
- **AND** the ratchet baseline declares per-kind baseline limits for suffix
  modules, suffix-flat groups, flat directories, private import aliases, package
  init facades, and ordinary module facades, so one debt category cannot grow
  while the total count appears unchanged
- **AND** adding baseline entries or raising `baseline_gap_limit` fails the gate
- **AND** adding governed modules to existing crowded directories fails before the
  directory reaches a larger flat-directory breach
- **AND** creating a brand-new directory with more than the configured direct
  module burst limit fails before the directory becomes a flat bucket
- **AND** package-root `__init__.py` files remain declaration-only docstring
  boundaries rather than re-export or compatibility facades
- **AND** ordinary modules cannot act as import-only compatibility re-export
  facades
- **AND** ordinary modules cannot act as module-level `__getattr__` dynamic
  compatibility export facades
- **AND** changed governed Python modules cannot import private symbols from
  another module with `from ... import _private` as a compatibility or helper
  dependency
- **AND** hosted CI, pre-commit, local CI, and proof invoke the reusable
  `tools/ci/scripts/run-module-layout.sh` owner script instead of duplicating
  the policy inline.

### Requirement: Python Public-Surface Docstring Gate

ETHOS SHALL gate intent-bearing Google-style docstrings for public Python product surfaces
without requiring private helper docstrings to become a parallel documentation
store.

#### Scenario: Public docstring coverage is reported

- **WHEN** `ethos quality docstrings --json` runs
- **THEN** ETHOS reports configured source paths, minimum coverage, documented
  public-surface count, total public-surface count, missing symbols, Google-style
  conformance, and a non-blocking broader public-definition inventory
- **AND** the configured minimum coverage floor is 100 percent for product
  public surfaces
- **AND** the gate fails when public-surface coverage is below the configured
  threshold
- **AND** existing structured docstrings must use Google-style sections and their
  `Args` section must match the Python signature
- **AND** retired reStructuredText or NumPy-style sections are rejected
- **AND** the gate scope is limited to product-visible Python surfaces such as
  CLI command functions, explicit exports, and package boundary docstrings
- **AND** hosted CI invokes the reusable docstring coverage script instead of
  duplicating the policy inline.

### Requirement: Product Boundary and Contributor Policy Gate

ETHOS SHALL keep active product surfaces, release metadata, and contributor
policy organization-native rather than person-native or adopter-private.

#### Scenario: Active product boundary is enforced

- **WHEN** hosted CI, pre-commit, local CI, or `ethos prove --execute --json`
  runs the product boundary gate
- **THEN** ETHOS invokes `tools/ci/scripts/run-product-boundary.sh`
- **AND** the owner script runs `ethos quality product-boundary --json` and
  `ethos quality contributor-policy --json`
- **AND** active product surfaces reject hardcoded personal identity literals,
  local workstation paths, private infrastructure URLs, adopter-specific
  literals, generic lifecycle bucket phrases, session-authority phrases, and
  person attribution fields in release/package metadata
- **AND** active product plans, rules, and configuration comments reject named
  private repository references as product authority while allowing generic
  reference-adopter and mechanism-class language
- **AND** distribution manifests explicitly allowlist neutral launcher assets
  and reject historical evidence, local state, tests, adopter-private records,
  private paths, and person attribution metadata from published package scope
- **AND** ignored host-local state under `.ethos/state/**` is not scanned as an
  active product surface
- **AND** historical evidence and archived change records may retain factual
  names only as historical records, not as active product defaults or authority

#### Scenario: Contributor policy is role-based

- **WHEN** `ethos quality contributor-policy --json` runs
- **THEN** ETHOS reports identity mode, allowed identity count, allowed roles,
  and contributor-policy findings
- **AND** single built-in author policy is rejected for active product
  governance
- **AND** product repositories use external role policy rather than a built-in
  author, personal allowlist, or local workstation identity
- **AND** the configured policy includes at least one maintainer or team role
  and at least one bot or service role
- **AND** Git author, Git committer, Work Lane actor, reviewer, maintainer,
  bot, team, and adopter-side owner remain distinct identity facts
- **AND** an opt-in local pre-push identity policy may require newly pushed
  commits to match the checkout's configured Git identity without creating a
  product-hardcoded personal author

#### Scenario: Enterprise readiness aggregates closeout layers

- **WHEN** `ethos quality enterprise-readiness --json` runs
- **THEN** ETHOS reports every enterprise closeout planning layer from L0
  through L8
- **AND** the report lifts required gaps from workspace status, report
  scorecard, product boundary, docs topology, contributor policy, governance
  context, generic parity, generated artifacts, release policy, and
  claim-carrier checks
- **AND** the report is clean only when every layer is clean
- **AND** the report states that remote publication, external adopter
  retirement, and foreign Work Lane cleanup are outside the local closeout claim
  unless separately authorized
- **AND** the enterprise-readiness aggregator belongs to the domain layer because
  it composes status, report, policy, parity, claims, and release checks rather
  than owning repository truth directly
- **AND** repository policy modules do not import domain or adapter modules to
  make the enterprise-readiness result pass import-linter

#### Scenario: Governance kernel is independently enforced

- **WHEN** `ethos quality governance-kernel --json` runs
- **THEN** ETHOS checks the live `governance_context`, governance profile
  isomorphism, first-glance product docs, and generic adoption scaffold
- **AND** the gate requires `Authority -> Subject -> Commitment -> Change ->
  Evidence -> Claim -> Chronicle` as the shared kernel chain
- **AND** the gate requires `ethos status`, `ethos plan`, `ethos prove`,
  `ethos land`, and `ethos publish` as the same transition command semantics
  for product and adopted repositories
- **AND** product and adopted repositories may differ only by authority binding,
  profile configuration, adapter binding, strictness, and rollout
- **AND** the gate blocks a second command plane, product cloning, profile-driven
  kernel changes, or adopter-specific product authority
- **AND** `tools/ci/scripts/run-governance-kernel.sh` is the reusable owner
  script and participates in the local product-boundary and local-CI gate bundle

### Requirement: Evidence Freshness Protocol Gate

ETHOS SHALL treat evidence freshness as the read model that checks claim
digests, claim evidence freshness, and evolution-ledger protocol health without
creating another truth store.

#### Scenario: evidence freshness reports claim and evolution protocol health

- **WHEN** `ethos quality evidence-freshness --json` runs
- **THEN** the result includes claim digest/head checks from `evidence/claims`
- **AND** the result includes evolution protocol checks from `evolution/ledger.toml`
- **AND** the result includes evidence topology checks for the durable evidence
  root, flat claim records, topic-scoped chronicle records, and parity artifacts
- **AND** required gaps from claims, evolution, or evidence topology block the command
- **AND** the command does not execute proof refs or claim hosted CI success

#### Scenario: default proof includes evidence freshness

- **WHEN** `ethos prove --json` builds the default product or adopter proof graph
- **THEN** the graph includes the trust-bearing `evidence-freshness` gate after
  `claims`
- **AND** the gate command is `ethos quality evidence-freshness --json`

### Requirement: Hosted CI tool supply is deterministic enough to support quality proof

Hosted CI jobs that require downloaded binary tools MUST use repository-owned
installer scripts with a shared cache, resumable artifact download, bounded retry
policy, and archive validation before the tool is installed.

#### Scenario: A binary tool installer runs in hosted CI

- **WHEN** a hosted CI job needs gitleaks or Node
- **THEN** the job invokes a repository-owned installer script
- **AND** the installer downloads through the shared CI artifact helper
- **AND** the artifact is cached under `build/runtime/tool-cache/ci-tools/`
- **AND** the installer validates the cached archive before reuse

### Requirement: Executable tooling adoption gates

ETHOS SHALL activate roadmap tools as quality gates only after every owner
surface exists: tool catalog, config owner, reusable runner, CI or hook
projection, and tests or proof coverage.

#### Scenario: Dependency hygiene is package-local and non-vulnerability evidence

- **WHEN** the dependency hygiene gate runs
- **THEN** ETHOS SHALL invoke `tools/ci/scripts/run-dependency-hygiene.sh`
- **AND** the runner SHALL execute `deptry` per Python distribution rather than
  treating the workspace root as one runtime package
- **AND** the resulting evidence SHALL be local owner-gate evidence
- **AND** it SHALL NOT claim vulnerability scanning or hosted CI success.

#### Scenario: Prose and schema hygiene are report-first gates

- **WHEN** prose spelling or JSON Schema hygiene runs
- **THEN** ETHOS SHALL invoke the reusable owner scripts
- **AND** the prose gate SHALL NOT rewrite digest-bound evidence or archived
  records
- **AND** the schema gate SHALL validate schema documents without replacing
  command payload validation.

### Requirement: Python Vulnerability Audit Gate

ETHOS SHALL run Python dependency vulnerability auditing through a reusable owner
script that uses a supported resolved dependency input, keeps scanner claim
boundaries explicit, and retries only classified transient transport failures
before parsing scanner output. The retry policy SHALL use a fixed bounded attempt
limit and SHALL fail closed when the scanner reports vulnerabilities, emits
malformed JSON, or fails for any unclassified reason.

#### Scenario: pip-audit scans uv-exported resolved requirements

- **WHEN** hosted CI, local CI, or `ethos prove --execute --json` runs the Python
  vulnerability audit gate
- **THEN** ETHOS SHALL invoke `tools/ci/scripts/run-python-vulnerability-audit.sh`
- **AND** the runner SHALL export a frozen resolved requirements input from
  `uv.lock` before invoking `pip-audit`
- **AND** the runner SHALL invoke `pip-audit` with `--no-deps --disable-pip` so
  the exported pinned input is audited without dependency resolution or a pip
  bootstrap step
- **AND** the evidence SHALL be local owner-gate evidence under
  `build/evidence/quality/security/`
- **AND** the gate SHALL NOT claim that `pip-audit` reads `uv.lock` directly
- **AND** the gate SHALL NOT claim OSV scanner coverage, image/package scanning,
  hosted CI success, or remote publication.

#### Scenario: transient scanner transport disconnect is retried within bounds

- **WHEN** `pip-audit` fails before producing usable JSON with a classified
  transient transport-disconnect diagnostic
- **THEN** the owner script SHALL retry at most once after a fixed delay
- **AND** it SHALL continue only if a later attempt succeeds with valid JSON
- **AND** it SHALL not create tracked retry state or transform the resulting
  evidence into hosted-provider proof.

#### Scenario: vulnerability or non-transient scanner failure remains final

- **WHEN** `pip-audit` reports a vulnerability, produces malformed JSON, or
  fails with an unclassified diagnostic
- **THEN** the owner script SHALL return a nonzero result without retrying that
  result
- **AND** it SHALL NOT emit a passing vulnerability-audit summary.

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
- **AND** product and adopter profiles expose status-required coordination gaps
  in report `required_gaps` and `gap_layers.coordination_risk.required_gaps`
- **AND** advisory coordination signals stay advisory and do not authorize foreign
  Work Lane cleanup
- **AND** advisory-only scorecards report `state=advisory` with `ok=true` rather
  than collapsing advisory visibility into `state=ready`
- **AND** effective score reflects hard floors and required coordination risk
  rather than presenting a misleading green nominal score alone

### Requirement: Local-ci fallback projects owner scripts from target root

ETHOS local-ci fallback evidence SHALL derive invoked owner scripts from the
actual target repository's local-ci script.

#### Scenario: publish is run with an explicit root from another cwd

- **WHEN** `ethos publish --root <repo> --json` assembles local-ci fallback
- **THEN** owner scripts come from `<repo>/.config/ci/scripts/run-local-ci.sh`
- **AND** the local-submit package and fallback evidence agree
- **AND** hosted CI status remains unclaimed

#### Scenario: local-ci fallback evidence is stale, missing, invalid, or current

- **WHEN** `ethos publish --json` assembles local-ci fallback evidence
- **THEN** the fallback package reports `evidence_status.path`,
  `evidence_status.current_head`, `evidence_status.evidence_head`,
  `evidence_status.state`, and `evidence_status.ok`
- **AND** stale, missing, or invalid local-ci fallback evidence directs the caller
  to rerun `tools/ci/scripts/run-local-ci.sh`
- **AND** current fallback evidence says only that local CI fallback evidence is
  current at HEAD; it does not claim hosted CI success or remote publication

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
- **AND** the Git history scan invokes `gitleaks git` with the repository path as
  the command argument rather than the removed `--source` flag

### Requirement: Global Executable Source Budget And Compression Debt

ETHOS SHALL measure maintained executable source across product code, tests,
tools, shell, JavaScript, declarations, schemas, templates, and tracked derived
projections. It SHALL reject an unbounded source increase that lacks an explicit
compression-debt record, but that global report SHALL not be part of the default
fine-grained promotion proof floor. Source-budget remains required for full
proof and global compression closeout. When a stale Work Lane is reconstructed
on a newer candidate train, candidate-owned debt records MUST remain visible,
every active record MUST have one registered ISO-8601 deletion wave and expiry,
and measured settlement MUST remove only the named allowance. Reconstruction
MUST preserve immutable baseline and terminal targets and regenerate evidence
from the successor HEAD.

#### Scenario: A fine-grained Change and a global compression debt coexist

- **WHEN** a fine-grained Change runs the default executed promotion proof
- **THEN** the proof SHALL not fail only because `ethos quality source-budget
  --json` reports a current global compression gap
- **AND** `ethos report --json` SHALL expose that gap in a distinct advisory
  global-compression layer with a direct source-budget action
- **AND** `ethos prove --full` and global compression closeout SHALL still
  require a clean source-budget report before claiming program completion.

#### Scenario: A migration reports global source deltas

- **WHEN** `ethos quality source-budget --json` evaluates a governed repository
- **THEN** it reports the baseline identity, current HEAD, global and carrier
  metrics, independent inventory status, terminal budgets, and active debt
- **AND** the metric does not exclude a tracked executable carrier merely because
  its logic moved from Python into TOML, CEL, Jinja, generated output, tests, or
  tools
- **AND** each active debt record names the added surface, owner, replacement,
  expiry, deletion wave, and expected net deletion
- **AND** a stale, missing, expired, or over-budget debt record is a required gap.

#### Scenario: Archived OpenSpec metadata remains historical evidence

- **WHEN** `ethos quality source-budget --json` evaluates archived OpenSpec
  change records
- **THEN** it SHALL exclude only the `.openspec.yaml` metadata file beneath
  `openspec/changes/archive/`
- **AND** active OpenSpec metadata and every other tracked YAML carrier SHALL
  remain in the source-budget inventory
- **AND** the exclusion SHALL not broaden to archived proposals, designs, tasks,
  specification deltas, or arbitrary YAML paths.

#### Scenario: Successor reconstruction preserves candidate debt and settled deletion

- **GIVEN** a source-budget Work Lane is stale behind `candidate/dev`
- **AND** candidate has added valid debt records while the stale Lane has measured settlement of a distinct record
- **WHEN** ETHOS reconstructs source-budget behavior in a new candidate-based Work Lane
- **THEN** the resulting policy retains candidate-only records with explicit lifecycle fields
- **AND** it removes only the settled record's allowance
- **AND** its aggregate allowance equals the sum of all retained active records
- **AND** it preserves the declared baseline and terminal limits
- **AND** stale parity, proof, and claim artifacts are regenerated rather than replayed as evidence

#### Scenario: Active debt rollover remains bounded and explicit

- **GIVEN** inherited active debt waves and matching record expiries are dated July 17, 2026
- **AND** the candidate train advances before the successor can produce clean proof
- **WHEN** the successor records its one-time lifecycle rollover
- **THEN** the inherited active waves and matching expiries move to July 18, 2026
- **AND** no record ID, expected deletion, allowance, aggregate cap, baseline, terminal limit, or settled deletion changes
- **AND** a later rollover requires a new recorded decision rather than an implicit extension

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

### Requirement: Local dependency runtime trees are excluded from artifact topology traversal

ETHOS SHALL exclude non-authoritative local dependency runtime roots from
recursive generated-artifact candidate traversal, including a Pixi `.pixi/`
environment tree, while retaining generated-artifact policy evaluation for all
non-excluded repository paths.

#### Scenario: Pixi-backed Work Lane runs the topology gate

- **WHEN** `ethos quality generated-artifacts --json` runs in a Work Lane that
  contains a local `.pixi/` environment tree
- **THEN** the audit SHALL prune `.pixi/` before recursive candidate descent
- **AND** the command SHALL remain finite and read-only
- **AND** adjacent non-excluded generated-artifact drift SHALL remain subject to
  the existing policy.

### Requirement: Bounded evidence-carrier debt remains explicit

ETHOS SHALL account for a temporary active evidence-carrier footprint through a
named source-budget debt record rather than a per-file exemption or baseline
reset.

#### Scenario: A compact active claim is introduced

- **WHEN** an active claim and its mandatory carrier metadata exceed the
  currently available source-budget slack
- **THEN** any temporary allowance SHALL name its owner, replacement, deletion
  wave, expiry, and exact allowance
- **AND** it SHALL remain within the existing maximum debt
- **AND** formatting policy MAY keep declarative arrays compact without changing
  the claim schema or its trust boundary.

### Requirement: Zero-Tolerance Python Type Policy

ETHOS SHALL enforce Python type checking as a fail-closed, zero-diagnostic
quality gate for every package declared by `.config/checks/ty/policy.toml`.
The policy SHALL contain no type-diagnostic ratchet, baseline, ignore, or
exception once a package is governed by this requirement.

#### Scenario: Unknown type-tool execution blocks proof

- **WHEN** `ty` is unavailable, cannot launch, exits without a terminal
  diagnostic result, or produces malformed terminal output
- **THEN** `ethos quality types --json` reports a stable required execution gap
- **AND** the command exits non-zero through its enforced quality verdict
- **AND** the result does not report the unknown execution as zero diagnostics

#### Scenario: Every declared package has zero diagnostics

- **WHEN** `ethos quality types --json` runs with an available `ty` runtime
- **THEN** every package declared in the zero-tolerance policy reports
  `tier = "zero_tolerance"` and `limit = 0`
- **AND** any positive diagnostic count reports
  `ty_zero_tolerance_violation:<package>:<count>`
- **AND** CI and the default proof graph invoke the same owner gate

#### Scenario: Retired type debt cannot return as a baseline

- **WHEN** all governed packages report zero diagnostics
- **THEN** the type policy contains no ratchet table or equivalent exception
- **AND** a future diagnostic blocks immediately rather than establishing a
  new tolerated count

### Requirement: Declarative Product-Parity Test Partitions

ETHOS SHALL represent finite, uniform product-parity verification partitions as
compact test-only fixtures and declarative pytest case tables when the resulting
scoped representation is a net deletion and preserves exact public contracts.

#### Scenario: Accepted differences retain exact contracts

- **WHEN** a case covers an external stricter state, gap, or plan scope
- **THEN** the table asserts the same semantic-diff and accepted-difference
  contract with a domain-named case identifier

#### Scenario: Compression preserves diagnostic boundaries

- **WHEN** product-parity tests are consolidated
- **THEN** false-negative, process-failure, schema-validation, and integration
  boundaries remain independently named and the recorded surface is smaller

#### Scenario: Runtime classification boundaries remain named

- **WHEN** a shadow runner distinguishes missing backends, timeouts, malformed
  output, verdict exit code, or invocation root behavior
- **THEN** the suite SHALL retain direct, domain-named coverage for each distinct
  process or routing boundary.

#### Scenario: Evidence destination and freshness contracts remain exact

- **WHEN** a parity evidence test varies only by durable evidence root, target
  identity, or acceptable current/parent head condition
- **THEN** a declarative test partition MAY share inert setup while asserting the
  same evidence path, identity, and freshness contract.

#### Scenario: Compression does not reimplement parity semantics

- **WHEN** reusable test helpers are introduced
- **THEN** they SHALL construct literal fixtures and asserted public envelopes
  only, and SHALL NOT classify product payloads or normalize runtime semantics.

### Requirement: Compact Declarative Rules-Evaluation Test Inputs

ETHOS SHALL represent stable rule-evaluation fact envelopes through compact
immutable test declarations and SHALL remove equivalent coverage-only scenario
bodies when the canonical test surface preserves their public contracts.

#### Scenario: Fact and waiver partitions remain fail-closed

- **WHEN** the rules test suite evaluates malformed, unavailable, stale,
  non-deterministic, conflicting, or waived facts
- **THEN** the canonical tests assert the same public state and required-gap
  contract while duplicate coverage-only scenario bodies are absent

#### Scenario: Compression does not weaken verification

- **WHEN** compact fact declarations replace legacy test setup
- **THEN** focused coverage and the repository proof floor still pass and the
  targeted effective test-line total is lower than its recorded baseline

### Requirement: Declarative Coordination-Lifecycle Test Partitions

ETHOS SHALL represent finite uniform coordination-lifecycle test inputs as
literal declarative partitions when the formatted scoped test representation is
a net deletion and preserves exact public lifecycle contracts.

#### Scenario: Pure helper cases remain direct and bounded

- **WHEN** handoff context, lease projection, or prewrite normalization cases
  differ only in literal input and expected public output
- **THEN** the test MAY use a local literal case table without deriving expected
  lifecycle semantics from production code

#### Scenario: Effect boundaries retain named coverage

- **WHEN** a case executes handoff, SQLite lease, Git-ref, or recovery effects
- **THEN** the test SHALL retain a domain-named boundary and exact failure or
  state assertion rather than merge unrelated effect sequences

#### Scenario: Duplicate normalization probes are removed safely

- **WHEN** multiple unrelated tests repeat the same shared normalizer scalar
  rejection probe
- **THEN** one direct named normalizer test SHALL retain the tuple and scalar
  contracts and the unrelated duplicate probes SHALL be absent

#### Scenario: Formatter-aware compression is measured

- **WHEN** Python test compression changes a file with pre-existing formatter
  drift
- **THEN** the recorded result SHALL compare the formatter-clean scoped ELOC to
  the formatter-clean baseline and SHALL not claim deletion from unformatted
  layout alone

### Requirement: Declarative Work-Lane Admission Test Partitions

ETHOS SHALL represent finite equivalent Work-Lane admission failure states as
bounded declarative test partitions when the formatter-clean scoped test
representation is a net deletion and each state-specific setup, blocking gap,
and no-worktree invariant remains explicit.

#### Scenario: Candidate readiness states remain independently covered

- **WHEN** the candidate branch is missing, the candidate worktree is missing,
  or the candidate worktree is dirty
- **THEN** a distinct declarative test case SHALL assert the corresponding
  blocking gap
- **AND THEN** no requested Work Lane checkout SHALL be created.

#### Scenario: Accepted-root start blockers remain independently covered

- **WHEN** a nested Work Lane start is requested from a Work Lane or the
  accepted root is dirty
- **THEN** a distinct declarative test case SHALL assert
  `lane_start_requires_clean_accepted_root`
- **AND THEN** no requested Work Lane checkout SHALL be created.

### Requirement: Declarative Cross-Host Handoff Test Command Envelopes

ETHOS SHALL factor a finite family of equivalent cross-host handoff test command
envelopes into one bounded typed local helper when the formatter-clean scoped
representation is a net deletion and each case-specific input and result remains
explicit.

#### Scenario: Export modes retain independent behavior

- **WHEN** a cross-host export uses a file or text context and clean, omitted,
  committed, or preserved dirty disposition
- **THEN** each test SHALL retain its distinct expected success or blocking
  result through the shared command envelope.

### Requirement: Declarative CLI Lifecycle Fixture Reuse

ETHOS SHALL reuse test-only literal fixture builders for repeated CLI lifecycle
topology and Git commit mechanics when formatter-clean scoped test ELOC is a
net deletion and every command-specific public assertion remains in its named
test.

#### Scenario: Work-Lane lifecycle contracts retain their command boundary

- **WHEN** land or publish tests require an adopted accepted root, candidate
  worktree, owned Work Lane, or a committed fixture file
- **THEN** a typed test-only helper MAY construct that topology or commit
  literal file content
- **AND THEN** each named test SHALL invoke its own command and assert its own
  state, gaps, and payload contract.

### Requirement: Canonical Workspace-Status Schema Sample Reuse

ETHOS SHALL validate schemas through real producer payloads and focused local
negative mutations. Synthetic production sample builders SHALL NOT be retained
solely to make a schema-quality report green.

#### Scenario: UI projection fields remain rejected

- **WHEN** a workspace-status producer test adds a forbidden UI projection field
to its real payload
- **THEN** validation SHALL fail with required gaps

### Requirement: Runtime-Owned Schema Contract Validation

ETHOS SHALL validate published schemas and real repository producer payloads
without retaining synthetic sample builders in production runtime merely to
exercise schema shape.

#### Scenario: UI projection fields remain rejected

- **WHEN** a workspace-status producer test adds a forbidden UI projection field
  to its real payload
- **THEN** validation SHALL fail with required gaps
- **AND THEN** the validation SHALL remain owned by that producer boundary.

### Requirement: Structural blank-line contract

ETHOS SHALL use one blank line as the only separator between adjacent semantic
blocks in active governed text carriers. It SHALL reject leading, trailing, and
repeated blank-line runs through the carrier's native formatter where one owns
the language, or through the shared structural reader otherwise. Python SHALL
remain governed only by Ruff's language-native formatting contract.

#### Scenario: active configuration has repeated blank lines

- **WHEN** an active governed configuration or provider projection contains two
  or more consecutive blank lines
- **THEN** its owning quality command fails with a line-addressed diagnostic

#### Scenario: Shell embeds another language

- **WHEN** a Shell carrier contains a heredoc body
- **THEN** the structural reader checks the outer Shell layout without applying
  the Shell blank-line contract inside the embedded body

#### Scenario: Active OpenSpec carrier contains repeated blank lines

- **WHEN** an active OpenSpec spec or Change Markdown carrier contains two or
  more consecutive blank lines
- **THEN** the shared reader reports the repeated blank run without replacing
  official OpenSpec schema validation

### Requirement: Curated JSON Evidence Carrier Admission

ETHOS SHALL keep tracked JSON placement fail-closed and SHALL admit a curated
Chronicle JSON evidence carrier only when the format-selection policy names its
exact repository-relative file path.

#### Scenario: Exact convergence inventory is admitted

- **WHEN** the tracked Work Lane convergence inventory is present at
  `evidence/chronicle/all-work-lanes-convergence-20260716/lane-inventory.json`
- **THEN** the format-selection owner script accepts that exact file as a
  declared JSON carrier
- **AND** the audit remains clean when every other JSON path satisfies its
  declared carrier boundary.

#### Scenario: Unlisted Chronicle JSON remains blocked

- **WHEN** a tracked JSON file appears under `evidence/chronicle/` without an
  exact file declaration
- **THEN** the format-selection owner script reports that JSON as outside its
  declared carrier home
- **AND** no broad Chronicle-root allowance is inferred.

### Requirement: Portable configuration-lint interpreter resolution

ETHOS configuration-lint owner scripts SHALL run inline Python standard-library
validation through an explicit bounded interpreter chain: `ETHOS_PYTHON`, then
`PYTHON`, then `python3`. They SHALL NOT require a bare `python` command alias.
Targeted TOML-only invocations SHALL retain all TOML checks even when no JSON or
YAML target is present.

#### Scenario: standalone runtime lacks a python alias

- **GIVEN** a standalone configuration-lint fixture exposes `python3` but no
  bare `python` executable
- **WHEN** its targeted TOML check runs with runtime bootstrap already marked
- **THEN** the TOML parser, newline, whitespace, Taplo format, and Taplo lint
  checks complete successfully
- **AND** the runner does not invoke the absent `python` alias.

### Requirement: Isolated sharded Python test evidence preserves the quality floor

ETHOS SHALL permit the Python test owner script to use an explicit isolated
evidence root, pytest base temporary directory, and finite shard count while
preserving the same selected tests, coverage combination, coverage floor, and
HEAD-stability check as its unsharded execution.

#### Scenario: isolated sharded execution completes

- **WHEN** the Python test owner script runs with isolated evidence and
  temporary paths plus a positive shard count
- **THEN** it combines all completed shard coverage before enforcing the
  declared coverage floor
- **AND** it leaves no trust-bearing claim that a hosted provider ran.

