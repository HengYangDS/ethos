---
subject: ethos:command-plane
role: reference
state: canonical
relations:
  canonical_for: public commands
---

# Command Plane

Status: canonical.

Purpose: define the public `ethos ...` command vocabulary and keep retired root
commands out of normal workflow docs.

See also: [Quickstart](../start/quickstart.md), [Docs Registry](../governance/docs-registry.md),
and [Glossary](glossary.md).

Public workflow commands:

```bash
ethos status
ethos plan
ethos prove
ethos land
ethos publish
```

`ethos orient` is a read-only first-glance orientation view over `status` and
`report`: it tells a human or agent where it is, what it may do, which foreign
Work Lanes and unbound Work Lane refs are visible, what remains gapped, and
which command should run next. It is a projection (`truth_boundary =
repository-reader-view`, `mints_truth = false`), not a transition verb and not a
truth store. Its current HEAD field is the repository HEAD that `status` reports at
the top level (resolved via `git rev-parse HEAD`, so it is correct even on a detached
HEAD); a workspace-status branch binding serves only as a fallback.

`ethos report` is the read-only scorecard over that workflow. It is not a
transition command:

```bash
ethos report
ethos report --json
ethos report --json --compact
```

Use `--json --compact` when an agent, CI summary, or constrained context window
needs the same top-level verdict, summary, required gaps, and next actions
without the heavyweight audit bodies carried by full JSON. Compact report output
keeps machine-stable counts and score data; it does not mint a separate truth
source or bypass `ethos prove` / `ethos land`.

This is the command grammar. `status`, `plan`, `prove`, `land`, and `publish`

The same transition command semantics apply in the product repository and in adopted repositories.
are the transition verbs; `report` is the payoff view. Every maintainer,
quality, parity, assistant, playbook, fleet, hook, lane, or docs command is a
domain lens or repair surface over that grammar. It must project a kernel
object, expose its boundary, and reduce its decision back to one of the
transition questions rather than becoming a parallel command plane.

`ethos plan --changed --json` reports the current change scope under
`data.changed_paths`. In a dirty accepted-root or non-lane checkout, this is the
Git porcelain dirty path set. In a Work Lane, it is the union of committed paths
changed from the configured candidate branch to `HEAD` and any local dirty paths.
A clean Work Lane can therefore still produce a non-empty changed plan when it
has committed lane delta waiting to prove or land.

The npm launcher exposes the same root command:

```bash
npm run ethos -- --version
```

Maintainer/reference commands remain under `ethos ...`. Retired root commands
are not compatibility surfaces.

Setup/onboarding commands:

```bash
ethos adopt --profile python --dry-run --json
ethos adopt --profile python --apply --authorize --expect-head <git-head> --json
ethos init --profile gitlab --dry-run --json
ethos doctor
```

`ethos doctor --json` also exposes host-local command wrapper diagnostics. If
`PATH` resolves `ethos` to a fixed-root wrapper, the report records
`data.host_wrapper.advisory_gaps=["host_wrapper_fixed_root"]` and recommends an
explicit `ETHOS_ROOT` or a package-bound invocation from the target checkout.
This is projection diagnosis only; repository truth remains the resolved Git
worktree root and the command payload's runtime binding.

Quality and governance:

```bash
ethos quality command-registry
ethos quality command-surface
ethos quality command-examples
ethos quality format-policy
ethos quality code-size
ethos quality module-layout
ethos quality projection-drift
ethos quality evidence-freshness
ethos quality coupling-audit
ethos quality asset-policy
ethos quality docs
ethos quality proof-policy
ethos quality tool-profiles
ethos quality package-ontology
ethos quality enterprise-readiness
ethos quality claims
ethos quality docs-registry
ethos quality docs-topology
ethos quality generated-artifacts
ethos quality gates
ethos quality provenance
ethos quality schemas
ethos quality commits
ethos quality release
ethos quality release-policy
ethos quality release-attestation
ethos quality sbom
ethos quality standards
ethos quality projection-drift
ethos audit
ethos audit --mode shape
ethos audit --mode deep
ethos openspec --lifecycle
ethos prove --execute
ethos prove --full --execute
ethos prove --expect-head <git-head>
ethos prove --scope proof-kernel
ethos prove --scope proof-kernel --host --probe
ethos campaign hypotheses
ethos campaign closeout --adopter <adopter-id> --target <repo>
ethos intake status
ethos intake mine
ethos hook admit pre-tool <paths> --editor-root <worktree-path> --require-editor-root
ethos hook admit pre-run --command <shell-command>
ethos hook admit post-write <paths> --editor-root <worktree-path>
ethos parity ledger
ethos parity gaps --adopter <adopter-id>
ethos parity gaps --adopter <adopter-id> --target <repo>
ethos parity shadow --target <repo>
ethos parity shadow --adopter <adopter-id> --target <repo>
ethos report
ethos docs
ethos explain <gap-or-signal>
```

