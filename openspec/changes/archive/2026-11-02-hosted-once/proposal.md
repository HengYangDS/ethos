# Proposal

## Why

GitHub runs the full verification twice for every published commit. A landing publishes `dev` and
then `main` at the same accepted commit, and both pushes start the whole workflow: ten
host-conformance legs, the quality gates, external links, the repository proof and the package
artifacts. At `424d32538` the `dev` run took 317.1 job-minutes (run 41482302947) and the `main`
run 324.8 (run 41482827700), so one published commit cost 641.9. The second run verifies nothing
the first did not, and it competes for the same hosted capacity: on 11-03 GitHub's macOS arm64
pool cancelled a leg of each run ("not acquired by Runner of type hosted"), and both had to be
rerun.

GitLab already verifies a commit once. Its commit-scoped jobs carry `rules:changes:compare_to:
refs/heads/dev`, so a `main` push with `dev`'s tree runs only `ethos:commit-policy`
(`80d53f1ff`). The approved end-state design routes the GitHub half to this Change as decision
D11: one hosted run per plane per published commit, at most 320 job-minutes.

## What Changes

- A push to `main` on GitHub no longer runs the commit-scoped jobs: host conformance, quality
  gates, external links, repository proof and package artifacts. `main` moves only to the exact
  accepted commit, which `dev`'s run of the same commit verifies.
- A new `commit policy` job admits the range of every `main` push, as the quality gates already do
  for `dev` and proposal pushes, so every pushed ref keeps its hosted commit-range admission.
- Pull requests, `dev` and proposal pushes, the supply-image dispatch and the release dispatch are
  unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: hosted verification runs a published commit's commit-scoped jobs once on each Forge.

## Impact

`.config/ci/pipeline.cue`, the generated `.github/workflows/ci.yml`, a structural test beside
`tests/architecture/ci/test_gitlab_commit_scope.py`, and `CHANGELOG.md`. No product code, adopter
configuration or GitHub ruleset changes.
