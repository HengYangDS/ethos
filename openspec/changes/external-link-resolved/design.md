# Design

## Context

See [proposal.md](proposal.md). The gate treats any lychee stderr as a failure, so a redirect hint
fails it even with no broken link.

## Goals / Non-Goals

Goals:

- The external link gate passes on the current documents.

Non-goals:

- Any change to the gate. Its strictness keeps link drift visible, and the hint names the fix.

## Decisions

- **Follow the permanent redirect.** A 308 is permanent, so the resolved address replaces the old
  one in the link reference.

## Risks / Trade-offs

- Another redirect can appear at any time; the advisory hosted job reports it, as it did this one.
