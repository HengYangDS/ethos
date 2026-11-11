# Design

## Context

See [proposal.md](proposal.md). `changelog_errors` validates the entry against the release target,
and the release assembler publishes the entry as the release notes.

## Goals / Non-Goals

Goals:

- The notes tell adopters and their agents what breaks, the one repair each break needs, which
  upgrades were qualified, and what remains open.
- Each adopter makes one move from beta.6, beta.5, beta.2 or alpha.29 to beta.7.

Non-goals:

- Repeating the Changes' designs. The entry names behavior, not implementation.
- `history-rebuild-map`, whose first landing follows beta.7 within schema 3.

## Decisions

- **Every break names its repair.** The catalog's Breaking lines name the refused form and the
  accepted one, such as `hook install` without `--authorize` unless the state is reset.
- **Fixes of listed defects are named.** Three of beta.6's known open defects were fixed after the
  beta.6 tag without a CHANGELOG line, and the entry names them as fixed. The npm advisories stay a
  known open defect: the locked production `npm` still bundles the affected glob and minimatch.
- **Upgrade paths follow the fleet.** Governed adopters select 0.2.0-beta.6, 0.2.0-beta.5,
  0.2.0-beta.2 and 0.2.0-alpha.29, so the journey upgrades from each of them, dispatched with that
  list after the release.
- **Known defects stay visible.** The entry lists every advisory that the release build's audit
  reports, and the open defects in the register that a user can meet.

## Risks / Trade-offs

- The entry's dates and journey claims must match the release run. The release readback checks the
  published notes against the entry, and the upgrade bullet is confirmed by the journey's receipt.
