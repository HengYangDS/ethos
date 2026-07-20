# Design: admit official OpenSpec goal metadata

## Context

ETHOS owns a closed-shape compatibility reader for `.openspec.yaml` so local
lifecycle checks fail before host projections discover unsupported metadata.
Official OpenSpec 1.6 now emits `goal` from `openspec new change --goal`; the
closed shape drifted from that source.

## Goals / Non-Goals

**Goals:** Align the one shared metadata allowlist used by active-shape and
archive-closeout checks, retaining rejection of unrecognized keys.

**Non-Goals:** Do not convert metadata into an authority source or accept
provider-specific fields.

## Decisions

Add `goal` only to `ALLOWED_OPENSPEC_METADATA_KEYS`. Both archive and active
paths import that shared constant, so one bounded update preserves a single
compatibility policy.

Alternative: delete `goal` from generated change metadata. Rejected because it
breaks the official OpenSpec 1.6 creation workflow and reintroduces drift on
every new change.

## Risks / Trade-offs

- [Future OpenSpec metadata expands again] → the closed reader continues to
  fail with the exact unsupported key until a tested compatibility update.
