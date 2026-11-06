# Design

## Context

See [proposal.md](proposal.md). `changelog_errors` validates the entry against the release target,
and the release assembler publishes the entry as the release notes.

## Goals / Non-Goals

Goals:

- The notes tell adopters what changed, which upgrades were qualified, and what remains open.
- Adopters move to beta.5 without changing their kits or their declarations.

Non-goals:

- Repeating the Changes' designs. The entry names behavior, not implementation.
- The result schema 3 and the publication declaration's retired fields, which ship in beta.6.

## Decisions

- **A fix release before the breaking one.** The mise 2026.11.2 incompatibility blocks adopters
  now. Coupling its fix to a change that breaks their kits would make the urgent move harder, so
  beta.5 ships only what the adopter checks of 2026-11-06 qualified, plus `private-address-class`,
  which only narrows what the paradigm refuses.
- **Upgrade paths follow the fleet.** Governed adopters select 0.2.0-beta.4, 0.2.0-beta.2 and
  0.2.0-alpha.29, so the journey upgrades from, and rolls back to, each of them.
- **Known defects stay visible.** The entry lists every advisory that the release build's audit
  reports.

## Risks / Trade-offs

- The entry's dates and journey claims must match the release run. The release readback checks the
  published notes against the entry.
