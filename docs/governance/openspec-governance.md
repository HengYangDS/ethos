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

Lifecycle also asks the configured official CLI to archive each active change
inside a disposable copy of `openspec/`. This is an archiveability preflight,
not a second delta parser: ETHOS neither rewrites delta operations nor mutates
the source workspace. An official failure becomes
`openspec_archive_preflight_failed:<change>:<code>` with the official diagnostic
projected under `archive_preflight`. The same lifecycle projection is consumed
by `ethos plan --changed`, `ethos prove`, and `ethos land`; accepted-root
closeout evaluates it against the admitted candidate root.

For adopters, the official active or archiving Change selection also feeds one
ETHOS-owned material-scope read model. An adopter declares the material path
families in `[openspec].material_paths`; an active Change may declare its
covered paths in `openspec/changes/<id>/scope.toml`. The companion is not an
official OpenSpec workflow-schema extension and cannot replace the official
lifecycle. `lane prewrite`, `plan --changed`, and `prove` consume the same
read model. An uncovered material path fails with
`openspec_material_path_uncovered:<path>`; lifecycle scope is not a
code-correctness gate and no method package carries Change authority.

The only bootstrap exception is the exact absent
`openspec/changes/<id>/scope.toml` for a Change that the official list already
identifies as active. Once written, that companion must validate and cover
itself. There is no blanket exemption for an OpenSpec directory, `.ethos/`, or
a path family; missing or invalid unrelated companions remain diagnostics and
do not override valid coverage supplied by another selected Change.

Adoption writes the complete material-path declaration. Later material writes
use ordinary Change-local `scope.toml` coverage; no historical profile-write
exception remains.

Canonical capability profiles live beside canonical specs as
`openspec/specs/<capability>/capability.toml`. They are validated by
`capability-profile.schema.json` and record the family owner, primary invariant,
routing question, boundary rules, and proof profile. They are routing and
contract metadata; promoted truth still lives in source, tests, schemas,
canonical docs, claims, and dated evidence.

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

Logical Change IDs are date-free lower-kebab identifiers beginning with a
letter. The only archive date is the leading directory component:
`openspec/changes/archive/YYYY-MM-DD-<change-id>/`. A numeric-leading ID,
terminal `YYYYMMDD` Change-ID suffix, or two dated carriers for one logical ID
is invalid; the repository keeps no alias, redirect, or date-based fallback.
Claim IDs and Chronicle paths may remain independently dated evidence labels.

Adoption does not create an OpenSpec workspace. When an adopter invokes the
OpenSpec capability, the official OpenSpec command owns workspace creation and
ETHOS validates the resulting tracked surface.

## Productized Workspace Substrate

A complete ETHOS OpenSpec workspace is inspectable by humans and machines. It
contains workspace guidance, change guidance, accepted capability guidance,
`specs/families.toml`, `specs/capability.template.toml`, and
`changes/template.md`. The workspace is intentionally more than directory
presence: adopters should understand official OpenSpec duties, ETHOS
repo-local lifecycle checks, direct capability names, proposal facets, claim
binding, evidence refs, archive closeout, and rollback before writing a change.

Capability profiles expose `decision_axes` and `recommended_facets` as routing
metadata. These fields are inspired by external OpenSpec governance practice,
but the values are ETHOS-owned vocabulary. Aliases are diagnostic only and do
not replace live capability directory names as routing truth.

Agent invocation and closeout evidence are part of the product protocol. An
agent or host may provide an invocation envelope or host-readiness evidence, but
repository mutation still requires Work Lane admission and repository proof.
Closeout evidence should be topic-scoped and digest-bound so it remains
reviewable rather than becoming unstructured transcript truth.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).

## Adopter Lifecycle Parity

`ethos plan` and `ethos prove` evaluate official OpenSpec lifecycle when the
repository has a workspace or a changed path matches the adopter's declared
material scope. Otherwise a valid adopter reports OpenSpec as not applicable.
Lifecycle gaps remain OpenSpec and repository-governance obligations: they are
not code-correctness gates, and no Superpowers or other method package carries
Change authority. Material-path scope admission remains fail-closed
`adopter-material-change-scope-20260714`.
