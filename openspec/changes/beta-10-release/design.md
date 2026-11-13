# Design

## Context

See [proposal.md](proposal.md). `changelog_errors` validates the entry against the release target,
and the release assembler publishes the entry as the release notes.

## Goals / Non-Goals

Goals:

- The notes name the breaking moves, the security fix, which upgrades were qualified, and what
  remains open.
- An adopter on beta.9, alpha.29 or alpha.27, the selections the fleet holds, makes one move to
  beta.10.

Non-goals:

- The common-base design's Changes, which wait for the owner's approval.

## Decisions

- **The weekly batch.** D19 releases weekly; beta.10 is that batch, not a fix beta.
- **Upgrade paths follow the fleet.** The journey upgrades from 0.2.0-beta.9, the newest selection,
  and from alpha.29 and alpha.27, which adopters still select.
- **Known defects carry over.** beta.9's known open defects stay listed until a Change fixes them;
  the entry lists every advisory the release build's audit reports.

## Risks / Trade-offs

- The entry's dates and journey claims must match the release run. The release readback checks the
  published notes against the entry, and the upgrade bullet is confirmed by the journey's receipt.
