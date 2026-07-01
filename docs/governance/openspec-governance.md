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
`openspec/specs/<capability>/capability.toml`. They are validated by
`capability-profile.schema.json` and record the family owner, primary invariant,
routing question, boundary rules, and proof profile. They are routing and
contract metadata; promoted truth still lives in source, tests, schemas,
current docs, claims, and dated evidence.

## Product Protocol

OpenSpec changes are ETHOS cases:

```text
case = proposal + design + tasks + spec deltas + claim/evidence refs
```

The active change folder records intended change. It does not supersede current
source, tests, schemas, docs, accepted specs, claims, or evidence until closeout
promotes those surfaces. Complete or archived changes are history, not default
containers for new semantic work.

Proposal capability entries must route directly to canonical live capability
names. ETHOS should reject or flag proposal metadata that cannot answer:

1. Which capability owns the primary behavior?
1. Which stable subject is changing?
1. Is the reuse stance `reuse`, `extend`, `extract`, or `new`?
1. Which lifecycle, surface, and authority facets explain the change?
1. What is deliberately out of scope?

`design.md` is mandatory for new capabilities, extracted ownership, cross-surface
topology changes, and product-shape changes. It must state why reuse or
extension is insufficient, where the official OpenSpec boundary ends, how ETHOS
adds repo-local validation, what proof is required, and how rollback works.

Archive closeout is an ETHOS product operation around the official OpenSpec
archive command. After the official command runs, ETHOS must guard live-spec
scope, archived task state, archive directory identity, retained evidence refs,
and Markdown links from the archived path.

Adopter scaffolds must create an inspectable OpenSpec workspace: config,
README files, change templates, capability templates, `specs/families.toml`,
and profile-appropriate first capabilities. A bare `openspec/` directory is an
incomplete scaffold.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
