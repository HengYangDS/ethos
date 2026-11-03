# Proposal

## Why

`ci-emulation-retirement` removed the emulator fields of the projection policy, and with them the
only declaration that owned Docker: an `emulator_image` entry made `docker` an owned executable and
reference in every file. ETHOS's pipelines still use Docker. The GitHub `supply_image` job runs
`docker buildx`, and every GitLab job names an `image:`, which the runner's Docker executor runs.
Reference closure therefore reports two orphan consumers, and the proof of the archived head
stopped at the `product-boundary` gate.

The same Change edited `.config/checks/ci-projection/policy.toml`, one of the eight inputs that the
supply image's manifest hashes. The GitLab `commit-policy` job refused the proposal in pipeline
13788 because the bound image no longer matches the checkout.

## What Changes

- Declare `docker` in `.config/ci/runners.toml`: an executable of the GitHub runner and a reference
  of the GitLab runner. Admission then owns each one only in that Forge's pipeline files.
- Bind the supply image that the hosted `supply_image` workflow built from the proposal at
  `b350f258e` in `.config/ci/pipeline.cue`, and regenerate `.gitlab-ci.yml`.
- `docs/reference/configuration.md` states that the runner declaration names references as well as
  executables.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The runner requirement already permits these declarations, so `skip_specs: true` applies.

## Impact

`.config/ci/runners.toml`, `.config/ci/pipeline.cue`, the generated `.gitlab-ci.yml` and one
reference document. No product code, lock or release entry changes.