`ethos quality docs-topology --json` audits the Minimal Semantic Documentation Topology Contract. It requires the minimal semantic common docs kernel (`docs/README.md`, `docs/decisions/`, `docs/evidence/`, `docs/history/`, and `docs/reference/`) while forbidding `current`/`future` roots such as `docs/current/` and `docs/future/`. Product or adopter roots such as `docs/architecture/`, `docs/concepts/`, `docs/start/`, `docs/governance/`, `docs/plans/`, and `docs/research/` are extensions, not required kernel lanes. `ethos fleet retirement-readiness --target <repo> --root <product> --json` uses the same audit as a blocking embedded-backend retirement gate.

`ethos quality enterprise-readiness --json` is an aggregate closeout gate for
general-purpose enterprise use. It composes existing owner gates for product
boundary neutrality, role-based contributor policy, semantic docs topology,
generic parity, release/distribution boundaries, claim carriers, governance
kernel, and the shared governed-repository context. It is read-only: remote
publication and foreign Work Lane cleanup remain separate states requiring their
own authority.

`ethos quality governance-kernel --json` is the independent guard for
Isomorphic Governance. It checks the live `governance_context`, the
product/adopter governance profile isomorphism, the product docs that make the
contract discoverable, and the generic adoption scaffold. A clean verdict means
product and adopted repositories share the same kernel and same transition
command semantics; only profile and adapter bindings may vary.

`ethos quality generated-artifacts --json` audits the Generated Artifact Topology Contract. It routes repository paths into declarative interface, local runtime, generated output, curated evidence, governed-docs, source-tree, package-metadata, and review-required classes; it blocks tracked generated drift outside `.cache/local-state/`, `.ethos/state/`, `build/runtime/tool-cache/`, `build/runtime/work/`, `build/ethos/`, `build/evidence/`, and `build/artifacts/`, while keeping `.config/ethos/` declarative-only and requiring curated evidence promotion under `docs/evidence/`, `evidence/chronicle/`, or `evidence/parity/`. Promotion from `build/evidence/` or `build/ethos/` requires an explicit reviewed summary that binds command, scope, verifier, digest, and HEAD; runtime caches and local artifacts are regenerated, not promoted. The JSON also includes lifecycle classes (`runtime_cache`, `machine_evidence`, `local_artifact`, `curated_evidence`) and an `entrypoint_audit` that verifies active producer entrypoints route pytest, Ruff, import-linter, package builds, and local provider emulator state to semantic homes before they can recreate root or flat generated residue.

`ethos quality evidence-freshness --json` is profile-aware. Its summary reports the active profile durable evidence root. The product-default `evidence/` root and non-docs custom evidence roots use the strict kernel layout (`claims/`, `chronicle/`, `parity/`). A profile-declared `docs/evidence` root is audited as curated profile evidence so existing adopter delivery or rollback evidence trees can remain under `docs/evidence/` without becoming generated output or product-owned adopter fixtures.

`ethos quality module-layout --json` audits semantic subpackages, suffix-flat
modules, import-only facades, package-root submodule imports, flat-directory
growth, and module-layout ratchet baselines. A clean verdict means no new or
stale layout gaps escaped the configured ratchet; it does not mean historic debt
is absent. Existing baseline debt is explicit in `summary.debt_count` and
`data.ratchet`, including `state`, `debt_kinds`, `baseline_gap_count`,
per-kind baseline counts and limits, and the next action to shrink baselines as
semantic subpackages remove debt.

Agent projections:

```bash
ethos assistants doctor
ethos assistants check-projections
ethos assistants mcp-manifest
ethos assistants mcp-server
```

Playbook routing:

