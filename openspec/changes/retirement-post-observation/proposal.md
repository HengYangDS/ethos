# Retirement post-observation and runtime provenance

## Why

A public linked-lane retirement can remove its own worktree and ref successfully, then fail while producing the receipt because postcondition observation resolves local state from the deleted invocation root. Separately, the installed hook runtime can point `direct_url.json` at a deleted build wheel, preventing the same package-only runtime from creating the next governed lane.

## What changes

- Observe retirement Lease/ref/worktree postconditions from the surviving accepted control root.
- Persist the exact runtime wheel in a content-addressed Git common-dir package store before installation.
- Prove both paths with real public apply regressions.
