# history-truth-boundary

## Why

The authority rename guard first separated current repository truth from
historical chronology. That distinction was useful, but its preservation rule was
too loose: it allowed archived evidence and OpenSpec records to keep retired
authority-head vocabulary. Under the later zero-residue policy, the stronger
boundary is: history keeps its meaning and chronology, but retired tokens are not
kept anywhere in repository records.

ETHOS therefore treats this archived change as an intermediate correction
superseded by repository-wide zero-residue closeout.

## What Changes

- Preserve historical Chronicle, claim, and archived OpenSpec meaning without
  retaining retired authority-head tokens.
- Apply the authority residue guard to all git-admissible repository records,
  including evidence and archived OpenSpec records.
- Remove the positive-preservation regression and replace it with a single
  zero-residue invariant.

## Capabilities

- `repository-governance`: subject=history-truth-boundary; reuse=extend;
  change=modify; facet:lifecycle=validation; facet:surface=evidence;
  facet:authority=test; facet:authority=openspec

## Out Of Scope

- No compatibility alias for retired authority-head vocabulary.
- No reintroduction of retired authority-head vocabulary into current or archived
  repository records.
- No change to transition command semantics.
