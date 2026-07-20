## MODIFIED Requirements

### Requirement: Work Lane Lifecycle Resolution

ETHOS SHALL keep routine mechanically determined lane lifecycle local and SHALL
record only exceptional interpretive judgments as evidence-bound Chronicle
`decision` events. Chronicle SHALL NOT become lease telemetry or a separate lane
resolution database.

#### Scenario: routine lifecycle remains local

- **WHEN** a lease is acquired, renewed, resumed, locally handed off, expires, or
  the same holder retires a clean mechanically proven landed lane
- **THEN** ETHOS uses ignored local coordination and postcondition receipts
- **AND** no tracked Chronicle decision is required.

#### Scenario: exceptional cleanup consumes prior accepted judgment

- **WHEN** orphan recovery, foreign retirement, non-mechanical supersession,
  disputed handoff, preserve, block, or irreversible deletion is requested
- **THEN** a separate owned governance Work Lane has already promoted a
  Chronicle decision binding policy, evidence, exact head, lane-incarnation
  digest, disposition, recovery plan, and target-observation digest
- **AND** cleanup recomputes the mutable target facts before its first
  destructive step
- **AND** any mismatch blocks cleanup and requires a new decision
- **AND** the decision authorizes an effect while postconditions alone prove what
  was actually removed.

#### Scenario: dirty or unknown work is preserved by default

- **WHEN** lane ownership, lease state, tracked/untracked contents, or recovery
  status is dirty, missing, ambiguous, or unknown
- **THEN** ETHOS preserves or blocks the lane instead of automatically deleting
  it
- **AND** irreversible deletion requires an accepted decision proving the exact
  target and why preservation is impossible or no longer required.

#### Scenario: break-glass reconciles after emergency action

- **GIVEN** a predeclared break-glass Commitment binds verified maintainer
  identity, exact target/head, reason, blast radius, expiry, preservation
  default, and postcondition plan
- **WHEN** an emergency command independently verifies those facts and acts
  before a new Chronicle decision can be promoted
- **THEN** it emits a digest-bound receipt and blocks later integration and
  publication
- **AND** a separate governance Work Lane promotes post-hoc judgment and
  reconciles residue before the block clears
- **AND** a self-supplied flag or holder string is insufficient.

#### Scenario: lane handoff is recorded as Chronicle resolution

- **GIVEN** a Work Lane handoff cannot be resolved by the normal local
  offer/accept protocol or becomes disputed
- **WHEN** an accepted exceptional judgment resolves the handoff
- **THEN** ETHOS records a Chronicle `decision` event binding the prior and next
  holder observations, evidence, exact head, lane-incarnation digest, and result
- **AND** routine local handoff remains ignored coordination and does not require
  tracked Chronicle telemetry
- **AND** the decision does not replace the active destination-local Lane Lease.

#### Scenario: orphan audit produces a decision, not a persistent orphan state

- **GIVEN** a Work Lane has missing, stale, ambiguous, or legacy holder evidence
- **WHEN** ETHOS audits the lane for exceptional closeout or cleanup
- **THEN** orphan-like facts remain observations requiring a separate accepted
  resolution decision before destructive action
- **AND** the durable outcome records `retire`, `preserve`, `block`, `handoff`, or
  `break_glass` together with exact target and recovery evidence
- **AND** dirty or owner-unknown lanes are preserved or blocked rather than
  automatically deleted.

#### Scenario: clean ownerless diverged source retires after semantic absorption

- **GIVEN** one clean ownerless source Work Lane has diverged because its
  historical evidence and carrier bytes differ from an independently accepted
  current-baseline implementation of its useful behavior
- **AND** a target-specific accepted Claim and Chronicle bind its exact ref,
  exact source head, semantic basis, recovery plan, and `lane_resolution/retire`
  policy
- **WHEN** the native resolver records and applies a fresh decision for that
  exact linked source with break-glass and irreversible confirmation
- **THEN** it SHALL re-observe the source before effect and emit a receipt after
  the exact retirement
- **AND** tree inequality, a missing lease, a preservation package, or an
  inventory entry alone SHALL NOT authorize retirement
- **AND** the authority SHALL NOT extend to another lane, a valid lease, remote
  mutation, or a hosted-provider claim.

### Requirement: Evolution Ledger Single Source Of Truth

ETHOS SHALL keep reviewed evolution records and active hypotheses in one
repository-truth ledger at `evolution/ledger.toml`.

#### Scenario: evolution commands and gates use one ledger

