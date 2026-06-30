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

Schema validation is product governance. A command that returns JSON without a
tracked schema is not mature enough for automation.
