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
```

This is the command grammar. `status`, `plan`, `prove`, `land`, and `publish`
are the transition verbs; `report` is the payoff view. Every maintainer,
quality, parity, assistant, playbook, fleet, hook, lane, or docs command is a
domain lens or repair surface over that grammar. It must project a kernel
object, expose its boundary, and reduce its decision back to one of the
transition questions rather than becoming a parallel command plane.

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
ethos quality projection-drift
ethos quality evidence-freshness
ethos quality coupling-audit
ethos quality asset-policy
ethos quality docs
ethos quality proof-policy
ethos quality tool-profiles
ethos quality package-ontology
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
ethos hook admit pre-tool <path> --editor-root <worktree-path> --require-editor-root
ethos hook admit pre-run --command <shell-command>
ethos hook admit post-write <path> --editor-root <worktree-path>
ethos parity ledger
ethos parity gaps --adopter <adopter-id>
ethos parity gaps --adopter <adopter-id> --target <repo>
ethos parity shadow --target <repo>
ethos parity shadow --adopter <adopter-id> --target <repo>
ethos report
ethos docs
ethos explain <gap-or-signal>
```

`ethos quality docs-topology --json` audits the Minimal Semantic Documentation Topology Contract. It requires the minimal semantic common docs kernel (`docs/README.md`, `docs/decisions/`, `docs/evidence/`, `docs/history/`, and `docs/reference/`) while forbidding `current`/`future` roots such as `docs/current/` and `docs/future/`. Product or adopter roots such as `docs/start/`, `docs/governance/`, and `docs/plans/` are extensions, not required kernel lanes. `ethos fleet retirement-readiness --target <repo> --root <product> --json` uses the same audit as a blocking embedded-backend retirement gate.

`ethos quality generated-artifacts --json` audits the Generated Artifact Topology Contract. It routes repository paths into declarative interface, local runtime, generated output, curated evidence, governed-docs, source-tree, package-metadata, and review-required classes; it blocks tracked generated drift outside `.cache/local-state/`, `build/ethos/`, and `build/evidence/`, while keeping `.config/ethos/` declarative-only and requiring curated evidence promotion under `docs/evidence/`, `evidence/chronicle/`, or `evidence/parity/`.

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
ethos lane start <name> --path <worktree-path> --owner <owner> --claim-id <claim> --apply
ethos lane refresh-base --apply --authorize --expect-head <git-head>
ethos lane bind-claim --claim-id <claim> --apply
ethos lane prewrite <path> --editor-root <worktree-path> --require-editor-root
ethos lane retire-landed --branch <work-lane-branch> --expect-head <work-lane-head> --apply
ethos lane retire-unbound --branch <work-lane-branch> --expect-head <git-head> --reason <why> --authorize --apply
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
`ethos status --json` also lifts first-glance coordination state into
`summary.foreign_work_lane_count`, `summary.unbound_work_lane_count`,
`summary.missing_lease_count`, `summary.dirty_foreign_work_lane_count`,
`summary.coordination_advisory_count`, and `summary.coordination_blocking`.
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
to the configured candidate branch, which target path would be updated, who owns
the lease when known, which claim is bound when known, and which mutation gap
blocks closeout.
The `data.coordination` object reports foreign Work Lanes with scope-aware
coordination state and unbound Work Lane refs with their relation to accepted
truth. Plain presence remains advisory through `advisory_gaps` such as
`foreign_work_lane_present`, `unbound_work_lane_ref_present`, or
`work_lane_missing_lease:<branch>`. Candidate integration from a Work Lane is
blocked only when a required coordination gap is present, such as unknown current
or foreign scope. Same-file or ancestor-scope overlap is surfaced as advisory
contention through `coordination_gap:scope_overlap:<branch>` so Git's
fast-forward land remains the mutation arbiter without serializing unrelated
agents that share a directory.
Each `foreign_work_lanes[]` item also exposes the current actor's capability:
`current_actor_capability=observe`, `allowed_actions=["observe"]`, and
`forbidden_actions=["write", "land", "retire"]`. The write policy is
`owner_only`; retirement requires the owner, an accepted handoff, or maintainer
break-glass. This is a product read model, not a host message bus: assistant hosts, MCP, editor hosts, and CI adapters all see the same
repository fact and must route mutation through their own owned lane.
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
command instead of waiting for `land --apply` to fail.
`ethos lane candidate --refresh-from-accepted --json` checks whether a clean
candidate train can be reset to the accepted root. Apply mode requires
`--authorize` plus `--expect-head`; it is the recovery path when accepted-root
closeout reports `candidate_diverged_from_accepted`.
`ethos lane retire-landed` lists landed Work Lanes without mutation by default.
Apply mode requires an explicit Work Lane branch so cleanup cannot accidentally
remove another active agent's worktree. Leased lanes are owner-bound: when the
actor binding does not match the lease owner, the JSON payload reports
`foreign_work_lane_retire_authority_required`, `actor_source = "ETHOS_ACTOR"`,
whether an actor is bound, the required lease owner, and a bounded next action to
bind the actor or obtain handoff.
`ethos lane retire-unbound` is the maintainer cleanup path for local unbound
Work Lane refs that already appear in `data.coordination.unbound_work_lane_refs`.
It is dry-run by default; apply mode requires `--authorize`, `--expect-head`,
and a non-empty `--reason`, then deletes `refs/heads/<branch>` with a
head-bound Git ref transaction. It does not replace `ethos land` or
`retire-landed`, and it does not remove linked worktrees.
The standard local lifecycle is product state even when a host provides its own
presentation: create the Work Lane through `ethos lane start`, attach claim
evidence with `ethos lane bind-claim` when needed, refresh the lane base only
through `ethos lane refresh-base`, land only through `ethos land`, retire
landed lanes through `ethos lane retire-landed`, and retire unbound residue refs
through `ethos lane retire-unbound`. Raw Git
worktree creation is an observable repository fact, but it is not admitted as
the standard ETHOS workflow state because it has no ETHOS lease or claim
boundary. `ethos orient --json` provides a derived reader view for human/agent discoverability;
`ethos status --json` remains the pure machine contract for role, dirtiness,
branch bindings, candidate state, and coordination.

