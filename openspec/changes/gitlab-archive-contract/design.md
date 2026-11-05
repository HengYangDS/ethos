# Design

## Context

See [proposal.md](proposal.md).

## Goals / Non-Goals

Goals:

- One contract for the GitLab archive in every test that reads it.

Non-goals:

- Any change to the projection itself.

## Decisions

- **Invert the assertion.** The line that required `build/artifacts/python/` now requires its
  absence; the dedicated test keeps the general rule for every GitLab job.

## Risks / Trade-offs

- None found.
