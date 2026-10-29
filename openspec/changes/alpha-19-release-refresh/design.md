# Design

## Context

See [proposal.md](proposal.md). `VERSION` already names `0.2.0-alpha.19`. The accepted `dev` and
`main`, `0ba9a7e44`, carry the prepared entry, and `dev`'s hosted push run on GitHub passed every
job, including Windows host conformance on Python 3.12, 3.13 and 3.14. The release build's audit on
that head passed with six findings that it classifies as unfixed upstream: npm 12.2.1, the latest
npm release, bundles undici 6.29.0 and ip-address 10.7.2, and undici 6.29.1 and ip-address 10.7.4
fix them.

## Goals / Non-Goals

**Goals:**

- An `0.2.0-alpha.19` entry that names the known advisories in the npm its wheels and installed
  runtimes ship, including the three that no entry has listed.

**Non-Goals:**

- Replacing npm's bundled packages. They ship inside npm's own package, and no npm release bundles
  the fixed versions yet; a replacement or the next npm release goes through a supply Change.
- Changing the `0.2.0-alpha.17` and `0.2.0-alpha.18` entries. Historical entries keep their
  recorded text; this entry states that both releases ship the same npm.

## Decisions

- **The note restates the whole known set.** It lists all six advisories with their packages, so a
  reader of this entry alone learns what the shipped npm carries; it names the three that no entry
  listed with their publication date.
- **The dependency gate's verdict stays.** Its policy reports a finding without blocking while the
  package that bundles it is its latest release, and the release audit classified all six that way;
  the note says so.
- **The entry keeps its date.** The tag follows the hosted runs of the refreshed head on the same
  local date, 2026-10-29.

## Risks / Trade-offs

- [An npm release that bundles the fixed undici and ip-address appears before the tag] → The
  release still ships the locked 12.2.1; the bump goes through a supply Change and the next release.
- [Another advisory is published between this proof and the tag] → The pre-tag audit reads the
  exact head again; a fixable finding stops the tag, and an unfixed one is added to the entry first.
- [GitLab hosted jobs refuse the stale supply image] → The release does not wait for it; the supply
  owner rebuilds and rebinds it from an accepted head.