- **WHEN** ETHOS reports campaign hypotheses, validates schemas, audits release
  files, or projects assistant governance resources
- **THEN** those surfaces use `evolution/ledger.toml`
- **AND** documentation may explain evolution governance without storing a
  parallel ledger
- **AND** the ledger schema accepts typed evolution entries and hypothesis
  records in the same document
- **AND** non-campaign evolution entries bind at least one evidence ref and one
  decision ref
- **AND** active hypothesis proof, review, and decision refs resolve to known
  ETHOS command references or repository paths

### Requirement: Publish Falls Back To Local CI When Remote Is Unavailable

ETHOS SHALL treat hosted remote publication as an adapter projection and provide
a local-ci fallback evidence path when the configured Git remote is unavailable.

#### Scenario: publish probes remote availability without blocking local readiness

- **WHEN** `ethos publish --json` runs
- **THEN** the payload includes a read-only `remote_availability` fact
- **AND** remote probe failure, missing remote, or timeout remains advisory and
  does not create a required gap for local readiness
- **AND** the payload includes `local_ci_fallback` with evidence class
  `local_fallback`
- **AND** `local_ci_fallback.hosted_ci_status_claimed` is false

#### Scenario: local-ci fallback uses owner gates

- **WHEN** remote publication is unavailable or deferred
- **THEN** ETHOS recommends `tools/ci/scripts/run-local-ci.sh` as local
  fallback evidence
- **AND** that script invokes reusable owner gate scripts rather than restating
  hosted CI policy inline
- **AND** local fallback evidence does not claim hosted CI pipeline success

### Requirement: OpenSpec active carrier residue is visible across protected branch trees

ETHOS SHALL make active OpenSpec carriers visible when they remain in configured
protected branch Git trees. Current protected-role checkouts MUST block on active
carriers. Non-current protected branch residue MUST remain visible as an advisory
signal so stale protected refs can be repaired without misclassifying the current
accepted truth horizon.

#### Scenario: Current release root blocks active carrier residue

- **WHEN** repository audit runs on a checkout whose role is `release_root`
- **AND** `openspec/changes/<id>/` exists outside `archive/`
- **THEN** audit reports `openspec_active_change_unarchived:<id>:release_root` as a required gap

#### Scenario: Non-current protected branch residue is advisory

- **WHEN** repository audit runs on a different current role
- **AND** a configured protected branch tree contains `openspec/changes/<id>/` outside `archive/`
- **THEN** audit includes `openspec_protected_branch_active_change_unarchived:<branch>:<role>:<id>` in OpenSpec advisory gaps
- **AND** audit does not make the current checkout fail solely because of that non-current protected branch residue

### Requirement: Advisory governance signals are visible in reader views

ETHOS SHALL expose non-blocking advisory governance signals in report and orient
reader views without treating them as transition-blocking required gaps.

#### Scenario: Report exposes advisory signal count and layer

- **WHEN** `ethos report --json` runs
- **THEN** the summary includes `advisory_gap_count`
- **AND** `gap_layers.advisory_signals` lists non-blocking advisory gaps
- **AND** when there are advisory gaps but no required gaps the report remains
  `ok=true` and reports `state=advisory` rather than `state=ready`
- **AND** required gaps remain reserved for blocking transition failures

#### Scenario: Orient carries advisory readiness signals

- **WHEN** `ethos orient --json` runs with report payload available
- **THEN** orientation readiness includes advisory signal count and items
- **AND** the human orientation output can mention advisory signals without granting mutation authority

#### Scenario: Report exposes advisory signal count, layer, and bounded next actions

- **WHEN** `ethos report --json` runs
- **THEN** the summary includes `advisory_gap_count`
- **AND** `gap_layers.advisory_signals` lists non-blocking advisory gaps
- **AND** `gap_layers.advisory_signals.next_actions` lists bounded inspection or explanation actions for known advisory signals
- **AND** required gaps remain reserved for blocking transition failures

#### Scenario: Orient carries advisory readiness signals and actions

- **WHEN** `ethos orient --json` runs with report payload available
- **THEN** orientation readiness includes advisory signal count and items
- **AND** orientation readiness includes advisory next actions derived from report
- **AND** the human orientation output can mention advisory signals without granting mutation authority

#### Scenario: Report carries Work Lane coordination advisories

