# Design

## Context

See [proposal.md](proposal.md). The coordinator decided on 2026-11-05 that a byte mismatch is a
conflict and belongs to the producer, not to the reducer that `cause-preserving-results` fixed.

## Goals / Non-Goals

Goals:

- A drifted generated artifact, upstream member or received archive blocks with its own code.

Non-goals:

- Changing what the provider compares, or the native archive helper. A member mismatch that the
  native helper (`archive.mjs`) finds still reaches the provider as an unqualified archive, so it
  stays `unknown` until the helper reports its own code.

## Decisions

- The provider raises a mismatch as a `refusal` with verdict `block`, and keeps every other
  refusal as before. Its handler reads the carried outcome: a `block` outcome reports its own
  gaps, and anything else reports `source_integrity_unproven:<path>` for every declared member.
- The three mismatch codes are the ones the provider already composes, so no consumer learns a
  new code.

## Risks / Trade-offs

- A drifted artifact's proof changes from `unknown` to `block`. Both are non-pass, so only
  scripts that match the verdict exactly notice.
