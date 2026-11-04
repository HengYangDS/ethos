# Design

## Context

See [proposal.md](proposal.md). The portfolio owner collects records from the normalized registry,
and checks coverage, design and retirement over those records only.

## Goals / Non-Goals

Goals:

- Every package under the Skills root has exactly one route: an active record or a retirement.

Non-goals:

- Validating the content of an unrouted package. Its route comes first.

## Decisions

- A package is a direct subdirectory of the Skills root that holds `SKILL.md`. It is routed when an
  active record's path lies in that directory, or when a retirement names that directory as its
  id.
- Run the check only when the registry loaded. A missing or invalid registry already blocks with
  its own gap, and listing every package again would only repeat it.

## Risks / Trade-offs

- A repository that keeps a draft package outside its registry now blocks until it routes or
  retires that package.
