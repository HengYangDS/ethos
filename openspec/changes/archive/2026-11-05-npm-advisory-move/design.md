# Design

## Context

See [proposal.md](proposal.md). The dependency acceptance policy
(`.config/checks/dependency-vulnerabilities/policy.toml`) reports a finding as unfixed upstream only
while every locked artifact that ships it is already its registry's latest release. The release-age
rule takes a release only after it has been public for 24 hours.

## Goals / Non-Goals

Goals:

- Ship npm 12.2.2, so the six fixable advisories leave ETHOS's runtimes.
- Leave the two advisories that no npm release fixes reported as unfixed upstream, not blocking.

Non-goals:

- Changing the policy. The gap between the age rule and the fix rule is recorded as its own
  candidate Change (`essential-fixes-20261105.md`, row 10).

## Decisions

- **Exception to the age rule.** The owner took this one release before its 24 hours, on
  2026-11-05. It is a patch release of a package that ETHOS already pins, from the same publisher.
  Its tarball comes from the npm registry with the lock's integrity hash.
- **Lock method.** Native `npm install --package-lock-only --ignore-scripts`, run by the Node
  archive's own npm 11.20.0. npm 12 refuses to fetch a root dependency by tarball URL under its
  default `allow-remote=none`.
- **Unchanged.** Top-level lock fields and every non-npm package stay as they were.

## Risks / Trade-offs

- A same-day release has had less community exposure. The patch is narrow: seven bundled packages
  move by one patch or minor step.
- The two remaining advisories stay until npm bundles fixed glob and minimatch.
