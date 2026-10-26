# Tasks

## 1. Supply Image Build

- [ ] 1.1 Reproduce the failure. Done when the local `linux/arm64` smoke build of `.config/ci/supply/Dockerfile` at `2ee966d46` fails in prepare with "No lockfile URL found".
- [ ] 1.2 Declare `CI=true` in the prepare and smoke stages. Done when the same local smoke build passes, including its offline acceptance and the pinned pytest selection.

## 2. Delivery

- [ ] 2.1 Publish the landed fix and build the image with the hosted `supply_image` workflow on `dev`. Done when the run passes and records the new digest.
- [ ] 2.2 Pin that digest for every GitLab supply job through the CI projection owner. Done when the projection is current and the GitLab jobs' input hashes match.
- [ ] 2.3 Confirm hosted verification on both peers at the landed head. Done when GitHub and GitLab both report green for it.

## Workflow follow-up

- Land with section 1 complete and section 2 open. A later lane completes section 2, archives this Change and lands.
