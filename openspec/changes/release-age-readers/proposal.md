# Proposal

## Why

The owner directed on 2026-11-13 that supply moves at a release age of 0 hours. It holds today by
declaration: each governed repository on the releasing host declares the age in its own toolchain
settings. Two readers of that declaration are not built: the supply refresh does not read it, and
`status` does not show it. Their absence blocks nothing today.

The release lead ruled on 2026-11-15, among the rows that no order holds, that this work takes a
weekly off-gate slot only when one is free at a cut, behind the removal of archived names, and
otherwise follows 0.2.0.

## What Changes

- The refresh reads the declared release age.
- `status` shows it.
- Relayed on 2026-11-19 by the session that keeps the governed repositories, as the owner's
  words to it, and to confirm with the owner first-hand before a design rests on them:
  - The age is 24 hours. Each repository writes its own; one that writes none takes the default
    of the common base, which ETHOS holds once, as configuration.
  - Two exemptions are a mechanism and not hand-written lines: a fix for an advisory, and the
    owner's own sources. It lands before 0.2.0, and its design and its release are this
    repository's to place.
- That session's inventory of the same day: one host line exempts one source by hand; no
  governed repository declares an exemption; two repositories let advisory fixes skip the age
  through Renovate's own setting, the one mechanized case.
- Corrected by the owner the same day, relayed: the base declares nothing about whose sources
  are whose, since that would make the base depend on the repositories it governs. ETHOS gives
  the mechanism of an exemption list alone; each repository writes its own list in its own
  configuration. Candidates for the mechanism, none decided: the one list projected into each
  resolver's native exemption; a check that a fix's exclusion names an advisory which affects
  the locked version and which the target fixes; a report of drift from the declared list.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The supply refresh and the status reader. It adds no rule.

Owner: the release lead. Next action: none before a free slot. Read again: after 0.2.0.
