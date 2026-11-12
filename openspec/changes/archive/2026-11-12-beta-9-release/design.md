# Design

## Context

See [proposal.md](proposal.md). `changelog_errors` validates the entry against the release target,
and the release assembler publishes the entry as the release notes.

## Goals / Non-Goals

Goals:

- The notes name the fix and who needs it, the breaking moves, which upgrades were qualified, and
  what remains open.
- An adopter on beta.8, beta.7, beta.6, beta.5, beta.2 or alpha.29 makes one move to beta.9.

Non-goals:

- History-rebuild landing 2, `source-budget-roles` and the first-hour batch, which follow later.

## Decisions

- **A fix release now.** D19 admits a fix beta for a defect that blocks landing, and a handed-off
  lane could not land.
- **OpenSpec 2.0 rides on it as D19's recorded exception.** On 2026-11-12 the owner asked for
  OpenSpec 2.0 in ETHOS and every governed repository at once, allowed an exception so that it
  need not wait, and allowed breaking changes. This release therefore carries `openspec-2-move`
  without waiting for the weekly batch, and before the 24-hour release age that 2.0.0 meets at
  2026-11-12T22:41:44Z; the exception covers that package alone.
- **Upgrade paths follow the fleet.** The journey upgrades from 0.2.0-beta.8, the fleet's newest
  selection, and from beta.7, beta.6, beta.5, beta.2 and alpha.29, which adopters still select.
- **Known defects carry over.** beta.8's known open defects stay listed until a Change fixes them;
  the entry lists every advisory the release build's audit reports.

## Risks / Trade-offs

- The entry's dates and journey claims must match the release run. The release readback checks the
  published notes against the entry, and the upgrade bullet is confirmed by the journey's receipt.
