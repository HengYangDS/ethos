---
subject: ethos:schema-validation
role: reference
state: canonical
relations:
  canonical_for: JSON protocol validation
---

# Schema Validation

ETHOS command output and kernel protocols are JSON-first and schema-governed.

`ethos quality schemas --json` validates tracked JSON Schemas with the
Draft 2020-12 validator. Command payloads use `schemas/ethos/result.schema.json`
as the stable envelope.

Workspace topology data is governed by
`schemas/ethos/workspace-status.schema.json`. The schema fixes the role
vocabulary, candidate fields, linked worktree entries, configured `role_policy`,
and role-policy `branch_bindings`. Release root and accepted root are separate
semantic roles. The role order is
release_root -> accepted_root -> candidate -> work_lane -> submit_lane. Bindings
are ordered by that semantic order, then by branch name for additional bound
branches. Work Lane bindings include `claim_id` and `claim_binding` so closeout
can distinguish local write ownership from trust-bearing claim evidence.

`ethos status --json` and `ethos lane status --json` validate the live
workspace-status payload before emitting it. The validation verdict is reported
as a `schema_validation` diagnostic that targets `data`; the `data` object stays
the raw workspace-status payload so existing consumers can continue to read
`data.role_policy`, `data.candidate`, `data.branch_bindings`, and
`data.closeout_support` directly.

Coupling audit output is governed by
`schemas/ethos/coupling-audit.schema.json`. It exposes `binding_registry` as
the product classification vocabulary for hard bindings, mandatory
dependencies, native protocols, self-hosting tools, adapters, legacy evidence,
and fixtures. The branch role entry carries its configuration source, config
keys, default-policy state, semantic role order, and configured patterns. The
Work Lane lifecycle entry carries the standard ETHOS lifecycle commands and
the raw-worktree bypass state that is not admitted as standard ETHOS workflow.
Registry entries cannot carry host navigation, action, or label fields; those
are adapter projections, not coupling contract state.

`data.closeout_support` is part of the workspace-status schema. It exposes
whether the current checkout can be locally closed out to the configured
candidate branch, the target worktree path, the planned operation, the lease
owner when one is known, the bound claim when one is known, and the same
required-gap vocabulary used by mutation admission.

Trust and promotion contracts are explicit:

- `claim.schema.json` accepts enriched active claim TOML with boundary,
  carrier, fallback, kill signal, and promotion fields.
- `trust-envelope.schema.json` governs the active claim envelope emitted by
  claim governance.
- `promotion-target.schema.json` restricts promoted authority references to
  repository-relative source, test, docs, schema, OpenSpec, or evidence paths.
- `capability-profile.schema.json` governs `openspec/specs/*/capability.toml`
  records that map each capability family to owner, invariant, routing, boundary,
  and proof metadata.

`ethos quality schemas --json` validates the schemas, sample contract instances,
and any canonical capability profiles present under `openspec/specs/`.

Schema validation is product governance. A command that returns JSON without a
tracked schema is not mature enough for automation.
