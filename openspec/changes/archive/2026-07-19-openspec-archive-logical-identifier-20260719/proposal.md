## Why

An OpenSpec archive directory is a dated storage name, not the logical Change
ID used by an active lifecycle query. Treating the two as interchangeable makes
an archived carrier appear to be an active Change and leaves callers with an
opaque official-status failure instead of a corrective boundary.

## What Changes

- Reject an archive directory name when it is supplied to the active
  `ethos openspec --change` selector.
- Add `ethos openspec --archive-id <logical-change-id> --json`, which resolves
  exactly one dated archived carrier from its logical Change ID.
- Fail closed on invalid identifiers, no archive match, and ambiguous archive
  matches; do not rename or edit historical archives.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `command-plane`: subject=openspec-archive-logical-identifier; reuse=extend;
  change=modify; facet:lifecycle=validation,archive; facet:surface=cli,docs,
  openspec,test; facet:authority=source,test,docs,openspec,claim,evidence

## Impact

- OpenSpec archive reader and public `ethos openspec` reference command.
- OpenSpec command-plane specification, documentation, regression tests, claim,
  and Chronicle.

## Out Of Scope

- Renaming, rewriting, or otherwise mutating any archived OpenSpec carrier.
- Adding host, task, worktree, or vendor-runtime semantics to ETHOS.
- Treating archived Changes as active lifecycle carriers.