```bash
ethos playbooks check
ethos playbooks check --mode v2-strict
ethos playbooks route
ethos playbooks route --changed
ethos playbooks route --changed --mode v2-strict
```

Work Lane admission:

```bash
ethos lane status
ethos lane candidate --path <candidate-worktree-path> --apply --expect-head <git-head>
ethos lane candidate --refresh-from-accepted --apply --authorize --expect-head <git-head>
ethos lane start <name> --path <worktree-path> --holder-ref <holder-ref> --claim-id <claim> --apply
ethos lane refresh-base --apply --authorize --expect-head <git-head>
ethos lane bind-claim --claim-id <claim> --apply
ethos lane prewrite <paths> --editor-root <worktree-path> --require-editor-root
ethos lane lease renew --branch <branch> --holder-ref <holder-ref> --lease-id <lease-id> --epoch <epoch> --expect-head <head> --apply
ethos lane handoff export --branch <branch> --holder-ref <holder-ref> --target-holder-ref <holder-ref> --lease-id <lease-id> --epoch <epoch> --expect-head <head> --context-file <path> --apply
ethos lane resolution decide --branch <branch> --disposition <block|preserve|retire> --reason <why> --evidence-ref <evidence> --chronicle-ref <accepted-chronicle> --recovery-plan <plan> --decision-path <build-artifact> --apply
ethos lane resolution apply --decision-path <build-artifact> --apply
ethos lane retire landed --branch <work-lane-branch> --expect-head <work-lane-head> --apply
ethos lane retire superseded --branch <work-lane-branch> --expect-head <work-lane-head> --absorbed-by <accepted-head> --reason <why> --authorize --apply
ethos lane retire unbound --branch <work-lane-branch> --expect-head <git-head> --reason <why> --authorize --apply
```

When `--root` is omitted, CLI commands resolve the current Git worktree root
from `cwd`. A Work Lane subdirectory therefore binds to that Work Lane, not to
the accepted-root checkout or a host launch directory. Product-repository
prewrite also reports `data.runtime_binding` and blocks when the command runner,
schema source, and audited root are not the same product checkout.

