# Design

## Context

See [proposal.md](proposal.md). `src/ethos/repository/release/changelog.py` owns the changelog
grammar and reports uncategorized content in an entry.

## Goals / Non-Goals

Goals:

- Keep both notes and satisfy the grammar.

Non-goals:

- Any change to the grammar.

## Decisions

- Each note becomes the first `Changed` bullet of its own entry. Every line below the beta.1 note
  stays byte-identical to the released tree.

## Risks / Trade-offs

- None beyond the reordering.
