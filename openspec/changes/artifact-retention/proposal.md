# Proposal

## Why

Hosted CI artifacts accumulate without bound. No generated pipeline declares how long an artifact
is kept: `.config/ci/pipeline.cue` and `.github/workflows/ci.yml` hold no `retention-days`, and
`.gitlab-ci.yml` holds no `expire_in`, against seven `actions/upload-artifact` steps and three
GitLab `artifacts` blocks. Each Forge therefore keeps every artifact for its own default. The
measurement behind the owner's direction found 3,463 live GitHub Actions artifacts holding 81 GiB
on ETHOS's own repository, and GitLab job artifacts kept 30 days by the instance default.

The common CI model, `.config/ci/verification.cue`, has the same gap. Every repository that
compiles its pipelines from that model gets one upload step in its GitHub verification job and one
`artifacts` block per GitLab runner and trust class, none with a retention, and the model's closed
job definition gives a repository no place to add one.

The owner directed this Change on 2026-11-14 for the beta.11 batch and approved a retention of 14
days.

## What Changes

- `.config/ci/pipeline.cue` declares the retention once, as 14 days, and every upload step and
  every GitLab `artifacts` block reads that declaration. The generated workflow carries
  `retention-days: 14` on each upload step, and the generated GitLab pipeline carries
  `expire_in: 14 days` on each `artifacts` block.
- The common CI model declares the same retention once and carries it on the upload step and the
  `artifacts` block of every verification job it generates. A repository receives it when it
  regenerates its projections with the release that ships this Change.
- An architecture test asserts the value on every upload step and every `artifacts` block of
  ETHOS's two projections, and the common model's test asserts it on the generated jobs.
- A model comment that said the release job downloads the Python distributions is corrected: no
  job downloads them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: ADDED requirement `Hosted artifacts expire after one declared retention`.

## Impact

`.config/ci/pipeline.cue`, `.config/ci/verification.cue`, the two generated projections, two test
modules and a CHANGELOG line. No product or tool code changes. Not Breaking: a repository that
compiles the common model regenerates its projections after it moves to the release, as it does for
any change of that model. An artifact uploaded before the change keeps the retention it was uploaded
with.
