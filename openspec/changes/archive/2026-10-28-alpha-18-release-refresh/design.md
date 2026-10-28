# Design

## Context

See [proposal.md](proposal.md). `VERSION` already names `0.2.0-alpha.18`. The accepted `dev`,
`2c6018b27`, carries both retention fixes, `retention-selection-window` and
`retention-observes-consumers`. Its hosted predecessor `bb242fd35`, which carries the first fix,
passed every hosted job, including Windows host conformance on Python 3.12, 3.13 and 3.14.

## Goals / Non-Goals

**Goals:**

- An `0.2.0-alpha.18` entry that names every user-visible product change the tag carries and the
  known advisories in its shipped bytes.

**Non-Goals:**

- Upgrading uv. No uv release embeds rustls 0.23.46 yet; the bump and the matching of embedded
  crates belong to `bounded-supply-and-state`.
- Changing the `0.2.0-alpha.17` entry. Historical entries keep their recorded text.

## Decisions

- **One note for the retention fix.** The follow-up corrected behavior that no release carried, so
  the entry describes the final behavior once.
- **The advisories go under Security, with their scope.** The dependency gate audits the locked
  Python and Node packages, not the crates inside a package's binary, so these advisories pass it.
  The note names the shipped component, the advisories, the fixing rustls version, the absence of a
  uv release that embeds it, and that `v0.2.0-alpha.17` ships the same uv.
- **The date is the tag date.** Release dates are local dates, and the tag waits for hosted Windows
  host conformance on the landed head.

## Risks / Trade-offs

- [A uv release that embeds rustls 0.23.46 appears before the tag] → The release still ships
  the locked 0.13.5; the bump goes through a supply Change and the next release.
- [Hosted Windows host conformance fails again on the landed head] → No tag; the failure is
  diagnosed from its producing source before anything else lands.
- [A repository still runs an earlier release] → It keeps the old retention window until it
  rebinds; the note says so.
- [GitLab hosted jobs refuse the stale supply image] → The release does not wait for it; the supply
  owner rebuilds and rebinds it from an accepted head.