- **WHEN** `ethos report --json` runs and workspace status contains Work Lane coordination advisory gaps
- **THEN** the report summary includes those gaps in `advisory_gap_count`
- **AND** `gap_layers.advisory_signals.advisory_gaps` includes the Work Lane coordination advisories
- **AND** `gap_layers.advisory_signals.next_actions` routes to read-only coordination inspection commands
- **AND** top-level `next_actions` mirrors those advisory inspection commands when
  no blocking gap is present
- **AND** the advisories do not become report `required_gaps`

#### Scenario: Report carries Work Lane coordination blockers

- **WHEN** `ethos report --json` runs for a product or adopter profile and workspace status contains required Work Lane coordination gaps
- **THEN** those required coordination gaps appear in report `required_gaps`
- **AND** `gap_layers.coordination_risk.required_gaps` carries the required coordination gaps
- **AND** `gap_layers.coordination_risk.advisory_gaps` carries advisory coordination signals without making them required
- **AND** product and adopter profiles both surface required coordination gaps as blockers
- **AND** the scorecard remains read-only and does not authorize foreign Work Lane cleanup

### Requirement: Generated Evidence Boundary
ETHOS SHALL keep generated proof artifacts outside repository truth while making
latest-artifact writes deterministic enough for proof gates. Its product package
build gate and contributor-facing package-build command SHALL route output to
`build/artifacts/python` and SHALL clear that local-artifact home before the
build; they SHALL NOT create a redundant output-local `.gitignore`, because the
repository-level ignore owns the generated home; and they SHALL NOT use the
repository-root `dist/` default.

#### Scenario: Shared coverage evidence writes are serialized

- **WHEN** the Python owner test gate writes generated coverage evidence
- **THEN** it serializes cleanup, shard combination, and latest XML writes for
  the shared coverage evidence directory
- **AND** the serialization mechanism does not create a new repository truth
  store
- **AND** local fallback evidence does not claim hosted CI success.

#### Scenario: An interrupted coverage writer does not block future proof forever

- **GIVEN** the generated coverage writer lock records a process identity whose
  PID and start fingerprint no longer identify a live process
- **WHEN** a later Python owner test gate starts for that same evidence home
- **THEN** it reclaims only that dead-owner lock before acquiring the writer
  boundary
- **AND** it never preempts an unknown or live owner
- **AND** an unrecoverable lock fails after a configured bounded wait with the
  lock path and observed owner identity, rather than waiting indefinitely
- **AND** lock metadata remains ignored generated state, not repository truth.

#### Scenario: Package build writes to the semantic artifact home

- **WHEN** the product full proof executes its package build gate or a
  contributor follows the documented package-build command
- **THEN** `uv build --all-packages --out-dir build/artifacts/python --clear
  --no-create-gitignore` is the invoked command
- **AND** generated package artifacts remain disposable local state under
  `build/artifacts/python`
- **AND** concurrent workspace package builds do not race on an output-local
  ignore marker
- **AND** the invocation does not create or authorize repository-root `dist/`
  output.

### Requirement: Forge provider projections preserve ETHOS repository truth

ETHOS SHALL support GitHub and GitLab as hosted forge providers that project the
same repository governance contract without changing `status -> plan -> prove ->
land -> publish` semantics. GitLab and GitHub SHALL be independent remote planes
with equal `repository`, `ci_cd`, and `publication` capabilities; their distinct
organization-collaboration and public-distribution roles SHALL NOT create
precedence, failover, or replacement semantics. Provider CI SHALL accept only
`dev`, `main`, and `submit/*`; the local-only `candidate/dev` and every `work/*`
branch SHALL be excluded.

#### Scenario: Dual provider templates mirror one gate contract

- **WHEN** the provider templates and projections are inspected
- **THEN** GitHub and GitLab SHALL include `dev`, `main`, and `submit/*`
- **AND** neither SHALL include `candidate/dev`
- **AND** each SHALL invoke repository-owned gate scripts or `ethos ...`
  command surfaces rather than duplicating policy inline.

#### Scenario: Local candidate is excluded from hosted providers

- **WHEN** the provider templates and projections are inspected
- **THEN** GitHub and GitLab SHALL include `dev`, `main`, and `submit/*`
- **AND** neither SHALL include `candidate/dev`
- **AND** each SHALL invoke repository-owned gate scripts or `ethos ...`
  command surfaces rather than duplicating policy inline.

#### Scenario: Local provider emulation remains local evidence

- **WHEN** a GitHub or GitLab provider projection is emulated locally
- **THEN** the evidence SHALL name the local emulator evidence class
- **AND** it SHALL record the provider, template or projection path, command,
  start and end Git head, dirty state, return code, and changed-scope summary
