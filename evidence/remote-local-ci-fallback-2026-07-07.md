# Remote Availability And Local CI Fallback Evidence

Date: 2026-07-07
Work Lane: `work/remote-local-ci-fallback`

## Claim Boundary

This evidence binds `remote-local-ci-fallback-20260707` to the ETHOS publish
read model change that probes configured Git remote availability and exposes a
local-ci fallback evidence class when remote publication is unavailable or
deferred.

The fallback is local repository evidence only. It does not claim hosted GitLab,
GitHub, or other remote CI success.

## Local Evidence

- `.config/ci/scripts/run-local-ci.sh` invokes reusable owner gate scripts rather
  than restating hosted CI policy inline.
- `ethos publish --json` emits `remote_availability` and `local_ci_fallback`.
- `local_ci_fallback.evidence_class` is `local_fallback`.
- `local_ci_fallback.hosted_ci_status_claimed` is false.
- `ethos publish --json` reported `remote_availability.state=unavailable`,
  `remote_availability.blocking=false`, and `local_ci_fallback.hosted_ci_status_claimed=false`.
- `.config/ci/scripts/run-local-ci.sh` passed: Python lint and format, config
  format and lint, shell lint, Google-style docstring coverage, repository
  hygiene, and full Python tests.
- Full Python tests passed through the local-ci owner bundle: 788 passed, 0
  failed, total coverage 95.11%.
- `ethos quality schemas --json` passed after synchronizing the
  campaign-closeout schema and contract sample with remote availability and
  fallback evidence fields.
- Focused tests passed for unavailable remote, available remote, publish JSON
  fallback shape, configured submit branch lifecycle, campaign closeout schema,
  and configuration owner registration.
- `ethos quality claims --json` passed before this evidence refresh.
- `openspec validate --all --strict --json` and `ethos openspec --lifecycle --json`
  passed after archive promotion.

## Boundary

This evidence does not claim remote push, merge request creation, hosted CI
pipeline status, Docker local emulator proof, or gitlab-ci-local execution. It
only claims local publish-readiness fallback semantics, stable command/schema
shape, and local owner-gate entrypoint availability.
