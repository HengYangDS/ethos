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

`ethos report` is the read-only scorecard over that workflow. It is not a
transition command:

```bash
ethos report
```

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
ethos explain required_gaps
```

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
ethos lane start <name> --path <worktree-path> --owner <owner> --claim-id <claim> --apply
ethos lane refresh-base --apply --authorize --expect-head <git-head>
ethos lane bind-claim --claim-id <claim> --apply
ethos lane prewrite <path> --editor-root <worktree-path> --require-editor-root
ethos lane retire-landed --branch <work-lane-branch> --apply
```

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
The `data.closeout_support` object reports whether the current checkout can land
to the configured candidate branch, which target path would be updated, who owns
the lease when known, which claim is bound when known, and which mutation gap
blocks closeout.
The `data.coordination` object reports foreign Work Lanes as advisory
coordination state. It carries `blocking=false`, an empty `required_gaps` list,
and `advisory_gaps` such as `foreign_work_lane_present` or
`work_lane_missing_lease:<branch>`. These gaps describe collaboration risk; they
do not block the current clean lane unless the current lane's own
`closeout_support.required_gaps` contains a blocking gap.
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
`ethos lane retire-landed` lists landed Work Lanes without mutation by default.
Apply mode requires an explicit Work Lane branch so cleanup cannot accidentally
remove another active agent's worktree.
The standard local lifecycle is product state even when a host provides its own
presentation: create the Work Lane through `ethos lane start`, attach claim
evidence with `ethos lane bind-claim` when needed, refresh the lane base only
through `ethos lane refresh-base`, land only through `ethos land`, and retire
only through `ethos lane retire-landed`. Raw Git
worktree creation is an observable repository fact, but it is not admitted as
the standard ETHOS workflow state because it has no ETHOS lease or claim
boundary.

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
`data.remote_push = "not_performed"` and `data.publication.remote_state =
"deferred"` while still exposing the configured submit branch plan.
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
kernel chain, shared transition commands, scorecard commands, repository truth
boundary, and profile or adapter boundary.
`shared_commands` and `transition_commands` list the five-command transition
loop: `ethos status`, `ethos plan`, `ethos prove`, `ethos land`, and
`ethos publish`. `scorecard_commands` lists the read-only payoff view:
`ethos report`. `ethos report --json` projects required gaps through
repository-neutral layers: `governance_audit` for the active repository governance
verdict, `capability_parity` for migration or adopter parity, and
`playbook_projection` for assistant-facing projection proof. Its summary uses
`governance_gap_count` for active repository governance gaps and
`parity_pending_count` for capability parity backlog.

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
