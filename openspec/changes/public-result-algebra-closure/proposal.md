## Why

Public results permit reasonless `unknown`/`block`, while `lane status` also
treats facts-only workspace data as a verdict owner.

## What Changes

- Close non-pass reasons at the existing `EthosResult` boundary.
- Derive `lane status` only from validation and explicit gaps.
- Delete stale reasonless public fixtures.

## Out of Scope

Authority, recovery, diagnostics, and TransitionPlan redesign remain successors.
