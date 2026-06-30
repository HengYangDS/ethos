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
`schemas/ethos/workspace-status.schema.json`. The schema fixes the accepted
roles, candidate train fields, linked worktree entries, and `branch_actions`
open-action vocabulary so consumers can distinguish `Open Worktree` from
ordinary checkout behavior.

`ethos status --json` and `ethos lane status --json` validate the live
workspace-status payload before emitting it. The validation verdict is reported
as a `schema_validation` diagnostic that targets `data`; the `data` object stays
the raw workspace-status payload so existing consumers can continue to read
`data.candidate`, `data.branch_actions`, and `data.closeout_support` directly.

`data.closeout_support` is part of the workspace-status schema. It exposes
whether the current checkout can be locally closed out to `candidate/dev`, the
target worktree path, the planned action, the lease owner when one is known, and
the same required-gap vocabulary used by mutation admission.

Schema validation is product governance. A command that returns JSON without a
tracked schema is not mature enough for automation.