`ethos status --json` and `ethos lane status --json` expose the configured role
contract under `data.role_policy` and role-policy branch bindings under
`data.branch_bindings`. The `role_policy` field is the configured product
contract for branch names, prefixes, and semantic role order. The role order is
release_root -> accepted_root -> candidate -> work_lane -> submit_lane. Exact
branches and prefixes are configurable, but the role vocabulary is product
state. Bindings are ordered by this semantic role order before branch name. Each
binding reports
`worktree_binding` as product state: `current`, `linked`, `unbound`, or
`absent`. Work Lane bindings also report `claim_id` and `claim_binding` as
boundary evidence. Missing claim binding does not block ordinary local work, but
trust-bearing closeout reports it as a governance gap when a lane is otherwise
ready to land. Host adapters may project linked worktrees as host-specific
navigation commands, but the product payload does not expose host labels or
navigation actions as truth; adapter UI text is not product state.
Both commands include a `schema_validation` diagnostic for the live
workspace-status payload. The diagnostic validates `data` against
`workspace-status.schema.json`; the validation result is not embedded in `data`
so the workspace-status object remains schema-valid.
`ethos status --json` and `ethos lane status --json` also lift
first-glance coordination state into `summary.foreign_work_lane_count`,
`summary.unbound_work_lane_count`, `summary.missing_lease_count`,
`summary.dirty_foreign_work_lane_count`, `summary.coordination_advisory_count`,
`summary.coordination_blocking`, and `summary.coordination_next_action`.
Those summary fields are derived visibility signals for humans and agents; they
do not replace `data.coordination`, do not add cleanup authority, and do not
change whether a coordination signal is advisory or required.
`ethos orient --json` projects `data.coordination.next_action` into
`data.orientation.coordination.next_action` for first-glance coordination
guidance. That field is distinct from the top-level transition `next_actions`:
it explains how to inspect coordination signals, not which transition command
must run next. Human `ethos orient` output renders coordination as one concise
line when coordination signals are present.
The `data.closeout_support` object reports whether the current checkout can land
to the configured candidate branch, which target path would be updated, which
lease holder is bound when known, which claim is bound when known, and which
mutation gap blocks closeout. The holder contract is `holder_ref`; predecessor
owner fields are storage or migration diagnostics only and are never authoritative.
The `data.coordination` object reports foreign Work Lanes with scope-aware
coordination state and unbound Work Lane refs with their relation to accepted
truth. Plain presence remains advisory through `advisory_gaps` such as
`foreign_work_lane_present`, `unbound_work_lane_ref_present`, or
`work_lane_missing_lease:<branch>`. Candidate integration from a Work Lane is
blocked only when a required coordination gap is present, such as unknown
current scope. Unknown foreign scope and same-file or ancestor-scope overlap are
surfaced as advisory contention through `coordination_gap:*` entries, so Git's
fast-forward land remains the mutation arbiter without serializing unrelated
agents that share a directory. Across product and adopter profiles,
`ethos report --json` mirrors status-required coordination gaps into report
`required_gaps` and `data.gap_layers.coordination_risk.required_gaps`; advisory
coordination signals stay advisory, classify into the same invalid-state
taxonomy, and never grant cleanup authority. If the scorecard has no blocking
`required_gaps` but does have advisory signals, the top-level command remains
`ok=true` while reporting `state=advisory`; in that state, top-level
`next_actions` mirror the bounded advisory inspection or repair actions instead
of implying that full proof alone will erase the advisory layer.
Each `foreign_work_lanes[]` item exposes a non-authoritative `action_preview`:
the only candidate action is `observe`, blocked actions include `write`, `land`,
and `retire`, and the preview states `mints_authority=false` and
`recheck_required=true`. Productized leases use concrete holder references such
as `agent:codex:thread:<id>` rather than provider labels such as `codex`; actual
mutation is independently re-admitted.
A landed dirty lane is not retire-ready residue: it reports
`closeout_disposition=landed_dirty`,
`residue_state=unpreserved_worktree_delta`, and a `next_action` requiring the
owner to preserve or intentionally discard the dirty worktree delta before
retirement. A clean claim-bound lane already absorbed by accepted truth reports
`closeout_disposition=retire_ready` and a head-bound `next_action` shaped as
`ethos lane retire landed --branch <branch> --expect-head <head> --apply --json`;
the command is still authority-gated by the lane holder or break-glass policy.
Handoff, retire, preserve, block, orphan audit, and break-glass outcomes are
recorded as evidence-bound Chronicle `lane_resolution` events when they become
durable judgments; they are not a separate lane-resolution truth store. This is
a product read model, not a host message bus: assistant hosts, MCP, editor hosts,
and CI adapters all see the same repository fact and must route mutation through
their own owned lane.
`ethos lane start --json` returns `data.worktree` in apply mode. That object
uses the same `worktree_binding` vocabulary as status output, so hosts can
project the new Work Lane without treating adapter UI text as product truth.
Start admission requires both the accepted root and the candidate worktree to be
clean. A dirty candidate returns `candidate_worktree_dirty` and does not create
a Work Lane.
`ethos lane bind-claim --claim-id <claim> --apply --json` updates an existing
Work Lane lease with a trust-bearing claim id. It is the handoff path for lanes
started before a claim id was known; it does not create a lease for raw
worktrees and does not promote lane presence into repository truth.
`ethos lane refresh-base --json` checks whether the current clean Work Lane is
based on the configured candidate branch. If the candidate train has advanced,
dry-run output reports `state = "ready_to_refresh_base"` and apply mode requires
`--authorize` plus `--expect-head` before replaying the current lane onto the
candidate branch. `ethos land --json` uses the same check before apply: a stale
lane returns `candidate_base_stale` and the exact `ethos lane refresh-base`
command instead of waiting for `land --apply` to fail. If replay conflicts only
on tracked parity shadow evidence (`evidence/parity/*-shadow.json`), refresh-base
keeps the candidate projection, completes the replay, and returns
`base_refreshed_projection_stale` with `projection_refresh_required`,
`projection_refresh_gaps`, `stale_projection_paths`, and next actions to
regenerate parity evidence before head-bound proof. Any non-projection conflict
still aborts as `refresh_base_failed`.
`ethos lane candidate --refresh-from-accepted --json` checks whether a clean
candidate train can be reset to the accepted root. Apply mode requires
`--authorize` plus `--expect-head`; it is the recovery path when accepted-root
closeout reports `candidate_diverged_from_accepted`. The apply path is a
sanctioned ETHOS candidate ref move: it carries the scoped official ref-move
context needed by the reference-transaction hook while still failing closed on
stale heads, dirty candidate worktrees, or reset errors.
`ethos lane retire landed` lists landed Work Lanes without mutation by default.
Apply mode requires an explicit Work Lane branch so cleanup cannot accidentally
remove another active agent's worktree. Leased lanes are exact holder, lease,
generation, and HEAD bound. When the invocation holder does not match, the JSON reports
`foreign_work_lane_retire_authority_required`, whether an actor is bound, the
required holder, and a bounded next action to bind the holder or obtain handoff.
`ethos lane retire superseded` is the holder-bound cleanup path for clean
linked Work Lanes whose semantic truth has already been absorbed into the current
accepted root but whose stale branch content must not be landed. It is dry-run by
default; apply mode requires `--authorize`, `--expect-head`, `--absorbed-by` equal
to the current accepted head, a non-empty `--reason`, compatible holder binding,
and accepted-root tree content that matches the lane's changed paths, then
deletes `refs/heads/<branch>` with a head-bound ref transaction and removes the
previously verified-clean linked worktree. If the worktree removal fails after
ref deletion,
ETHOS attempts to restore the ref before reporting the blocked cleanup. It does
not replace `ethos land` or `ethos lane retire landed`; it closes a distinct superseded
linked-lane residue state.
`ethos lane retire unbound` is the maintainer cleanup path for local unbound
Work Lane refs that already appear in `data.coordination.unbound_work_lane_refs`.
It is dry-run by default; apply mode requires `--authorize`, `--expect-head`,
and a non-empty `--reason`, then deletes `refs/heads/<branch>` with a
head-bound Git ref transaction. It does not replace `ethos land` or
`ethos lane retire landed`, and it does not remove linked worktrees.
The standard local lifecycle is product state even when a host provides its own
presentation: create the Work Lane through `ethos lane start`, attach claim
evidence with `ethos lane bind-claim` when needed, refresh the lane base only
through `ethos lane refresh-base`, land only through `ethos land`, retire
landed lanes through `ethos lane retire landed`, retire absorbed linked-lane
residue through `ethos lane retire superseded`, and retire unbound residue refs
through `ethos lane retire unbound`. Raw Git
worktree creation is an observable repository fact, but it is not admitted as
the standard ETHOS workflow state because it has no ETHOS lease or claim
boundary. `ethos orient --json` provides a derived reader view for human/agent discoverability;
`ethos status --json` remains the pure machine contract for role, dirtiness,
branch bindings, candidate state, and coordination.