Hook admission:

```bash
ethos hook admit context --expected-root <repo-root>
ethos hook admit pre-tool <path> --editor-root <worktree-path> --require-editor-root
ethos hook admit pre-run <path> --command <shell-command> --editor-root <worktree-path>
ethos hook admit post-write <path> --editor-root <worktree-path>
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
`land --apply` from an admitted Work Lane advances the configured candidate
branch; it does not advance the accepted root.
Accepted-root closeout is also an ETHOS mutation. The current ETHOS runner may
execute the closeout command above against the clean accepted-root checkout, audits
the configured candidate worktree before mutation, and then fast-forwards the
accepted branch from the candidate branch. Raw Git merge commands are repository
operations, not the ETHOS product mechanism.

`ethos campaign closeout --json` is the campaign-mode local closeout report. It
does not mutate Git and does not push. The output aggregates workspace
`closeout_support`, trust closeout, intake projection state, evolution
state, release policy, parity backlog, planned shadow parity execution, and
publish readiness under `data.packages`. The `trust_closeout` package composes
claim envelopes, promotion readiness, executed proof evidence, and Work Lane
claim binding. The `intake_projection` package records provider state as
projection evidence with `repository_truth=false`; it does not promote intake
state into repository truth.
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
exact `ethos parity shadow --adopter <adopter-id> --target <repo> --execute
--write-evidence --json` command. If no target is supplied, ETHOS does not reuse
a target path from stale evidence as the next action.

ETHOS report and audit payloads use a governed repository contract. Every
governed repository exposes `governance_context` so consumers can read the same
command semantics without inferring product truth from a special branch or
private command plane. The context records the profile, repository subject,
kernel chain, shared transition commands, reader-view commands, scorecard
commands, repository truth boundary, and profile or adapter boundary.
`shared_commands` and `transition_commands` list the five-command transition
loop: `ethos status`, `ethos plan`, `ethos prove`, `ethos land`, and
`ethos publish`. `reader_view_commands` lists the read-only first-glance view:
`ethos orient`. `scorecard_commands` lists the read-only payoff view:
`ethos report`. `ethos report --json` projects required gaps through
repository-neutral layers: `governance_audit` for the active repository governance
verdict, `capability_parity` for migration or adopter parity, and
`playbook_projection` for assistant-facing projection proof. Each layer exposes
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
