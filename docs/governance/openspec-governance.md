---
subject: ethos:openspec-repository governance
role: policy
state: canonical
relations:
  canonical_for: spec-driven repository governance
---

# OpenSpec Governance

ETHOS keeps `openspec/` as an official repository governance capability for
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
ethos openspec --json
ethos openspec --lifecycle --json
```

That command reports official OpenSpec `doctor`, `status`, and strict
validation results. Invalid placeholder changes are residue and should be
completed, archived, or removed before release.

Lifecycle mode does not replace the official OpenSpec CLI. It composes official
validation with ETHOS carrier checks. Every active change must have proposal,
design, tasks, delta specs, and an active trust-bearing claim whose
`carriers.openspec` points at the change. A syntactically valid change without a
claim binding reports `openspec_claim_binding_missing:<change>`.

Canonical capability profiles live beside canonical specs as
`openspec/specs/<family>/capability.toml`. They are validated by
`capability-profile.schema.json` and record the family owner, primary invariant,
routing question, boundary rules, and proof profile. They are routing and
contract metadata; promoted truth still lives in source, tests, schemas,
current docs, claims, and dated evidence.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