Hook admission:

```bash
ethos hook admit context --expected-root <repo-root>
ethos hook admit pre-tool <paths> --editor-root <worktree-path> --require-editor-root
ethos hook admit pre-run <paths> --command <shell-command> --editor-root <worktree-path>
ethos hook admit post-write <paths> --editor-root <worktree-path>
```

`ethos hook admit --json` is the product decision endpoint for write-capable
hosts. It reports the hook layer, target root, checkout role, editor root,
target paths, command-risk classification when applicable, the underlying
prewrite admission payload when applicable, and a decision of `allow`, `block`,
or `fuse`. `pre-tool` and mutation-risk `pre-run` decisions bind to
`prewrite_guard`; `post-write` fuses on protected-root dirty state or unexpected
tracked paths. Git hooks and CI remain fallback/proof layers, not the mandatory
choke point for direct tracked writes.

Mutation readiness is explicit:

```bash
ethos land --apply --authorize --expect-head <git-head>
ethos land --closeout --apply --authorize --expect-head <accepted-head> --root <accepted-root>
ethos publish --apply --authorize --expect-head <git-head>
```

Those commands still report readiness in the current implementation; remote
publication remains an adapter responsibility. `publish --json` reports
`summary.remote_push = "not_performed"`,
`summary.remote_publication_state = "deferred"`, and
`data.publication.remote_state = "deferred"` while still exposing the configured
submit branch plan. Remote reachability is separate and appears under
`data.remote_availability.state` and `data.publication.remote_availability.state`.
The local fallback package also reports
`data.local_ci_fallback.evidence_status` and
`data.publication.fallback_evidence.evidence_status`, binding fallback evidence to
the current HEAD when `build/evidence/local-ci/fallback.json` exists. Missing,
stale, or invalid fallback evidence remains a local-evidence action; it never
claims hosted CI success or remote publication.
`land --apply` from an admitted Work Lane advances the configured candidate
branch; it does not advance the accepted root.
Accepted-root closeout is also an ETHOS mutation. The current ETHOS runner may
execute the closeout command above against the clean accepted-root checkout, audits
the configured candidate worktree before mutation, and then fast-forwards the
accepted branch from the candidate branch. Raw Git merge commands are repository
operations, not the ETHOS product mechanism.
When the accepted root already matches the configured candidate head, closeout
reports `state = "accepted_current"` and `closeout_bootstrap.state = "current"`;
the next action is `ethos publish`, not another closeout command. Authorized
apply mode is a no-op in that state and does not require proof for a head that is
already accepted.

