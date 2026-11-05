# Design

## Context

See [proposal.md](proposal.md). The distribution specification promotes a prerelease to beta by
evidence on its declared journeys. A beta's journey must start from the previous release and from
every earlier published release that a governed adopter still selects. On 2026-11-06 at 01:03, six
adopters ran 0.2.0-beta.2 and six ran 0.2.0-alpha.29; none ran 0.2.0-alpha.30.

## Goals / Non-Goals

Goals:

- Ship the landed Changes as `0.2.0-beta.3`, proven once on the archived head.
- Qualify the direct upgrade from both live lines, so the alpha.29 adopters move once.

Non-goals:

- Any product change. Later work lands in later betas.

## Decisions

- The version carriers and the release entry are this Change's only edits.
- After publication, a `journey_tag=v0.2.0-beta.3` dispatch with
  `journey_previous=v0.2.0-beta.2,v0.2.0-alpha.29` provides the adopter-journey evidence. The set
  is rechecked against the adopters right before the dispatch.

## Risks / Trade-offs

- The release run's own journey legs upgrade only from the previous release. The dispatch above
  covers the alpha.29 line, so the beta is not announced to alpha.29 adopters before it passes.
