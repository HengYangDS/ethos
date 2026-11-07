# Design

## Context

See [proposal.md](proposal.md). `changelog_errors` validates the entry against the release target,
and the release assembler publishes the entry as the release notes.

## Goals / Non-Goals

Goals:

- The notes tell adopters and their agents what breaks, the one repair each break needs, which
  upgrades were qualified, and what remains open.
- Each adopter makes one breaking move: it repairs its declaration once, and its kit reads the final
  `next` once.

Non-goals:

- Repeating the Changes' designs. The entry names behavior, not implementation.
- `command-forms`, `store-retention`, `peer-identity-records` and `history-rebuild-map`, which follow
  beta.6 within schema 3.

## Decisions

- **One breaking move.** Schema 3 and the retired declaration fields ship together, so no adopter
  kit moves twice. `next-wire-shape` closed the `next` vocabulary inside schema 3 before this tag,
  so later Changes add derivations, not wire fields.
- **The repair is named with its command.** An adopter runs `ethos lane repair-paradigm --apply` in
  a lane, and its declaration loses the retired fields. A rollback across that repair is refused
  until the predecessor's declaration is restored in a lane.
- **Upgrade paths follow the fleet.** Governed adopters select 0.2.0-beta.5, 0.2.0-beta.4,
  0.2.0-beta.2 and 0.2.0-alpha.29, so the journey upgrades from each of them.
- **Known defects stay visible.** The entry lists every advisory that the release build's audit
  reports. It also lists the open defects in the register that a user can meet.

## Risks / Trade-offs

- The entry's dates and journey claims must match the release run. The release readback checks the
  published notes against the entry.