`ethos campaign closeout --json` is the campaign-mode local closeout report. It
does not mutate Git and does not push. The output aggregates workspace
`closeout_support`, trust closeout, intake projection state, evolution
state, release policy, parity backlog, planned shadow parity execution, and
publish readiness under `data.packages`. The `trust_closeout` package composes
claim envelopes, promotion readiness, executed proof evidence, and Work Lane
claim binding. The `intake_projection` package records provider state as
projection evidence with `repository_truth=false`; it does not promote intake
provider state into repository truth. `ethos intake mine --json` is a
read-only repository read model: it projects signals into intake envelopes
and issue candidates with `auto_raise_allowed=false` and
`auto_dispatch_allowed=false`, so signal discovery cannot authorize issue
creation, Work Lane mutation, or agent dispatch by itself.
`ethos campaign status --json` reports campaigns as strict serial sequences of
OpenSpec-backed Work Lanes. Each `data.campaigns[].steps[]` item carries
`ordinal`, `depends_on`, `openspec_change`, `work_lane`, `claim_id`, and
`closeout`; `data.campaigns[].lane_topology` reports the serial edges, current
active step, and next planned step. A campaign coordinates many lane closeouts;
it is not itself the executable lane.
`data.remote_publication.state = "deferred"` is expected while the remote
publication adapter is unavailable.
Parity refresh is likewise command-bound. When tracked shadow evidence is
missing, stale, or target-mismatched, `ethos parity gaps --json` and
`ethos parity shadow --json` expose a `parity_evidence_refresh` package with the
adopter id, product root, explicit target when supplied, blocking gaps, and the
exact refresh command. For a distinct adopter Git repository that command includes
`--root <product-root>` and `--target <adopter-repo>`: product identity remains
rooted in ETHOS while the tracked `<durable-evidence-root>/parity/<adopter-id>-shadow.json`
file is read and written under the adopter repository. The durable evidence root
is resolved from the owning repository profile, so an adopter may use
`docs/evidence/parity/` while generic/self parity continues to use the product
profile's durable evidence root. If no target is supplied, ETHOS does not reuse a
target path from stale evidence as the next action.

Local shadow parity verifies the command surfaces needed for local governance,
including `land` and `quality command-surface`. It does not execute `publish`:
publication readiness deliberately probes remote availability, while remote
publication remains a separate deferred state. The command-surface gate still
verifies that `publish` is publicly available.

ETHOS primary command payloads use a governed repository contract. Every
primary command result (`status`, `plan`, `prove`, `land`, `publish`, `orient`,
and `report`) exposes a top-level `governance_context` so consumers can read the
same command semantics without inferring product truth from a special branch,
private command plane, or command-specific payload shape. Domain payloads may
repeat the same context when their nested report already owns it, but pure data
contracts such as `status.data` remain schema-valid source payloads rather than
being polluted by envelope metadata. The context records the profile, repository
subject, kernel chain, shared transition commands, reader-view commands,
scorecard commands, repository truth boundary, and profile or adapter boundary.
`shared_commands` and `transition_commands` list the five-command transition
loop: `ethos status`, `ethos plan`, `ethos prove`, `ethos land`, and
`ethos publish`. `reader_view_commands` lists the read-only first-glance view:
`ethos orient`. `scorecard_commands` lists the read-only payoff view:
`ethos report`. `ethos report --json` projects required gaps through
repository-neutral layers: `governance_audit` for the active repository governance
verdict, `capability_parity` for migration or adopter parity, and
`playbook_projection` for assistant-facing projection proof. Advisory signals
are a visible, non-blocking layer: `ok=true` means they do not block transitions,
while `state=advisory` distinguishes them from a fully ready scorecard. Each
layer exposes
`invalid_states`, a reduction of its `required_gaps` onto the governed taxonomy in
`system/invalid_states.toml`; the top-level `data.invalid_states` is the same
projection across all reported layers. Its summary uses `governance_gap_count`
for active repository governance gaps and `parity_pending_count` for capability
parity backlog.

