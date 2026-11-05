# Design

## Context

See [proposal.md](proposal.md). The distribution specification and DR-0015 promote a prerelease to
beta by evidence on the declared journeys. beta.1 ships alpha.30's code; beta.2 is the first beta
with new product code.

## Goals / Non-Goals

Goals:

- Ship the four Changes of this lane as `0.2.0-beta.2`, proven once on the archived head.
- Tag it after beta.1's tag, and only after this head's hosted verification passed on every
  supported platform.

Non-goals:

- Any product change beyond the four Changes. Later work lands in later betas.
- The Python packages that turn 24 hours old after this head is proven. They move in the next
  supply step.

## Decisions

- The version carriers and the release entry are this Change's only edits. The four Changes own
  their code, tests and specification deltas, and archive before this one.
- The release run's journey legs on macOS and Linux are this beta's adopter-journey evidence.
  A `journey_tag` dispatch re-runs them alone when hosted capacity cancels a leg.

## Risks / Trade-offs

- GitHub's macOS arm64 runners lacked capacity on the evening of 2026-11-04. Three attempts of
  alpha.30's macOS journey were cancelled before a runner took them. beta.1's tag waits for that
  leg, and beta.2's tag follows beta.1's, so a long shortage delays both.
