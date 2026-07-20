## Context

The source's committed head is in accepted history, but its worktree has four
uncommitted edits. The source combines desirable Ruff output routing with
obsolete quality-audit behavior. A line-level replay would silently replace
current contract semantics, while preservation alone would leave the useful
behavior unaccepted.

## Decision

Reimplement only the behavior demanded by the current contract: no direct
`print` in the four advertised scripts, with package digest integrity refreshed.
Retain accepted quality-audit semantics and tests as the selection oracle. After
local lifecycle proof and closeout, use a target-specific native
`preserve-retire` resolution to bundle any remaining source delta and retire the
exact lane.

## Risk controls

- Fresh prewrite confines all carrier changes to its own worktree.
- Focused Ruff and quality tests distinguish accepted semantics from stale
  source assumptions.
- Package digests prevent script edits from becoming unverified skill residue.
- Native resolution re-observes and preserves the dirty source before removal.
- Candidate ownership is separate; no carrier action changes `candidate/dev`.
