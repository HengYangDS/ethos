# Lane Status Coordination Summary Design

## Context

`workspace_status` already owns Work Lane coordination truth. `ethos lane status`
is the focused reader view for that topology, so its summary should expose the
same coordination small signals without becoming a lifecycle owner.

## Design

The CLI builds `lane status` summary through a small helper that reads the
already-computed status payload. Values owned by `data.coordination` mirror that
package directly: foreign count, unbound count, missing lease count, advisory
count, blocking flag, and next action. Dirty foreign lane count is derived from
the emitted foreign lane records because dirty state belongs to each lane entry.

The top-level `next_actions` remain bounded reader guidance. Advisory signals
continue to route to `ethos orient --json` and `ethos lane status --json`; work,
land, retire, or cleanup authority remains with the lane owner, handoff, or
maintainer break-glass evidence.

## Alternatives

- Adding another coordination command was rejected because `status`, `orient`,
  and `lane status` already own the reader views.
- Making advisory signals blocking was rejected because foreign lanes are normal
  in multi-agent work and should not block an otherwise clean accepted root.
- Duplicating coordination computation in the CLI was rejected; the CLI only
  lifts existing payload fields.

## Proof Strategy

- Unit tests verify the helper lifts coordination fields from a status payload.
- CLI regression tests verify emitted summary fields match `data.coordination`
  and do not grant mutation authority.
- Docs and OpenSpec are updated with the current command contract.
- Focused tests, lint, OpenSpec lifecycle, report, and executed proof gate the
  lane before landing.
