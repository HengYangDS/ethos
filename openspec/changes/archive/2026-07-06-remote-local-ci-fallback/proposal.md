## Why

ETHOS already treats hosted publication as an adapter projection, but `publish`
did not surface a live remote availability fact or a named local-ci fallback
evidence class. When GitLab or another remote is unreachable, humans and agents
need an explicit local closeout path instead of stale remote-dependent guidance.

## What Changes

- Probe configured Git remote availability during publish readiness.
- Keep remote failures advisory and non-blocking for local readiness.
- Add `.config/ci/scripts/run-local-ci.sh` as the repository-local owner gate
  bundle for fallback evidence.
- Expose `local_ci_fallback` in publish JSON without claiming hosted CI success.

## Capabilities

- `repository-governance`: subject=remote-local-ci-fallback; reuse=extend; change=modify; facet:lifecycle=publish,closeout; facet:surface=cli,ci,evidence; facet:authority=git,local-ci

## Out Of Scope

- No remote push, merge request creation, or hosted CI status claim.
- No Docker or gitlab-ci-local emulator implementation in this change.
