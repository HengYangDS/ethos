# Proposal

## Why

The ARM64 CI supply image no longer builds. GitHub run `40294783483` fails in the image's prepare stage at `mise install --locked cue github:rhysd/actionlint go`, with "No lockfile URL found" for `linux-arm64`, although `.config/mise/mise.lock` records those URLs.

- A Docker build has no CI environment and no mise trust record. ETHOS's isolated resolution therefore finds the root untrusted and carries no trust to its copy. It then runs mise in safe mode, and outside CI mode mise ignores an untrusted copy's lock.
- GitHub and GitLab jobs set `CI=true`, which makes mise trust their configuration. The image build that prepares their supply did not.
- The failure surfaced now because `6e4092a5e` changed the mise configuration and lock, which invalidated the cached prepare layer.

Meanwhile GitLab job `60546` fails, because the input hashes in the pinned images no longer match the checkout.

## What Changes

- The prepare and smoke stages of `.config/ci/supply/Dockerfile` declare `CI=true`, as the CI jobs they supply do.
- The shipped supply stage does not declare it, because jobs set it themselves. `--locked` resolution and the checksums stay.
- After landing, a published `supply_image` build on `dev` yields a new image digest. The pinned GitLab supply digests then move to it. These are this Change's delivery obligations.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- None. The requirement "Hosted supply preparation precedes expensive verification" keeps its behavior; this Change restores the image that satisfies it.

## Impact

- Files: `.config/ci/supply/Dockerfile`, then the pinned supply digests in the CI projection source and `.gitlab-ci.yml`.
- ETHOS reads `CI` for dependency acceptance only in the dependency-audit gate, which these stages do not run.
- Out of scope: ETHOS's trust carriage (`carried_trust`), which stays as accepted in 0.2.0-alpha.14.
