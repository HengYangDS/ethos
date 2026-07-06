# Publish Readiness Role Regression

## Problem

The land role-boundary fix correctly blocked normal `ethos land --json` on
protected roots, but initially applied the dry-run role check through the shared
mutation reducer broadly enough to block read-only `ethos publish --json` on the
accepted root.

## Change

Limit dry-run role-bound admission to normal land. Keep publish dry-run as a
read-only publication readiness report, while apply paths still enforce
authorization, expect-head, role, dirty-state, and proof gates.
