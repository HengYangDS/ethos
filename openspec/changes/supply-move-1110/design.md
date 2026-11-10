# Design

## Context

ETHOS's supply moves through its own lane and gates. The age floor is 24 hours, applied with
`uv --exclude-newer` and npm `--before`; tool and action releases must be at least as old. The CI
supply image is built from the committed locks on the lane's proposal ref and bound by digest.

## Goals / Non-Goals

Goals: every locked supply at its newest stable release under one cutoff.

Non-Goals: retiring shfmt, which is its own Change; any prerelease channel; releases younger than
the cutoff.

## Decisions

1. One cutoff for every ecosystem: 2026-11-09T04:45:00Z.
2. npm moves with `npm update --package-lock-only --before=<cutoff> --ignore-scripts`. The direct
   pins are already newest, so only transitive versions change.
3. Action pins move to the newest stable release's full commit SHA.

## Risks / Trade-offs

- A new release can change tool behaviour. The full proof and hosted CI on both peers are the
  acceptance, and a regression is fixed or pinned in this Change with its reason.
