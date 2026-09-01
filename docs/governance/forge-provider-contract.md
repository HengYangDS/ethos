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
[Gate Runner](../architecture/gate-runner.md).

## Contract

ETHOS supports GitHub and GitLab as semantically homomorphic hosted forge
providers. They carry the same Git-native repository governance contract, not
separate product modes; their physical syntax and provider-native capabilities
may differ.

GitLab is the organization-collaboration plane and GitHub is the public-distribution
plane. Both carry the same repository, CI/CD, and publication capabilities; neither
is a fallback for, or authority above, the other. Hosted CI accepts only `dev`,
`main`, and `proposal/*`; `candidate/dev` and `work/*` remain local-only.

The provider contract is:

```text
repository owner scripts + ETHOS commands
  -> provider templates
  -> tracked provider projections
  -> local provider emulators
  -> hosted provider observations
```

The repository-owned scripts, command JSON, schemas, OpenSpec records,
Commitments, and Attestations decide truth. GitHub Actions and GitLab CI project that truth into
provider runtimes. A hosted forge may provide review UI, branch protection,
runner status, artifacts, or remote publication observations; it does not own
ETHOS lifecycle state.

For Git publication, local Git is the sole product-object authority. ETHOS
creates no provider-specific commit or tag: one locally signed commit or
annotated tag is transported unchanged to zero or more peers, and exact object
OID equality is required after publication. Provider-specific SSH keys, PATs,
OIDC identities, account-email mappings, and `Verified` badges belong to
transport or presentation. They cannot trigger replay, re-signing, identity
rewrite, tag recreation, history mapping, or tree-only parity.

## Required Provider Invariants

1. **Homomorphic semantics**: GitHub and GitLab SHALL cover the same required
   contract capabilities, thresholds, and evidence boundaries for a given
   profile. A provider-specific execution path is valid only when its reason is
   declared in `.config/checks/ci/templates.toml` and the shared capability is
   still proved exactly once by an owner script.
1. **Template ownership**: provider YAML SHALL be generated or checked from
   tracked provider templates. Hand-edited drift in hosted files is a governance
   gap.
1. **Owner-script invocation**: provider jobs SHALL call `tools/ci/scripts/*`
   or `ethos ...` command surfaces instead of duplicating tool policy inline.
1. **Collaboration-surface homomorphism**: issue and proposed-change forms SHALL
   project one provider-neutral subject/intent/contract/acceptance/evidence
   vocabulary into GitHub Issue/Pull Request and GitLab Issue/Merge Request
   paths. Provider-native syntax may differ; required semantics may not drift.
1. **Local-first proof**: local proof and local provider emulation SHALL be
   available before hosted publication is claimed.
1. **Evidence separation**: local owner gates, local provider emulators, hosted
   GitHub status, hosted GitLab status, remote branch reachability, and release
   publication SHALL remain separate evidence classes.
1. **No provider ontology**: GitHub and GitLab profiles may add adapters,
   variables, templates, emulators, and publication checks; they SHALL NOT alter
   the shared result, continuation, or effect semantics.
1. **Exact object projection**: peer adapters may authenticate transport, push
   an already existing local object under exact CAS, and observe the result.
   They SHALL NOT construct, rewrite, sign, or select a different product Git
   object.

## Provider Surfaces

| Surface | GitHub | GitLab | Truth boundary |
| --- | --- | --- | --- |
| Template source | `.config/ci/templates/hosted/github-actions.yml` | `.config/ci/templates/hosted/gitlab-ci.yml` | Tracked projection source |
| Hosted projection | `.github/workflows/ci.yml` | `.gitlab-ci.yml` | Generated or checked provider file |
| Syntax gate | `actionlint` | YAML/config lint plus GitLab template checks | Provider syntax, not repository proof |
| Local emulator | `act` wrapper | `gitlab-ci-local` wrapper | Local provider emulation only |
| Hosted observation | GitHub Checks / Actions artifacts | GitLab pipeline/job/artifacts | Hosted provider evidence only |
| Issue intake | `.github/ISSUE_TEMPLATE/task.md` | `.gitlab/issue_templates/task.md` | `forge_surface.required_sections` |
| Proposed change | `.github/PULL_REQUEST_TEMPLATE.md` | `.gitlab/merge_request_templates/default.md` | `forge_surface.required_sections` |
| ETHOS gate | `ethos prove`, `ethos status`, owner scripts | Same | Repository governance truth |

The checked parity inventory covers CI, issue intake, proposed-change review,
ownership, security intake, dependency updates, and release publication. A
capability may be explicitly absent only when the shared contract records the
absence and the reason. Unknown maintainer identities must not be replaced by a
fabricated `CODEOWNERS` entry.

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

## Activation

Provider projections are explicit operations over one governed repository
subject. Adoption never creates GitHub or GitLab files. A dual-provider
repository declares and verifies both provider surfaces independently; neither
provider state creates a second repository kind or mints repository truth.

Dual-provider activation requires:

1. provider templates are present;
1. tracked hosted projections are present or intentionally disabled by profile;
1. template drift check passes;
1. local owner gate passes;
1. local emulator check passes for each enabled provider;
1. hosted observations are recorded separately before claiming hosted success.

## Non-Adoption Decisions

The forge contract does not require Nox, Pixi, Pants, Backlog, Superpowers,
Dagger, or a hosted CI provider SDK as product-runtime dependencies. Those may be admitted as
adopter profile adapters when they reduce invalid states and keep their evidence
boundary explicit.
