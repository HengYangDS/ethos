---
subject: ethos:forge-provider-contract
role: policy
state: canonical
relations:
  canonical_for: hosted forge and CI provider boundary
---

# Forge Provider Contract

Status: canonical.

Purpose: define how ETHOS supports GitHub and GitLab without turning either
hosted forge into repository truth or a second command plane.

See also: [Product Design Contract](product-design-contract.md),
[Adoption Profiles](../architecture/adoption-profiles.md),
[Gate Runner](../architecture/gate-runner.md), and
[Tooling Adoption Roadmap](../plans/tooling-adoption-roadmap.md).

## Contract

ETHOS supports GitHub and GitLab as equivalent **provider adapters** for the
same Git-native governance contract; they are not separate product modes. Their
provider equivalence permits equal repository and CI/CD capability without
symmetric organizational publication authority. A repository may declare GitLab
as its organizational primary publication source and GitHub as an independent,
complete repository and CI/CD plane.

The provider contract is:

```text
repository owner scripts + ETHOS commands
  -> provider templates
  -> tracked provider projections
  -> local provider emulators
  -> hosted provider observations
```

The repository-owned scripts, command JSON, schemas, claims, OpenSpec records,
and evidence decide truth. GitHub Actions and GitLab CI project that truth into
provider runtimes. A hosted forge may provide review UI, branch protection,
runner status, artifacts, or remote publication observations; it does not own
ETHOS lifecycle state.

## Three-Layer, Peer-Complete Provider Topology

A repository that declares `publication_topology.mode =
"three_layer_peer_complete"` has three distinct roles:

| Layer | Role | May claim | Must not claim |
| --- | --- | --- | --- |
| Local | Verification and installation | Local owner-gate and installation evidence | Remote publication or hosted CI success |
| GitLab primary | Organizational primary publication plus complete repository and CI/CD plane | GitLab publication, repository, and hosted observations when separately observed | GitHub status as GitLab status |
| GitHub peer plane | Independent complete repository and CI/CD plane | GitHub repository, CI/CD, update, distribution, and hosted observations when separately observed | GitLab-primary publication or GitLab hosted status |

GitLab and GitHub SHALL each declare the same complete capability set:
`repository`, `ci_cd`, `update`, and `distribution`. GitLab remains the
organizational primary publication source. A GitHub outage does not reduce
GitLab capability; a GitLab outage does not reduce GitHub capability. `ethos
publish` remains read-only: it reports `remote_push = not_performed` and does
not mint a publication claim.

`candidate/dev` is an internal local integration ref, never a hosted-provider
ref. Both GitLab and GitHub SHALL admit only `dev`, `main`, and `submit/*` for
remote transition. The tracked release policy is the common whitelist; a
provider-specific exception is not permitted.

## Required Provider Invariants

1. **Peer-complete capability parity**: enabled GitHub and GitLab provider
   profiles SHALL each declare repository, CI/CD, update, and distribution
   capability and SHALL expose the corresponding tracked CI, review-template,
   and issue-template surfaces. The required gate classes, thresholds, and
   evidence boundaries SHALL be the same for a given profile. This concerns
   provider capability parity, not organizational publication authority.
1. **Remote-ref parity**: GitLab and GitHub SHALL use the same remote-ref
   whitelist: `dev`, `main`, and `submit/*`. They SHALL reject
   `candidate/dev`; it remains a local candidate-integration root.
1. **Template ownership**: provider YAML SHALL be generated or checked from
   tracked provider templates. Hand-edited drift in hosted files is a governance
   gap.
1. **Owner-script invocation**: provider jobs SHALL call `tools/ci/scripts/*`
   or `ethos ...` command surfaces instead of duplicating tool policy inline.
1. **Local-first proof**: local proof and local provider emulation SHALL be
   available before hosted publication is claimed.
1. **Evidence separation**: local owner gates, local provider emulators, hosted
   GitHub status, hosted GitLab status, remote branch reachability, and release
   publication SHALL remain separate evidence classes.
1. **No provider ontology**: GitHub and GitLab profiles may add adapters,
   variables, templates, emulators, and publication checks; they SHALL NOT alter
   `status -> plan -> prove -> land -> publish` semantics.

## Provider Surfaces

| Surface | GitHub | GitLab | Truth boundary |
| --- | --- | --- | --- |
| Template source | `.config/ci/templates/hosted/github-actions.yml` | `.config/ci/templates/hosted/gitlab-ci.yml` | Tracked projection source |
| Hosted projection | `.github/workflows/ci.yml` | `.gitlab-ci.yml` | Generated or checked provider file |
| Syntax gate | `actionlint` | YAML/config lint plus GitLab template checks | Provider syntax, not repository proof |
| Local emulator | `act` wrapper | `gitlab-ci-local` wrapper | Local provider emulation only |
| Hosted observation | GitHub Checks / Actions artifacts | GitLab pipeline/job/artifacts | Hosted provider evidence only |
| ETHOS gate | `ethos prove`, `ethos report`, owner scripts | Same | Repository governance truth |

## Evidence Classes

Provider evidence MUST declare one of these classes:

| Evidence class | Meaning | Forbidden claim |
| --- | --- | --- |
| `local_owner_gate` | Repository-owned scripts or `ethos prove --execute` ran locally. | Hosted CI passed. |
| `local_github_emulator` | GitHub Actions projection was emulated locally through an ETHOS wrapper. | GitHub hosted status passed. |
| `local_gitlab_emulator` | GitLab CI projection was emulated locally through an ETHOS wrapper. | GitLab hosted status passed. |
| `hosted_github_observation` | GitHub provider reported a concrete workflow/check/artifact fact. | GitLab status or repository proof. |
| `hosted_gitlab_observation` | GitLab provider reported a concrete pipeline/job/artifact fact. | GitHub status or repository proof. |
| `hosted_provider_observation` | A provider-neutral envelope captured GitHub/GitLab observation state or tool-discovery state. | Repository proof, hosted success, or remote publication. |
| `remote_publication` | A remote ref or release artifact was observed after publication. | Local proof sufficiency. |

Local emulator evidence MUST include provider, template path, projected file,
job or workflow scope, command, start/end Git head, dirty state, return code,
and explicit booleans such as `hosted_github_status_claimed=false` or
`hosted_gitlab_status_claimed=false`. Observation modes such as `doctor`,
`list`, and `dry-run` may report a missing optional emulator binary as bounded
local evidence with `tool_available=false`; materializing run modes remain
fail-closed when the required emulator binary is unavailable.

## Activation Profiles

`ethos adopt --profile github` and `ethos adopt --profile gitlab` may scaffold
provider-specific templates and variables. A dual-provider repository uses both
profiles over one governed repository subject. The profile changes projection
surfaces and required provider checks; it does not create a second repository
kind.

Dual-provider activation requires:

1. provider templates are present;
1. tracked hosted projections are present or intentionally disabled by profile;
1. template drift check passes;
1. local owner gate passes;
1. local emulator check passes for each enabled provider;
1. hosted observations are recorded separately before claiming hosted success.

## Non-Adoption Decisions

The forge contract does not require Nox, Pixi, Pants, Backlog, Superpowers,
Dagger, or a hosted CI provider SDK as product core. Those may be admitted as
adopter profile adapters when they reduce invalid states and keep their evidence
boundary explicit.
