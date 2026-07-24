## Why

GitHub repository proof on the self-hosted macOS runner can lose an xdist
worker when the global `pytest-timeout` thread handler reaches its bound,
because that handler terminates the worker process instead of reporting an
ordinary test failure. The same accepted source completed all 2,954 tests on
the same runner when the timeout remained finite but used a macOS-compatible
signal handler with additional headroom.

## What Changes

- Give the Python test owner script an explicit, validated pair of optional
  timeout override inputs.
- Project a five-minute signal-based timeout only into GitHub's macOS
  repository-proof job while retaining four workers.
- Keep the repository-wide pytest defaults and GitLab execution unchanged.
- Add architecture coverage for the owner-script contract and generated
  provider projection.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: subject=github-pytest-timeout-resilience; reuse=extend;
  change=modify; facet:lifecycle=validation; facet:surface=ci,test,openspec,evidence;
  facet:authority=source,test,openspec,claim,evidence.

## Out Of Scope

- Changing the global 120-second thread-based pytest default.
- Changing GitLab's single-worker projection, runner hardware, or provider
  topology.
- Retrying failed tests, suppressing timeout failures, or treating a cancelled
  workflow as passing evidence.
- Modifying or closing foreign Work Lanes.

## Impact

The existing Python test owner script, GitHub hosted-CI template and generated
workflow, two architecture contracts, the quality specification, and bounded
claim/Chronicle evidence. No dependency or runtime installation changes.
