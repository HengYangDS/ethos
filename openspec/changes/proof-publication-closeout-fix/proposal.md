# Accepted proof closeout

## Why

A package-only full proof on a clean accepted root with no active Change crashes
because OpenSpec status is intentionally absent but governance indexes its JSON
payload unconditionally. This prevents a fresh accepted-head proof and therefore
blocks governed remote synchronization after the owner lane is retired.

## What changes

- Treat an absent OpenSpec status receipt as the empty payload when no Change is selected.
- Preserve strict status validation whenever an active or completed Change is selected.
- Prove the source-independent accepted-root closeout path.
