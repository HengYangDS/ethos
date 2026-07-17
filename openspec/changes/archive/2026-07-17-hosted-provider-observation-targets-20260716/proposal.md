# Hosted Observation And Report Closure

## Why

The hosted observation runner currently asks gh and glab to infer a repository
from the current origin remote. That fails for repositories with only one
configured forge, for SSH/API host aliases, and whenever the provider CLI needs
an explicit repository selector. The resulting envelope also lacks a bounded
gap summary, while the report scorecard does not expose hosted observation or
local publication state required by the completion audit.

## What Changes

- Declare one provider-neutral repository-target environment variable for each
  supported forge in the hosted observation configuration.
- Add explicit --repo targets to GitHub and GitLab observation commands when
  configured.
- Report an absent provider target as bounded not_configured observation state
  instead of executing a misleading provider lookup failure.
- Summarize provider observation states and gaps at the envelope top level.
- Add read-only report projections for local publication readiness and hosted
  observation freshness/state.
- Preserve provider output as observation-only evidence and keep all hosted
  success and remote-publication claim flags false.
- Add architecture and scorecard regressions for targeting, bounded gaps,
  freshness, local publication, and provider fact normalization.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `proof-hosts`: subject=hosted-provider-observation-targeting; reuse=extend;
  change=modify; facet:lifecycle=evidence,validation;
  facet:surface=config,provider,ci,evidence,test;
  facet:authority=source,test,config,openspec
- `repository-governance`: subject=completion-audit-report-projection;
  reuse=extend; change=modify; facet:lifecycle=read-model,evidence;
  facet:surface=command,report,provider,publication,test;
  facet:authority=source,test,docs,openspec,evidence

## Impact

The change affects .config/checks/ci/hosted-observation.toml,
tools/ci/hosted_observation.py, the repository evidence read model,
packages/ethos/src/ethos/domain/report.py, report gap composition, and
architecture/domain tests. Operator and CI contexts may supply
ETHOS_HOSTED_GITHUB_REPO or ETHOS_HOSTED_GITLAB_REPO; no provider SDK or new
dependency is introduced.

## Out Of Scope

- No hosted success, repository proof, or remote publication claim is minted.
- No provider credentials, remotes, project settings, branches, tags, or
  releases are changed.
- No requirement is added for a repository to configure both providers.
- No private repository identifier is committed as a product default.
- The report projection does not replace ethos publish or authorize a remote
  mutation.
