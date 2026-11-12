# Proposal

## Why

The documentation registry admits `how-to`, `reference` and `explanation`, three of the four
documentation kinds that Diátaxis defines, but not the fourth, `tutorial`: a learning-oriented page
that takes a newcomer through a first success, distinct from a task-oriented how-to. A governed
repository that adds a tutorial refuses `invalid_role:<path>:tutorial` and must misfile it as a
how-to. The owner asked governed repositories to follow industry practice, and a per-repository
taxonomy extension would be a per-repository exception.

## What Changes

- The registry's default roles admit `tutorial`.
- The configuration reference names tutorials among the pages under `docs/`.
- The Unreleased entry gains an Added line.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No specification enumerates the document roles; the registry owns the list, so
`skip_specs: true` applies.

## Impact

`src/ethos/repository/registry/docs/registry.py`, its tests, `docs/reference/configuration.md` and
`CHANGELOG.md`.
