## Why

GitLab job 36899 at accepted `10d328944` failed before tests because the
required source-budget cross-check executable was absent. Its dependent test,
coverage and generated-artifact gates correctly did not run. The hosted setup
implicitly relied on tools installed on a maintainer host.

## What Changes

- Bind the budget cross-check tool to one version and official archive digest
  in the existing budget configuration.
- Prepare and verify a project-local executable before hosted verification;
  both Forge projections continue to consume the same shell owner.
- Fail before tests on unsupported supply, download, checksum or version errors,
  retaining current diagnostics rather than stale passing proof or reports.
- Close the demonstrated hosted-verification prerequisites: explicit archive
  test clocks and child interpreters bound to the selected source checkout.
- Retain complete native process-observation failures in retirement assertions;
  successful repetitions do not establish a repair of an intermittent failure.

## Capabilities

### Modified Capabilities

- `quality`: hosted proof prepares the same declared source-budget tool supply
  without ambient host packages or relaxed gates.

## Impact

Existing budget configuration, hosted verification transport, one native tool
installer, runtime/archive test fixtures and the canonical terminal plan. No system
installation, extra budget parser, Forge-specific policy, new lane or change to
accepted product meaning. Python binding-observation work remains hash-preserved.
