# Equal Dual-Remote Publication Topology

## Why

GitLab and GitHub must be equal remote publication and CI/CD planes while local
verification and candidate closure remain independent. A fine-grained topology
Change must not be blocked by repository-wide source-budget debt.

## What Changes

- Preserve explicit GitLab/GitHub remotes, `dev`/`main`/`submit/*` admission,
  legacy verbose declarations, independent no-push observations, and local-only
  candidate/work branches.
- Keep `ethos quality source-budget` as an explicit repository-wide compression
  program, outside the Change proof floor and OpenSpec lifecycle admission.

## Capabilities

- `repository-governance`: subject=dual-remote-publication-topology; reuse=extend; change=modify; facet:lifecycle=validation,release; facet:surface=cli,scaffold; facet:authority=source,test,openspec,claim,evidence

## Impact

Release policy, push admission, publish, scaffold, tests, and evidence retain
their remote authority without changing the official OpenSpec schema.

## Out Of Scope

- Raising source-budget allowances, suppressing the repository compression
  program, pushing a remote, or claiming hosted CI.
