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
ethos self audit
ethos self audit --mode shape
ethos self audit --mode deep
ethos prove --execute
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
ethos playbooks route
ethos playbooks route --changed
```

Work Lane admission:

```bash
ethos lane status
ethos lane candidate --path <candidate-worktree-path> --apply --expect-head <git-head>
ethos lane start <name> --path <worktree-path> --owner <owner> --apply
ethos lane prewrite <path> --editor-root <worktree-path> --require-editor-root
ethos lane retire-landed --branch <work-lane-branch> --apply
```

`ethos status --json` and `ethos lane status --json` expose role-policy branch
bindings under `data.branch_bindings`. The bindings are ordered by semantic
role: configured release root first, accepted root second, then candidate, then
additional bound branches such as Work Lanes. Each binding reports
`worktree_binding` as product state: `current`, `linked`, `unbound`, or
`absent`. Host adapters may project linked worktrees as host-specific open
commands, but the product payload does not expose host labels or checkout
actions as truth.
Both commands include a `schema_validation` diagnostic for the live
workspace-status payload. The diagnostic validates `data` against
`workspace-status.schema.json`; the validation result is not embedded in `data`
so the workspace-status object remains schema-valid.
The `data.closeout_support` object reports whether the current checkout can land
to the configured candidate branch, which target path would be updated, who owns
the lease when known, and which mutation gap blocks closeout.
`ethos lane start --json` returns `data.worktree` in apply mode. That object
uses the same `worktree_binding` vocabulary as status output, so hosts can
project the new Work Lane without treating adapter UI text as product truth.
Start admission requires both the accepted root and the candidate worktree to be
clean. A dirty candidate returns `candidate_worktree_dirty` and does not create
a Work Lane.
`ethos lane retire-landed` lists landed Work Lanes without mutation by default.
Apply mode requires an explicit Work Lane branch so cleanup cannot accidentally
remove another active agent's worktree.

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
`closeout_support`, self-evolution state, release policy, parity backlog,
planned shadow parity execution, and publish readiness under `data.packages`.
`data.remote_publication.state = "deferred"` is expected while the remote
publication adapter is unavailable.

Self-governance modes are explicit. `shape` is the daily fast path for product
shape, schemas, claims, command vocabulary, and OpenSpec layout. `deep` includes
official OpenSpec CLI validation and is required for release or archive proof.

`ethos quality coupling-audit --json` reports product-semantic hard bindings,
mandatory governance dependencies, native protocol bindings, self-hosting
toolchain bindings, profile or adapter bindings, legacy evidence, and
test-fixture coupling boundaries. It treats Git, worktrees, refs, and branch
roles as product semantics; OpenSpec as mandatory governance; command JSON,
schemas, TOML, JSONL, and ignored SQLite state as native protocols; and hosted
forge, editor, model, and current proof toolchain terms as non-product-semantic
bindings.
