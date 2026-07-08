# history-truth-boundary

## Why

The authority rename guard must protect current repository truth without
rewriting historical evidence. A whole-repository predecessor-vocabulary ban
made hidden drift visible, but it also erased what earlier Chronicle and
archived OpenSpec records actually said at the time.

ETHOS needs the sharper distinction: current code, schemas, docs, and live
OpenSpec specs use `Authority`; historical evidence and archived change records
may preserve the predecessor vocabulary as history.

## What Changes

- Restore historical Chronicle, claim, and archived OpenSpec text that recorded
  the predecessor term at the time.
- Scope the architecture guard to current truth surfaces instead of all tracked
  historical records.
- Add a positive regression that historical records retain the predecessor term
  so future cleanup cannot silently rewrite Chronicle into current narrative.

## Capabilities

- `repository-governance`: subject=history-truth-boundary; reuse=extend;
  change=modify; facet:lifecycle=validation; facet:surface=evidence;
  facet:authority=test; facet:authority=openspec

## Out Of Scope

- No compatibility alias for the predecessor term in current code.
- No reintroduction of the predecessor term into current docs, schemas, code, or
  live OpenSpec specs.
- No change to transition command semantics.