- **AND** it SHALL record whether the Git head stayed stable for the emulator run
- **AND** observation modes such as `doctor`, `list`, and `dry-run` MAY report a
  missing optional emulator binary as bounded local evidence with
  `tool_available=false` without claiming hosted provider status
- **AND** materializing emulator run modes SHALL fail closed when the required
  emulator binary is unavailable
- **AND** normal emulator run modes SHALL refuse untracked files by default
  because provider materialization can omit them
- **AND** it SHALL explicitly state that hosted provider status was not claimed.

### Requirement: Equal dual-remote publication topology

ETHOS SHALL model publication as one local verification/install layer and two
independent remote targets: GitLab organization collaboration and GitHub public
distribution. Each target SHALL expose equal `repository`, `ci_cd`, and
`publication` capabilities; no target SHALL become a fallback or authority
above the other. Remote admission and hosted CI SHALL allow only `dev`, `main`,
and `submit/*`; `candidate/dev` and every `work/*` branch SHALL remain local.
`ethos publish` SHALL observe declared targets independently without pushing or
claiming hosted CI success. Compact declarations SHALL retain valid former
verbose remote records for adopter compatibility.

#### Scenario: explicit remote admission preserves local candidate isolation

- **WHEN** pre-push admission receives a named declared target and `candidate/dev`
- **THEN** it SHALL reject the destination before proof admission
- **AND** it SHALL emit `publication_candidate_branch_remote_forbidden:candidate/dev`.

#### Scenario: independent remote observations remain no-push

- **WHEN** `ethos publish` observes GitLab and GitHub
- **THEN** it SHALL expose each target separately
- **AND** `remote_push` SHALL remain `not_performed`
- **AND** hosted CI status SHALL remain unclaimed.

#### Scenario: valid verbose declaration remains accepted

- **WHEN** an adopter supplies valid `[[publication.remote]]` records
- **THEN** ETHOS SHALL resolve the same named GitLab and GitHub targets
- **AND** it SHALL retain equal capability and explicit-admission validation.

### Requirement: Tool adoption remains profile and adapter scoped

ETHOS SHALL admit mature tooling through contracts, profiles, adapters,
projections, and gates instead of making adopter tools product ontology.

#### Scenario: Planned tools do not become active gates by catalog presence

- **WHEN** a tool is listed in `system/tools.toml` with `planned = true`
- **THEN** ETHOS SHALL NOT report it as an active quality floor
- **AND** activation SHALL require a config owner, reusable execution surface,
  CI or hook projection, and proof coverage.

#### Scenario: Optional method packs remain replaceable

- **WHEN** an agent uses Superpowers or another method pack to plan or review a
  change
- **THEN** the method pack MAY be recorded as execution context
- **AND** repository truth SHALL still require promoted source, docs, OpenSpec,
  claim, evidence, or command proof
- **AND** missing method-pack availability SHALL NOT block ETHOS repository
  governance when equivalent evidence discipline is satisfied.

### Requirement: OpenSpec customization stays official-compatible

ETHOS SHALL apply official OpenSpec validation before ETHOS-specific schema,
capability profile, claim binding, evidence, and archive lifecycle checks.

#### Scenario: ETHOS validates capability metadata after official OpenSpec

- **WHEN** an OpenSpec change or accepted spec is validated for ETHOS governance
- **THEN** official OpenSpec validation SHALL run first
- **AND** ETHOS SHALL validate repo-local capability profiles, proposal facets,
  claim carriers, evidence refs, and archive closeout without replacing official
  OpenSpec syntax or semantics.

#### Scenario: clean ownerless landed residual retires after exact accepted absorption

- **GIVEN** one named linked Work Lane is clean, has no active lease, and its
  exact head is a strict ancestor of the current accepted branch
- **AND** an accepted target-specific Claim and Chronicle bind that source ref,
  source head, accepted absorption basis, and a recovery plan
- **WHEN** the native resolver records and applies a fresh
  `lane_resolution/retire` decision with break-glass and irreversible
  confirmation
- **THEN** it SHALL re-observe the named source's ref, head, linked binding,
  cleanliness, lease state, Chronicle bytes, and accepted control state before
  any effect
- **AND** it SHALL remove only that source's branch and worktree and write a
  receipt
- **AND** an inventory, expired lease, graph relation, or historical evidence
  alone SHALL NOT authorize retirement of another lane.
