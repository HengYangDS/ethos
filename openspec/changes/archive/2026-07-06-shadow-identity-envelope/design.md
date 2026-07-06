# Design

## Context

Shadow parity already compares status, plan, prove, report, quality,
assistants, playbooks, land, and publish command projections. That comparison is
necessary but insufficient for external >= embedded because a diff is only
meaningful when both sides are run from the same input frame.

## Decision

Executed shadow parity reports include an `identity` envelope:

- `target_root`
- `target_head`
- `product_head`
- `changed_paths`
- `commands`
- `external_commands`
- `embedded_commands`
- `evidence_inputs`

Evidence input digests are computed for generic repository governance roots such
as `.ethos/profile.toml`, `rules`, `claims`, `evidence/claims`, `openspec`, and
tracked evidence roots when present. The list is generic and path-optional:
missing roots are omitted instead of becoming universal layout requirements.

## Follow-ups

This change creates the identity carrier. Later retirement-readiness work should
turn identity mismatches into explicit blocking false-negative tests for
alphasim-dmgr and add rollback-window evidence gates.
