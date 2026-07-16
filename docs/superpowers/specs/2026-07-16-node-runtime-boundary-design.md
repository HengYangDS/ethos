# Node Runtime Compatibility Design

## Context

ETHOS exposes a thin npm launcher with engines.node >=20, while hosted npm
verification currently installs one exact Node 24 release. A maintainer
workstation may use the latest stable Node release, and IDEs or desktop
applications may carry their own managed Node runtimes. Those provider
runtimes are not one authority and must not be mechanically rewritten into one
version.

## Goals

- Prove the npm launcher on Node 24.18.0 and Node 26.5.0.
- Keep Node 24.18.0 as the packaging/default hosted runtime until Node 26 has
  entered Active LTS and hosted evidence supports a deliberate promotion.
- Give the compatibility set one repository policy owner and keep hosted CI as
  a checked projection.
- Keep host-managed IDE/application runtimes outside repository mutation.

## Non-Goals

- Replacing IDE-, application-, or workstation-owned Node runtimes.
- Changing the npm launcher implementation or its node >=20 compatibility
  floor.
- Promoting Node 26 to the packaging default before its LTS review gate.
- Changing packageManager = npm@11.12.1 without a separate package-manager
  supply decision.

## Design

.config/checks/node/runtime.toml owns the exact compatibility releases,
the current hosted default, the next default candidate, and the earliest review
date. tools/ci/scripts/run-node-compatibility.sh verifies that the active
runtime matches the requested matrix version and runs the existing npm launcher
acceptance commands.

The GitLab npm verification job projects the policy as a two-version matrix.
Architecture tests parse both the policy and the projection so version drift is
visible. The packaging job continues to use the installer default, which
remains Node 24.18.0.

The date 2026-10-28 is a review trigger, not an automatic state transition.
Changing the default requires current official release status, successful
hosted compatibility results, package evidence, and a separate reviewed change.

## Verification

- Focused architecture tests fail before the policy, runner, and matrix exist.
- The focused tests pass after the owner and projection agree.
- The compatibility runner succeeds in isolated Linux environments for both
  exact Node versions.
- Shell/config/OpenSpec checks and HEAD-bound ETHOS proof remain green.

## Rollback

Revert the compatibility commit. This restores the single Node 24 verification
job without touching host-managed runtimes or historical evidence.
