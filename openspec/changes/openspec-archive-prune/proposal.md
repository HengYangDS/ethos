# Proposal

## Why

On 2026-11-12 the owner asked to remove the archived OpenSpec Changes dated before October 2026 from
the repository. There are 98 of them, all from September 2026, in 507 tracked files and about 2.3
MB, a quarter of the archive. Nothing in the current tree depends on them: outside the archive no
file names their paths, and the test paths that look alike are synthetic fixtures built in temporary
repositories. One archived October Change, `one-proof-per-change`, names
`2026-09-26-proof-execution-carrier` in its proposal; that citation is history and resolves at the
commits and tags that hold both. Product code reads only the archive of the Change being archived,
landed or retired, and closeout selects proofs by their bindings, not by scanning the archive
(product design contract, Change Relations And Learning). Git history and the 35 release tags from
`v0.2.0-alpha.5` to `v0.2.0-beta.9` keep every removed file.

## What Changes

- The 98 archived Change directories dated before 2026-10-01 leave the current tree.
- `repository-governance` states how the archive is kept: a governed Change may remove archived
  Changes that no tracked file outside the archive cites; Git ancestry and release tags keep them
  readable; an archived Change that stays is still never rewritten.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: ADDED `Pruned archived Changes stay in Git history`.

## Impact

`openspec/changes/archive/2026-09-*` (98 directories, 507 files). No product code, test or
specification text outside the archive changes.
