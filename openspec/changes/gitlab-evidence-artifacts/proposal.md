# Proposal

## Why

GitLab proposal pipeline 14296 for `df2dba636` failed in its `ethos:verify` job although its
verification passed: `hosted_verification` succeeded in 40 minutes with 34 gates and 95.0%
coverage. The upload of the job's `archive` artifacts then failed with
`413 Request Entity Too Large`. The archive holds `build/artifacts/python/`, whose platform wheel
is about 101 MB, and, since `release-binary-scan`, about 12 MB of SBOM evidence in
`build/evidence/release/`. Together they exceed the GitLab instance's artifact limit. Every GitLab
verify fails the same way until the archive shrinks.

No GitLab job consumes the Python distributions, and GitLab publishes no release. On GitHub the
same files form the `python-distributions` artifact that the release job downloads, so GitHub keeps
them.

## What Changes

- The GitLab verify job's archive keeps its evidence and drops `build/artifacts/python/`.
- A CI projection test requires every GitLab archive path to be evidence, never a build output
  under `build/artifacts/`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Which files a hosted job archives changes no requirement, so `skip_specs: true` applies.

## Impact

`.config/ci/pipeline.cue`, its projection `.gitlab-ci.yml`, and a new
`tests/architecture/ci/test_gitlab_artifacts.py`.
