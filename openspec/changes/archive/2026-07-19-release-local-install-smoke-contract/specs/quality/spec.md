## ADDED Requirements

### Requirement: Fresh Offline Local Installation Smoke Gate

ETHOS SHALL prove local wheel installability through one reusable owner that
uses a fresh environment, disables network access during build and install,
binds its result to a stable HEAD, and remains separate from remote or hosted
claims.

#### Scenario: Fresh environment proves both installed packages

- **WHEN** `tools/ci/scripts/run-local-install-smoke.sh` executes
- **THEN** workspace wheels SHALL be built under `build/artifacts/python/**`
- **AND** disposable state SHALL stay under
  `build/runtime/work/local-install-smoke/**`
- **AND** installation SHALL run offline into a newly created virtual
  environment
- **AND** both `ethos` and `ethos_core` module origins SHALL resolve inside that
  environment rather than the source checkout
- **AND** the installed `ethos --help` and `ethos --version` commands SHALL
  succeed.

#### Scenario: Local install evidence is bounded and head-stable

- **WHEN** the smoke succeeds on a stable Git HEAD
- **THEN** it SHALL write `build/evidence/local-install/smoke.json` containing
  the exact HEAD, wheel digests, installed origins, executed CLI checks, and
  `hosted_ci_status_claimed=false` plus `remote_publication_claimed=false`
- **AND** a HEAD change during execution SHALL fail the owner rather than retain
  a passing receipt.

#### Scenario: Local CI and full proof share the owner

- **WHEN** local CI runs
- **THEN** it SHALL invoke the owner before writing local fallback evidence
- **AND** `system/tools.toml` SHALL register one active local-install concern
- **AND** `system/gates.toml` SHALL register one trust-bearing, file-writing,
  offline `local-install-smoke` gate in `product_full` after `build`
- **AND** only an executed full proof SHALL claim that full-proof gate ran.
