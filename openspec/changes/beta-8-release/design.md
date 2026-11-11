# Design

## Context

See [proposal.md](proposal.md). `changelog_errors` validates the entry against the release target,
and the release assembler publishes the entry as the release notes.

## Goals / Non-Goals

Goals:

- The notes name the fix and who needs it, which upgrades were qualified, and what remains open.
- An adopter on beta.7, beta.6, beta.5, beta.2 or alpha.29 makes one move to beta.8.

Non-goals:

- `history-rebuild-map` and `source-budget-roles`, which follow in beta.9.

## Decisions

- **A fix release now.** One adopter's redaction and first release are blocked on the fix, so the
  release does not wait for the larger Changes.
- **Upgrade paths follow the fleet.** The journey upgrades from 0.2.0-beta.7, the fleet's newest
  selection once adopters bind it, and from beta.6, beta.5, beta.2 and alpha.29, which adopters
  still select, dispatched with that list after the release.
- **Known defects carry over.** beta.7's known open defects stay listed until a Change fixes them;
  the entry lists every advisory the release build's audit reports.

## Risks / Trade-offs

- The entry's dates and journey claims must match the release run. The release readback checks the
  published notes against the entry, and the upgrade bullet is confirmed by the journey's receipt.
