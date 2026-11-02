# Proposal

## Why

`tests/architecture/test_ci_provider_projections.py` starts real tools and bounds each wait with a
literal that the declared timeouts do not govern: 10 seconds for the ETHOS CLI and for the
hermetic toolchain bootstrap, 5 for a projected shell step, 15 for `cue fmt`, 30 for the
projection render and 60 for a pytest collection. On 11-02 the GitLab job 63524 of pipeline 13710
failed the 10-second wait for `python -m ethos.cli hook commit-range --help` on the Linux arm64
runner while its host's load average was about 38; GitHub passed the same commit.

## What Changes

- Each of these waits uses the declared tool deadline, `timeout.tool_seconds` (60 seconds by
  default), which bounds one tool run everywhere else.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Only a test's own deadlines change and no requirement names them, so `skip_specs: true`
applies.

## Impact

`tests/architecture/test_ci_provider_projections.py` only. No product, lock or adopter change.
