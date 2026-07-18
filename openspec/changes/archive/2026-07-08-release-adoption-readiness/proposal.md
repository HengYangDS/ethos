---
subject: ethos:release-adoption-readiness
reuse: extend
change: record
facet:lifecycle: release
facet:surface: adoption
facet:authority: evidence
---

# Release And Adoption Readiness Evidence

## Why

ETHOS needs a current, tracked evidence packet for local publish readiness,
release artifact smoke checks, and external repository adoption pilots. Temporary
build logs and `/tmp` pilot repositories are not repository truth until their
bounded results are summarized into evidence and claim surfaces.

## What Changes

- Record current product HEAD, candidate/origin alignment, and local
  `local_publish_ready` status.
- Record release build, npm launcher smoke, artifact SHA-256 digests, and
  release attestation tag.
- Record generic, Python, and GitLab external adoption pilots.
- Preserve the GitLab non-empty `.gitlab-ci.yml` conflict as a guard outcome.
- Separate local readiness, remote ref alignment, and hosted CI observation.

## Out Of Scope

- No package registry upload.
- No remote push is performed by this evidence packet.
- No hosted CI success is claimed without a separately observed pipeline.
