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
  lane could not land; the owner's OpenSpec 2.0 decision rides on the same release.
- **Upgrade paths follow the fleet.** The journey upgrades from 0.2.0-beta.8, the fleet's newest
  selection, and from beta.7, beta.6, beta.5, beta.2 and alpha.29, which adopters still select.
- **Known defects carry over.** beta.8's known open defects stay listed until a Change fixes them;
  the entry lists every advisory the release build's audit reports.

## Risks / Trade-offs

- The entry's dates and journey claims must match the release run. The release readback checks the
  published notes against the entry, and the upgrade bullet is confirmed by the journey's receipt.
