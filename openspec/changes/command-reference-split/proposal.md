# Proposal

## Why

The repository's rules raise the bound of a document from 500 to 560 nonblank lines for the
whole repository. The recorded reason is the command reference, measured at 515 lines on
2026-11-14, and its condition: the page splits by reader question in the following batch, and the
bound returns to the default when it does. The release lead's ruling of 2026-11-15 first withdrew
the split and was wrong; the essence seat of the direction review found the recorded condition.

A plain count of the page's nonblank lines on `dev` at `d98081605` reads 497. The two figures
differ, and the difference is not explained yet.

## What Changes

- The page is measured with the rule's own reader.
- It splits by reader question, or the measure shows that it fits, and the bound returns to 500
  in the same Change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

`docs/reference/command-plane.md`, its links, the pages an installation carries and one line of
`.ethos/rules.toml`. A moved anchor of a carried page is a release entry.

Owner: the release lead. Next action: measure the page with the rule's reader. Read again: at the
cut of 0.2.0-beta.12.
