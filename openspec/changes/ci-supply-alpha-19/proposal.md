# Proposal

## Why

GitLab verification refuses every checkout since the `0.2.0-alpha.19` changes: the commit-policy job's
supply manifest check fails on `package-lock.json` and `.config/checks/ci-projection/policy.toml`,
which the re2js override and the shared obligations changed after the bound supply was published.
Publishing the supply for the accepted checkout and binding it restores GitLab execution while
keeping the input check that detected the mismatch.

## What Changes

- Publish the locked Linux ARM64 supply from the accepted checkout through the existing
  `supply_image` workflow and its offline smoke stage.
- Bind its verified digest in the existing CUE CI source and regenerate the provider projection.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is a supply refresh with no requirement change, so `skip_specs: true` applies.

## Impact

- Owners: `.config/ci/pipeline.cue` and its generated `.gitlab-ci.yml`.
- The Dockerfile, tool declarations, lockfiles, manifest validation, offline bootstrap and product
  runtime contract keep their behavior.
