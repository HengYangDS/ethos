# Change: Preserve terminal architecture claims after archive

## Why

The official terminal Change archive correctly relocates its immutable carrier,
but four architecture assertions still addressed that carrier by its former
active path. The assertions must follow the Change identity or current active
Change set so the required post-archive proof can execute without weakening any
quality threshold.

## What Changes

- Resolve the terminal campaign carrier by its immutable Commitment identity.
- Validate format ownership for the current active Change set rather than one
  hard-coded historical path.

## Impact

- Affected tests: terminal product-design and format-selection architecture
  contracts.
- No production behavior or quality threshold changes.
