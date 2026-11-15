# Proposal

## Why

The repository's rules raise the bound of a document from 500 to 560 nonblank lines for the
whole repository. The recorded reason is the command reference, measured at 515 lines on
2026-11-14, and its condition: the page splits by reader question in the following batch, and the
bound returns to the default when it does. The release lead's ruling of 2026-11-15 first withdrew
the split and was wrong; the essence seat of the direction review found the recorded condition.

The rule's reader counts every nonblank line of a file, front matter included. By that count the
page read 503 in the commit that raised the bound, 515 at its largest on 2026-11-14, 499 later
that day, and 497 on `dev` at `d98081605`. No authored document on `dev` exceeds 500: the plan and
the contract read 500. The raised bound has had no user since 2026-11-14.

## What Changes

- The bound returns to 500 first, in one line of the rules.
- The page splits by reader question, because three free lines do not hold the next operation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

`docs/reference/command-plane.md`, its links, the pages an installation carries and one line of
`.ethos/rules.toml`. A moved anchor of a carried page is a release entry.

Owner: the release lead. Next action: return the bound in the first lane of 0.2.0-beta.12, then
design the split. Read again: at the cut of 0.2.0-beta.12.
