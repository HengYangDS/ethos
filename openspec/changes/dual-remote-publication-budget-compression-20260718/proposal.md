# Compress Dual-Remote Publication Implementation

## Why

The dual-remote topology is correct but the rebased implementation exceeds the
current shared source budget. Raising its allowance would hide that regression.

## What Changes

- Compress the topology reader, publication reducers, and scaffold declaration.
- Preserve explicit GitLab/GitHub remotes, `dev`/`main`/`submit/*` admission,
  legacy verbose declarations, independent no-push observations, and local-only
  candidate/work branches.

## Capabilities

- `repository-governance`: subject=dual-remote-publication-topology; reuse=extend; change=modify; facet:lifecycle=validation,release; facet:surface=cli,scaffold; facet:authority=source,test,openspec,claim,evidence

## Impact

Release policy, push admission, publish, scaffold, tests, and evidence compact
without changing remote authority or the official OpenSpec schema.

## Out Of Scope

- Raising source-budget allowances, suppressing gates, pushing a remote, or
  claiming hosted CI.
