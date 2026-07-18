# CI Tool Supply Determinism

## Why

The hosted `ethos:secrets` gate for current HEAD stalled on a hot-path GitHub
release download, reaching repeated curl timeouts and SSL EOF retries before the
actual secret scan could start. A quality gate that depends on flaky external
transport at execution time is a weak proof carrier: it can make a healthy
repository appear red or pending for infrastructure reasons.

## What Changes

- Add one reusable CI artifact download helper with bounded retries, resumable
  partial files, low-speed detection, and atomic destination writes.
- Route the gitleaks and Node installers through that helper and a shared
  `build/cache/ci-tools/` cache.
- Project the cache into GitLab CI without moving policy into `.gitlab-ci.yml`.
- Register CI tool supply as a product quality concern in the tool catalog.

## Capabilities

- `quality`: subject=ci-tool-supply; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=ci,config; facet:authority=source,test,openspec
- `repository-governance`: subject=hosted-ci-readiness; reuse=extend; change=modify; facet:lifecycle=publish; facet:surface=ci,evidence; facet:authority=source,test,evidence

## Out Of Scope

- No new CI provider abstraction or command plane.
- No weakening of secret, markdown, npm, package, or proof gates.
- No claim of hosted CI success until the relevant remote pipeline actually
  succeeds.
