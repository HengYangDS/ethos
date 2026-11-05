# Design

## Context

See [proposal.md](proposal.md). The distribution specification and DR-0015 promote a prerelease to
beta by evidence on the declared journeys. Semantic Versioning orders every `0.2.0-beta.N` after
every `0.2.0-alpha.N`, so later prereleases on this line are betas.

## Goals / Non-Goals

Goals:

- Ship alpha.30's code as `0.2.0-beta.1`.
- Tag it only after alpha.30's release journeys passed and this head's hosted verification passed.

Non-goals:

- Any product change. Those land in later betas.

## Decisions

- The version carriers and the release entry are the only changes, so this head's proof and hosted
  runs verify the same code that alpha.30 published.
- The tag waits on two pieces of evidence: alpha.30's release run with both journey legs passed,
  and this head's hosted runs on every supported platform. If either fails, this Change does not
  land, and the defect ships in a later prerelease.

## Risks / Trade-offs

- A journey failure in alpha.30's release run delays beta.1 until a fixed prerelease publishes.
