# Proposal

## Why

The beta.3 release run 42099003242 failed its runtime jobs for linux-x64, linux-arm64 and
macos-arm64 at "Declare the components of the retained runtime archive". That step runs
`nox -s supply_chain`, which calls `materialize_tool(ROOT, "syft")`. With Syft not staged, the call
looks for mise and fails with `mise_unavailable:put the mise executable on PATH`.

The job's shared supply step, "Prepare locked native build supply", stages only `vale`. GitLab's
bootstrap stages Syft, and the local proof had the operator's mise on PATH, so only the GitHub
release job lacked it. Those steps run for the first time at tag time, so neither the proof nor the
proposal's hosted jobs reached them.

## What Changes

- The GitHub supply step takes the native tools to stage as a list, `["vale"]` by default. The
  release runtime job stages `["vale", "syft"]`.
- A projection test requires every GitHub job that runs `nox -s supply_chain` to stage Syft.
- The fix ships on main as a workflow change. The existing tag `v0.2.0-beta.3` is released again
  from it: the release jobs check out the tag and verify `release_head`, and only the workflow comes
  from main.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Which tools a hosted job stages changes no requirement, so `skip_specs: true` applies.

## Impact

`.config/ci/pipeline.cue`, its projection `.github/workflows/ci.yml`, and a test in
`tests/architecture/ci/`.
