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
- Mise 2026.11.6. Its locked install refused the locked Python archive for Linux arm64 in the
  supply image build, so Mise and its CI bootstrap stay at 2026.10.25 until that is understood.

## Decisions

1. One cutoff for every ecosystem: 2026-11-10T18:00:00Z.
2. npm moves with a full `npm install` and then `npm update`, both with `--ignore-scripts`,
   `--allow-remote=all` and `--before=<cutoff>`, in a scratch copy of `package.json` and
   `package-lock.json`. Once a direct pin changes, a `--package-lock-only` run drops the lock's
   entries for the bundled dependencies of the `npm` package. Every resolved URL must be the
   public registry.
3. uv moves with `uv lock --upgrade --exclude-newer=<cutoff>`, then a plain `uv lock` drops the
   persisted option.

## Risks / Trade-offs

- A new release can change tool behaviour. The full proof and hosted CI on both peers are the
  acceptance, and a regression is fixed or pinned in this Change with its reason.
