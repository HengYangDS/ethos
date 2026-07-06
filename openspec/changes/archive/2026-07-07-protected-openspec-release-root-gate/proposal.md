---
subject: ethos:protected-openspec-release-root-gate
reuse: extend
change: modify
facet:lifecycle: publish
facet:surface: openspec
facet:authority: repository-governance
---

# Protected OpenSpec Release Root Gate

## Why

A release-root branch can be unbound from the current worktree while still being
repository truth for publication. If that branch retains an active
`openspec/changes/<id>` carrier, the release tree still contains an unclosed
Change carrier even when the accepted root has already archived the change.

## What Changes

- Reuse the protected-branch OpenSpec scanner.
- Keep read models advisory because observing another branch does not authorize
  mutation.
- Block `ethos publish` readiness when the non-current release root contains an
  active OpenSpec carrier.
- Expose the blocking release-root OpenSpec package in publish JSON.

## Impact

ETHOS can no longer claim local publish readiness while `main` contains an
unarchived OpenSpec carrier. The owning release-root branch must be repaired
through governed release work or maintainer break-glass before publish readiness
is true.
