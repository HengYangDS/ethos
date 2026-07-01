---
subject: ethos:openspec-self-governance
role: policy
state: canonical
relations:
  canonical_for: spec-driven self governance
---

# OpenSpec Self Governance

ETHOS keeps `openspec/` as an official self-governance capability for
spec-driven planning, change deltas, and canonical capability records.
In the current product state, this is a mandatory official governance
dependency: records that do not satisfy the OpenSpec workspace and validation
contract are not equivalent ETHOS governance records.

OpenSpec is not a second public command plane. User-facing workflows still enter
through `ethos ...`; ETHOS then calls the official OpenSpec CLI when it needs to
prove planning artifact health. The CLI invocation remains an adapter execution
surface even though the governance dependency is mandatory.

The required invariant is stricter than directory presence:

```bash
ethos self openspec --json
```

That command reports official OpenSpec `doctor`, `status`, and strict
validation results. Invalid placeholder changes are residue and should be
completed, archived, or removed before release.
