# Design

## Context

See [proposal.md](proposal.md). The paradigm's formatter table
(`src/ethos/contracts/paradigm/paradigm.toml`, `[[formatter]]`) names one formatter per carrier
class with the settings every binding declares, and the source-format and configuration gates read
that shipped configuration whether or not a repository carries its own. The release conventions name
`VERSION` as the only version source.

## Goals / Non-Goals

**Goals:**

- A repository with no formatter carrier of its own passes on the shipped baseline, and a carrier it
  does keep is still held to the common settings.
- A root npm manifest may carry the version npm needs while `VERSION` stays its only source.

**Non-Goals:**

- Bounded overrides of common settings with a recorded reason; the base rows of the end-state design
  own them.
- Version projections other than the root `package.json`.

## Decisions

- **Absence is valid, contradiction is not.** The report skips a formatter whose carrier the
  repository does not track and keeps the setting check for one it does. The alternative, keeping
  the binding gap and letting repair write the copy, preserves the duplication the issue reports.
- **Equality makes a copy a projection.** A literal `version` equal to `VERSION`'s text is read from
  the source and checked against it, the same drift check every projection has; any other value is a
  second source. Rejected: requiring npm to read `VERSION`, which `npm pack` and `npm publish`
  cannot do.

## Risks / Trade-offs

- [A repository loses the local carrier that documented its settings] → The shipped carrier is the
  documentation; `ethos status` names the configuration each gate ran.
- [A stale npm version slips through] → Any difference from `VERSION` keeps the gap, so a release
  bump that forgets the manifest is refused.
