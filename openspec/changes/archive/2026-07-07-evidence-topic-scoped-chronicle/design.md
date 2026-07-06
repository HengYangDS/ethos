## Context

The official OpenSpec boundary is `repository-governance`; the repo-local truth
boundary is the tracked `evidence/` tree plus claim digest validation. The
terminal design already says closeout evidence should be topic-scoped, but the
physical tree still allowed root-level and flat chronicle Markdown.

## Design

Use the kernel chain directly: claim records stay in `evidence/claims/`, machine
parity proof stays in `evidence/parity/`, and judged human-readable history lives
under `evidence/chronicle/<topic>/<date>.md`. The topic is the stable evidence
subject; the date is the record instance. This keeps the root shallow and avoids
pre-creating taxonomy directories that have no records.

This is a relocation and boundary hardening, not a new truth store. Existing
claim digests continue to bind unchanged Markdown contents; only evidence paths
and promotion target paths move.

## Proof Strategy

- Architecture tests assert no loose root Markdown and no flat chronicle
  Markdown.
- Claim quality proof verifies moved paths still match their recorded digests.
- OpenSpec lifecycle validation proves the carrier shape.
- Full executed proof binds the final change to HEAD before land.
