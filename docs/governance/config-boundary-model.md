---
subject: ethos:config-boundary-model
role: policy
state: canonical
relations:
  canonical_for: .ethos, .config, rules, docs, and system placement boundaries
---

# Config Boundary Model

ETHOS separates repository binding, execution configuration, rules, evidence,
and machine contracts. No single directory owns every governance fact.

## Placement Matrix

| Surface | Role | Owns | Does Not Own |
| --- | --- | --- | --- |
| `.ethos/` | ETHOS binding layer | profile entrypoint, backend selection, ignored ETHOS local state | tool-native config, domain truth, durable evidence |
| `.config/` | execution/config layer | tool configuration, reusable gate policy, CI scripts, boundary configs, worktree configs | ETHOS ontology, evidence truth, user decisions |
| `rules/` | governance rule layer | human and agent rules, domain contracts, projection policies | tool implementation details, generated state |
| `docs/` | truth/evidence/explanation layer | current docs, decisions, dated evidence, reference material | local runtime state |
| `system/` | optional machine-contract layer | machine-readable product or system contracts | adopter-only domain truth when absent |
| `openspec/` | specification projection | official OpenSpec changes and specs | promoted runtime truth by itself |
| `claims/` | claim lifecycle layer | semantic claim records and evidence bindings | local execution state |
| `.agents/` | repo-local agent projection | skills and activation projections | independent truth store |

## `.ethos/` And `.config/`

`.ethos/profile.toml` references `.config/`; it does not replace it.

`.config/` remains the repository-native location for how tools run. A profile
may point to `.config/checks/`, `.config/boundaries/`, `.config/interfaces/`,
`.config/worktree/`, or `.config/ci/`, but the profile must not copy their
contents or make their physical layout universal.

## `system/` Optionality

Product repositories may expose machine contracts under `system/`. Adopter
repositories are not required to have a `system/` tree. ETHOS must work from the
repository profile, configuration roots, rules, docs, and evidence when no
system contract layer exists.

If `system/` exists, ETHOS may treat it as a machine-contract surface according
to the repository authority order. If it is absent, absence is not a profile gap
unless the profile explicitly requires it.

## Evidence Boundaries

Durable evidence belongs in the repository's durable evidence roots, commonly
`docs/evidence/` or a declared equivalent. Generated evidence belongs in generated
artifact roots, commonly `build/evidence/`. Host-local state belongs under
ignored state roots such as `.ethos/state/` or `.cache/local-state/`.

ETHOS must not turn generated artifacts or host-local state into durable truth.
A proof can cite generated evidence for a current HEAD, but durable claims need
reviewed evidence or an accepted repository authority surface.

## Tool Boundary

A tool configuration file decides how one tool runs. A tool catalog or profile
binding decides why the tool runs for a repository operation. Hosted CI files are
provider projections over repository-owned scripts and policies; they do not
replace local proof or repository evidence.

Status: see front matter.

Purpose: keep configuration placement MECE as ETHOS adoption expands across
repositories with different shapes and toolchains.

See also: [Repository Profile Contract](repository-profile-contract.md),
[Product Design Contract](product-design-contract.md), and
[Terminal Governance Product Design](../architecture/terminal-governance-product-design.md).
