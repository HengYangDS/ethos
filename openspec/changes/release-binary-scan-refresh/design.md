# Design

## Context

See [proposal.md](proposal.md). GitLab jobs check the checkout's locks against the bound image's
manifest, so an image is valid only for the exact locks it was built from.

## Goals / Non-Goals

Goals:

- GitLab jobs run on an image built from this lane's merged locks.

Non-goals:

- Any change to the image's recipe.

## Decisions

- Neither side's digest is kept as final: each was built from locks that the merge replaced.
- The rebuilt image is dispatched from this lane's proposal after the merge, then bound with the
  native bind and projection.

## Risks / Trade-offs

- Every lane that moves a lock and refreshes after another such lane needs one more image build. The
  candidate Change `supply-image-currency` makes the stale binding fail in seconds instead of on
  GitLab.
