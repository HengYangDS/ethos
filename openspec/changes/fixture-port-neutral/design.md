# Design

## Context

See [proposal.md](proposal.md). The test proves that a local `remote.<name>.forgeRepository`
locator reaches the native GitLab client, including a non-default port in `GITLAB_HOST`.

## Goals / Non-Goals

Goals:

- No real peer port in ETHOS's current tracked content.

Non-goals:

- Rewriting history, which the history rebuild track owns.

## Decisions

- **A neutral port.** `8443` is non-default and identifies no peer.

## Risks / Trade-offs

- None; the assertion keeps its meaning.