The invalid-state taxonomy is not a second lifecycle and does not add a sixth
transition command. It is a read-only explanation vocabulary for failed
preconditions in the kernel chain and boundary substrate. `ethos explain <gap-or-signal>
--json` projects one gap or advisory signal into that taxonomy and returns the category id, node,
question, summary, and taxonomy source. A gap that cannot classify is reported as
`unclassified_invalid_state`, which means the command plane emitted an ungoverned
failure mode that must be folded back into the taxonomy or renamed to an existing
precondition.

Repository governance modes are explicit. `shape` is the daily fast path for product
shape, schemas, claims, command vocabulary, and OpenSpec layout. `deep` includes
official OpenSpec CLI validation and is required for release or archive proof.
`ethos openspec --lifecycle --json` adds ETHOS lifecycle carrier review:
active changes need proposal, design, tasks, delta specs, and an active claim
binding in addition to official OpenSpec validation.

Proof states are execution-depth states. `ethos prove --json` is readiness and
reports `state=ready` with `executed=false` when planning and static admission
pass. `ethos prove --execute --json` can report `state=proven` because every
selected gate records an exit code. `ethos prove --full --json` without
execution is intentionally `gapped` with `full_proof_requires_execute`.
`ethos prove --scope proof-kernel --json` is a compatibility contract for
adopters whose existing governance invokes scoped proof-kernel checks; scope is
proof-boundary metadata and does not override `--gate`, `--full`, or profile gate
selection. `--host --probe` records an optional host-local readiness boundary in
`data.host_probe`; it does not satisfy repository proof, hosted CI, publication,
or adopter retirement readiness by itself.

`ethos quality coupling-audit --json` reports product-semantic hard bindings,
mandatory governance dependencies, native protocol bindings, product-toolchain
toolchain bindings, profile or adapter bindings, historical evidence, and
test-fixture coupling boundaries through `data.binding_registry`. The
`binding_registry` field is the machine-readable binding classification
contract. It treats Git, worktrees, refs, branch roles, and the Work Lane
lifecycle command contract as product semantics; OpenSpec as mandatory
governance; command JSON, schemas, TOML, JSONL, and ignored SQLite state as
native protocols; and hosted forge, editor, model, and current proof toolchain
terms as non-product-semantic bindings.
The branch role policy entry also reports its configuration source, config
keys, default-policy state, semantic role order, and configured patterns so
release_root, accepted_root, candidate, work_lane, and submit_lane remain
distinct configured roles rather than hard-coded branch names.
The registry also names the official OpenSpec CLI, uv workspace orchestration,
Hatchling build backend, pytest, Ruff, the configured GitLab release profile,
MCP/ACP protocol adapters, the npm launcher distribution adapter, historical
evidence, and provider fixtures under their explicit binding layers.

Skills V2 command payloads expose normalized registry and package evidence.
`ethos playbooks check --json` runs the current product proof mode; the explicit
`ethos playbooks check --mode v2-strict --json` spelling is equivalent. The
proof requires activation ownership metadata, path coverage, proof obligations,
package manifests, digest agreement, and official-quality `SKILL.md` content.
Historical playbook payloads remain archive or adopter evidence, not current
route contract. `ethos playbooks route --changed --json` selects records via the
explicit `changed-scope` route and path-glob metadata.

`ethos report --json` includes `data.scorecards[]` with the `skills-v2`
scorecard and `data.gap_layers.playbook_projection` for blocking Skills V2
gaps. `ethos prove --execute --gate playbooks-v2 --json` executes the strict
playbook gate. `ethos quality projection-drift --json` reports package drift,
the normalized registry digest, the expected registry digest, the playbook
generator digest, the expected generator digest, and activation input digests.
