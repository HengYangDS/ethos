# Proposal

## Why

The repository's rules raise the bound of a document from 500 to 560 nonblank lines for the
whole repository. The recorded reason is the command reference, measured at 515 lines on
2026-11-14, and its condition: the page splits by reader question in the following batch, and the
bound returns to the default when it does. The release lead's ruling of 2026-11-15 first withdrew
the split and was wrong; the essence seat of the direction review found the recorded condition.
The corrected ruling of the same day owes the split to 0.2.0-beta.12, and this Change is that
batch's first documents Change.

The rule's reader counts every nonblank line of a file, front matter included. By that count
(`git show <commit>:docs/reference/command-plane.md | grep -c '[^[:space:]]'`) the page read 503
in the commit that raised the bound, 515 at its largest on 2026-11-14, 499 later that day, and 497
at this Change's base. No authored document exceeds 500 there: the plan and the contract read 500.
The raised bound has had no user since 2026-11-14.

Three free lines do not hold the next operation, and three Changes prepared for the same batch add
lines to the page. So the split lands before them, and the bound returns in this Change.

## What Changes

- Two reader questions leave the command reference for pages of their own under `docs/reference/`.
  `integration-and-release.md` holds `Native Merge Continuation`,
  `Retained Candidate Materialization` and `Accepted Release Selection`; `ci-operations.md` holds
  `Native CI Projection` and `Exact Ref Observation For CI`. Each moved section keeps its text
  byte for byte and its anchor.
- The command reference keeps the commands, their result, verification, runtime selection and
  commit integrity. It reads 373 nonblank lines; the new pages read 113 and 48.
- Each moved heading stays in the command reference with one pointer to the section's new place,
  so an old anchor still resolves.
- Both pages enter the reference index, the wheel and the source archive. The one tracked link to
  a moved anchor points to the new place.
- `.ethos/rules.toml` loses the `[paradigm.size]` override, its reason and its comment. The bound
  is the paradigm's default of 500 again.
- The unreleased changelog names the five moved anchors.

Not breaking: no command, schema or requirement changes, and no anchor of the command reference
stops resolving.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The quality requirement `Current Markdown stays within one navigable topic` already sets the
default of 500, and the repository stops declaring a higher value. No accepted requirement names
the page or the documents an installation carries, so `skip_specs: true` applies.

## Impact

`docs/reference/command-plane.md`, `docs/reference/integration-and-release.md`,
`docs/reference/ci-operations.md`, `docs/reference/README.md`,
`docs/architecture/runner-and-mutation.md`, `pyproject.toml`, `.ethos/rules.toml` and
`CHANGELOG.md`. The wheel and the source archive carry two more documents. A moved anchor of a
carried page is a release entry.
