# Design: History Truth Boundary

## Boundary

ETHOS distinguishes current truth from historical record:

- Current truth surfaces: source code, schemas, active docs, live OpenSpec specs,
  rules, hooks, config, README, and package metadata.
- Historical record surfaces: evidence chronicles, evidence claims, and archived
  OpenSpec changes.

The authority predecessor guard belongs to the first set. Chronicle belongs to
the second set. A current-truth lint may not force historical records to pretend
they used today's vocabulary.

## Mechanism

The architecture regression scans tracked current truth files only. It excludes
`evidence/**` and `openspec/changes/archive/**`, then fails on predecessor
vocabulary. A companion regression asserts selected historical records still
contain the predecessor term.

This keeps the kernel naming clean while preserving evidence-grounded history.
No new truth store is introduced.
