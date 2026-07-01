---
subject: ethos:command-plane
role: reference
state: canonical
relations:
  canonical_for: public commands
---

# Command Plane

Public daily commands:

```bash
ethos status
ethos plan
ethos prove
ethos land
ethos publish
```

The npm launcher exposes the same root command:

```bash
npm run ethos -- --version
```

Advanced commands remain under `ethos ...`. Retired root commands are not
compatibility surfaces.

Quality and governance:

```bash
ethos quality command-registry
ethos quality command-surface
ethos quality command-examples
ethos quality coupling-audit
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
ethos self audit
ethos self audit --mode shape
ethos self audit --mode deep
ethos self openspec --lifecycle
ethos prove --execute
ethos prove --full --execute
ethos prove --expect-head <git-head>
ethos self hypothesize
ethos self prove --mode shape
ethos self prove --mode deep
ethos campaign hypotheses
ethos campaign closeout --adopter alphasim-dmgr --target <repo>
ethos intake status
ethos parity ledger
ethos parity gaps --adopter alphasim-dmgr
ethos parity shadow --target <repo>
ethos report
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
ethos playbooks check --mode legacy-compat
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
`ethos lane retire-landed` lists landed Work Lanes without mutation by default.
Apply mode requires an explicit Work Lane branch so cleanup cannot accidentally
remove another active agent's worktree.
The standard local lifecycle is product state even when a host provides its own
presentation: create the Work Lane through `ethos lane start`, attach claim
evidence with `ethos lane bind-claim` when needed, land only through
`ethos land`, and retire only through `ethos lane retire-landed`. Raw Git
worktree creation is an observable repository fact, but it is not admitted as
the standard ETHOS workflow state because it has no ETHOS lease or claim
boundary.

Mutation readiness is explicit:

```bash
ethos land --apply --authorize --expect-head <git-head>
ethos publish --apply --authorize --expect-head <git-head>
```

Those commands still report readiness in the current implementation; remote
publication remains an adapter responsibility. `publish --json` reports
`data.remote_push = "not_performed"` and `data.publication.remote_state =
"deferred"` while still exposing the configured submit branch plan.
`land --apply` from an admitted Work Lane advances the configured candidate
branch; it does not advance the accepted root.

`ethos campaign closeout --json` is the campaign-mode local closeout report. It
does not mutate Git and does not push. The output aggregates workspace
`closeout_support`, trust closeout, intake projection state, self-evolution
state, release policy, parity backlog, planned shadow parity execution, and
publish readiness under `data.packages`. The `trust_closeout` package composes
claim envelopes, promotion readiness, executed proof evidence, and Work Lane
claim binding. The `intake_projection` package records provider state as
projection evidence with `repository_truth=false`; it does not promote intake
state into repository truth.
`data.remote_publication.state = "deferred"` is expected while the remote
publication adapter is unavailable.

Self-governance modes are explicit. `shape` is the daily fast path for product
shape, schemas, claims, command vocabulary, and OpenSpec layout. `deep` includes
official OpenSpec CLI validation and is required for release or archive proof.
`ethos self openspec --lifecycle --json` adds ETHOS lifecycle carrier review:
active changes need proposal, design, tasks, delta specs, and an active claim
binding in addition to official OpenSpec validation.

Proof states are execution-depth states. `ethos prove --json` is readiness and
reports `state=ready` with `executed=false` when planning and static admission
pass. `ethos prove --execute --json` can report `state=proven` because every
selected gate records an exit code. `ethos prove --full --json` without
execution is intentionally `gapped` with `full_proof_requires_execute`.

`ethos quality coupling-audit --json` reports product-semantic hard bindings,
mandatory governance dependencies, native protocol bindings, self-hosting
toolchain bindings, profile or adapter bindings, legacy evidence, and
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
MCP/ACP protocol adapters, the npm launcher distribution adapter, legacy
evidence, and provider fixtures under their explicit binding layers.

Skills V2 command payloads keep legacy playbook fields while adding normalized
registry and package evidence. `ethos playbooks check --json` defaults to
`legacy-compat`, which keeps external v1 adopters readable and reports V2 gaps
as advisory. `ethos playbooks check --mode v2-strict --json` is the product
proof mode; it requires activation ownership metadata, path coverage, proof
obligations, package manifests, digest agreement, and official-quality
`SKILL.md` content. `ethos playbooks route --changed --json` selects records via
the explicit `changed-scope` route and path-glob metadata.

`ethos report --json` includes `data.scorecards[]` with the `skills-v2`
scorecard and `data.gap_layers.playbook_projection` for blocking Skills V2
gaps. `ethos prove --execute --gate playbooks-v2 --json` executes the strict
playbook gate. `ethos quality projection-drift --json` reports package drift,
the normalized registry digest, the expected registry digest, the playbook
generator digest, the expected generator digest, and activation input digests.
