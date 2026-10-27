# Proposal

## Why

GitLab verification refuses the alpha.16 checkout because its immutable CI supply still binds alpha.15 npm release metadata. Refreshing that supply restores execution while preserving the input check that detected the mismatch.

## What Changes

- Publish the locked Linux ARM64 supply from the accepted checkout through the existing `supply_image` workflow and its offline smoke stage.
- Bind its verified digest in the existing CUE CI source and regenerate the provider projection.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- None. This is a supply refresh with no requirement change.

## Impact

- Owners: `.config/ci/pipeline.cue` and its generated `.gitlab-ci.yml`.
- The Dockerfile, tool declarations, lockfiles, manifest validation, offline bootstrap and product runtime contract retain their existing behavior.
- Reporter confirmation for issue #1 and the existing runtime retirement grace period remain separate acceptance boundaries.
