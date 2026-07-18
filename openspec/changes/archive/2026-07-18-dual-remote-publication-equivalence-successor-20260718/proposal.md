# Equal Dual-Remote Publication Topology

## Why

ETHOS currently models one provider-shaped remote and runs hosted CI on the
local-only `candidate/dev` train. That conflates local integration with remote
publication and leaves GitLab/GitHub unequal despite each requiring full
repository, CI/CD, and publication capability.

## What Changes

- Declare one three-layer publication topology: local verification/install,
  GitLab organization collaboration, and GitHub public distribution.
- Require GitLab and GitHub to expose equal `repository`, `ci_cd`, and
  `publication` capabilities without authority ordering, failover, or
  replacement.
- Restrict remote push admission and hosted CI triggers to `dev`, `main`, and
  `submit/*`; reject `candidate/dev`, `work/*`, arbitrary branches, and
  undeclared targets.
- Project two independent, read-only remote observations in `ethos publish`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: subject=dual-remote-publication-topology;
  reuse=extend; change=modify; facet:lifecycle=validation,release;
  facet:surface=cli,docs,openspec,evidence,scaffold,ci;
  facet:authority=source,test,docs,openspec,claim,evidence

## Impact

Release policy parsing, pre-push admission, publish read models, hosted CI
projections, adoption scaffold, docs, tests, OpenSpec, claim, and Chronicle.
No remote push, hosted-run assertion, foreign Work Lane mutation, or OpenSpec
schema extension is included.

## Out Of Scope

- Pushing, configuring, or privileging either remote.
- Claiming that observation is hosted CI success or remote publication.
- Changing candidate/accepted closeout authority, weakening proof, or altering
  the official OpenSpec schema.
- Mutating the predecessor lane, DDWG, or any foreign worktree.
