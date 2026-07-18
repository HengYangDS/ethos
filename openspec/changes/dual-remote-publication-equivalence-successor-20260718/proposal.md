## Why

ETHOS currently models only one provider-shaped remote, and its hosted CI still
runs on the local-only `candidate/dev` train. That conflates local integration
with publication and makes GitLab/GitHub unequal even though both must be full
repository, CI/CD, and distribution planes.

## What Changes

- Declare one three-layer publication topology: local verification/install,
  GitLab organization collaboration, and GitHub public distribution.
- Require both remote targets to expose equal repository, CI/CD, and
  publication capabilities while retaining distinct roles and no failover or
  authority ordering.
- Restrict remote push admission and hosted CI triggers to `dev`, `main`, and
  `submit/*`; reject `candidate/dev`, `work/*`, and undeclared targets.
- Project two independent read-only remote observations in `ethos publish`.

## Capabilities

### New Capabilities

- `dual-remote-publication`: Equal GitLab/GitHub topology and remote-ref
  admission while preserving local verification as a separate layer.

### Modified Capabilities

- `repository-governance`: Publication topology and provider-CI requirements
  become explicitly dual-remote and candidate-local.

## Impact

Release policy parsing, pre-push admission, publish read models, hosted CI
projections, adoption scaffold, docs, tests, OpenSpec, claim, and Chronicle.
No remote push, hosted-run assertion, foreign Work Lane mutation, or OpenSpec
schema extension is included.
