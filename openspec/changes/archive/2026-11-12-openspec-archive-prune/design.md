# Design

## Context

See the [proposal](proposal.md). `repository-governance` says archived Changes "remain history" and
own no current queue, and that an archived Change is never rewritten when a fact is corrected. The
product design contract names Git ancestry and the official archive as history, and proof binds
acceptance at its exact source commit, whose tree keeps the archive it had.

## Goals / Non-Goals

Goals:

- The current tree holds the archive that current work reads; older Changes stay in Git.
- One stated rule, so a later prune follows the same test.

Non-Goals:

- Rewriting history, tags or any archived Change that stays.
- A schedule or automatic pruning; each prune is its own Change.
- Moving the removed Changes to another directory or store.

## Decisions

1. The cutoff is the owner's: every archive directory whose date prefix is before 2026-10-01.
2. A prune is admitted only when no tracked file outside the archive cites the removed directories;
   `git grep` over the current tree is the check, and its result goes into the task evidence. A
   citation inside another archived Change is history: the commits and tags that hold the citing
   Change also hold the cited one, and the citing Change is not rewritten.
3. A removed Change is cited, when needed, by release tag and path, for example
   `git show v0.2.0-beta.9:openspec/changes/archive/<name>/proposal.md`.

## Risks / Trade-offs

- A reader browsing the tree no longer sees September's Changes; the tags and history hold them.
- A tool that walks the archive sees fewer Changes; none in ETHOS depends on the walk.
