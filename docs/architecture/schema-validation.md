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
vocabulary, candidate fields, linked worktree entries, and role-policy
`branch_bindings`. Release root and accepted root are separate semantic roles.
Bindings are ordered release root first, accepted root second, then candidate,
then additional bound branches.

`ethos status --json` and `ethos lane status --json` validate the live
workspace-status payload before emitting it. The validation verdict is reported
as a `schema_validation` diagnostic that targets `data`; the `data` object stays
the raw workspace-status payload so existing consumers can continue to read
`data.candidate`, `data.branch_bindings`, and `data.closeout_support` directly.

`data.closeout_support` is part of the workspace-status schema. It exposes
whether the current checkout can be locally closed out to the configured
candidate branch, the target worktree path, the planned operation, the lease
owner when one is known, and the same required-gap vocabulary used by mutation
admission.

Schema validation is product governance. A command that returns JSON without a
tracked schema is not mature enough for automation.
