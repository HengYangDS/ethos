# Tasks

## 1. Supply Image Build

- [x] 1.1 Reproduce the failure. Done when the local `linux/arm64` smoke build of `.config/ci/supply/Dockerfile` at `2ee966d46` fails in prepare with "No lockfile URL found" (local smoke build at `2ee966d46`: go, actionlint and cue refused with "No lockfile URL found" for linux-arm64; `build/evidence/supply-image-ci-mode/red-build.log`).
- [x] 1.2 Declare `CI=true` in the prepare and smoke stages. Done when the same local smoke build passes, including its offline acceptance and the pinned pytest selection (the same build passes: `build/evidence/supply-image-ci-mode/green-build.log`).

## 2. Delivery

- [x] 2.1 Publish the landed fix and build the image with the hosted `supply_image` workflow on `dev`. Done when the run passes and records the new digest (run `40350486410` passed and published `ghcr.io/hengyangds/ethos-ci-supply@sha256:fc65dd70…`; the first dispatch, run `40341345307`, was refused at the push until the package granted this repository write access).
- [x] 2.2 Pin that digest for every GitLab supply job through the CI projection owner. Done when the projection is current and the GitLab jobs' input hashes match (`.config/ci/pipeline.cue` and its `.gitlab-ci.yml` projection pin that digest, and `lane project --check` passes; run `40350486410` checked the image manifest against `57641887a`, whose hashed inputs this lane leaves unchanged).

## Workflow follow-up

- Section 1 landed at `57641887a`; section 2 lands with the archive of this Change.
- Hosted green on both peers at the landed head; owner: the alpha.16 release gate; unverified at archive.
