# Design

## Context

See the [proposal](proposal.md). ETHOS locks only releases that have been public for at least 24
hours. One cutoff serves every ecosystem: uv applies it with `--exclude-newer` and npm with
`--before`, and tool and Mise releases must be at least as old. The CI supply image is built from
the committed locks on the lane's proposal ref and bound by digest.

## Goals / Non-Goals

Goals: every locked supply at its newest stable release under one cutoff.

Non-Goals:

- CUE, Vale and shfmt, which have no release built with a fixed Go yet.
- Any prerelease channel, and releases younger than the cutoff.
- The Mise lockfile format: the lock keeps its revision, since no `mise lock --upgrade` runs.

## Decisions

1. One cutoff for every ecosystem: 2026-11-10T18:00:00Z.
2. The Mise floor and the CI bootstrap version move together, because CI bootstraps the floor's
   version. The six executable digests are the official release assets' SHA-256 values.
3. npm moves with `npm update --package-lock-only --before=<cutoff> --ignore-scripts`, after the
   direct pins move. uv moves with `uv lock --upgrade --exclude-newer=<cutoff>`, then a plain
   `uv lock` drops the persisted option.

## Risks / Trade-offs

- A new release can change tool behaviour, in particular Mise 2026.11.x's safe and locked modes,
  which ETHOS uses. The full proof and hosted CI on both peers are the acceptance, and a regression
  is fixed or pinned in this Change with its reason.
