# Design

## Context

See [proposal.md](proposal.md). The GitLab supply image carries a manifest of the locks it was built
from, and each GitLab job refuses a checkout whose locks differ. So a lock move needs a rebuilt and
rebound image in the same lane.

## Goals / Non-Goals

Goals:

- GitLab jobs run on an image whose locks match the head.

Non-goals:

- Any change to the image's contents beyond the moved lock.

## Decisions

- Dispatch the existing `supply_image` workflow on this lane's proposal, and bind the digest it
  pushed in `.config/ci/pipeline.cue`. The GitLab projection is regenerated from it.

## Risks / Trade-offs

- An earlier lane head's GitLab run stays red. Only the bound head is acceptance evidence.
