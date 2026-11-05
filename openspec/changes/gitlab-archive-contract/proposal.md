# Proposal

## Why

`gitlab-evidence-artifacts` dropped `build/artifacts/python/` from the GitLab verify archive, which
had overflowed the instance artifact limit. The full architecture suite then failed
`test_provider_commands_use_shared_owners_without_activating_mutation[gitlab]`. That test still
required the path in the archive, so it pinned the old contract.

## What Changes

- The provider projection test requires the GitLab verify archive to exclude the Python
  distributions, which matches `tests/architecture/ci/test_gitlab_artifacts.py`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A test that follows a changed archive list changes no requirement, so `skip_specs: true`
applies.

## Impact

`tests/architecture/test_ci_provider_projections.py`.
