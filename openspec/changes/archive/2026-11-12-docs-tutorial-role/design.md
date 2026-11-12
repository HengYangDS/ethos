# Design

## Context

See the [proposal](proposal.md). `DEFAULT_ROLE_VALUES` in the registry is the closed list of
document roles. Reader guidance applies to every role outside the observational `evidence` and
`history`, so a tutorial gets the same visible title and guidance checks as a how-to.

## Goals / Non-Goals

Goals: a governed repository can declare a tutorial as `role: tutorial`.

Non-Goals: a per-repository role extension, or a check of a tutorial's content.

## Decisions

1. `tutorial` joins the default roles beside `how-to`, with no other rule change.

## Risks / Trade-offs

None: the list only grows, and no page loses an admitted role.
