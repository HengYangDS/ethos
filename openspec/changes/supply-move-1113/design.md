# Design

## Context

See the [proposal](proposal.md). ETHOS locks only releases that have been public for at least 24
hours. One cutoff serves every ecosystem: uv applies it with `--exclude-newer`, and tool and image
releases must be at least as old. The CI supply image is built from the committed locks on the
lane's proposal ref and bound by digest.

## Goals / Non-Goals

Goals: every locked supply at its newest stable release under one cutoff.

Non-Goals:

- Mise 2026.11.x, until the 2026.11.6 refusal of the locked Linux arm64 Python archive is
  understood.
- Prettier 3.10, whose layout change across the governed repositories needs its own fleet scan.
- Any prerelease channel, and releases younger than the cutoff.

## Decisions

1. One cutoff for every ecosystem, recorded in the tasks: 24 hours before the lock step.
2. uv moves with `uv lock --upgrade --exclude-newer=<cutoff>`, then a plain `uv lock` drops the
   persisted option, and `uv lock --check` passes.
3. The Mise lock keeps its revision: only the moved tools' entries change.

## Risks / Trade-offs

- A new release can change tool behaviour: `ty` 0.0.101 can report new diagnostics. The full proof
  and hosted CI on both peers are the acceptance, and a regression is fixed or pinned in this
  Change with its reason.
