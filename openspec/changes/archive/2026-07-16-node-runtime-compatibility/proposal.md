# Node Runtime Compatibility

## Why

The npm launcher declares a broad Node compatibility floor, while hosted
verification and packaging have used one exact Node 24 release. A maintainer
workstation may already run Node 26, but workstation, hosted, and
application-managed runtimes are separate authorities. Treating one observed
runtime as a universal baseline would either weaken hosted evidence or mutate
provider-owned runtimes without authority.

ETHOS needs one exact repository compatibility policy, a reusable acceptance
runner, and a reviewed promotion boundary that expands evidence without
silently changing the packaging default.

## What Changes

- Add `.config/checks/node/runtime.toml` as the exact compatibility and
  promotion-policy owner.
- Prove the npm launcher on Node 24.18.0 and Node 26.5.0 through
  `tools/ci/scripts/run-node-compatibility.sh`.
- Project the exact two-release matrix into the hosted GitLab npm verification
  job while keeping the npm packaging job on the Node 24.18.0 installer
  default.
- Record 2026-10-28 as an earliest review trigger, not an automatic promotion.
- Add architecture and behavioral contracts for policy, projection, command
  order, engine-strict execution, and fail-fast version mismatch.

## Capabilities

- `distribution`: subject=node-runtime-compatibility; reuse=extend;
  change=modify; facet:lifecycle=validation,release;
  facet:surface=config,ci,docs,openspec,test,package;
  facet:authority=source,test,docs,openspec,evidence

## Out Of Scope

- No replacement of workstation-, IDE-, desktop-, or application-managed Node
  runtimes.
- No change to the npm launcher's `engines.node >=20` compatibility floor.
- No change to `packageManager = npm@11.12.1`.
- No promotion of Node 26 to the packaging default before a separate reviewed
  change after the review trigger.
- No rerouting of the existing offline npm package quality gates through the
  hosted compatibility runner.
