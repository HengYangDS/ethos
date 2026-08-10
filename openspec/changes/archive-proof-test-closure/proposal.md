# Change: Preserve terminal architecture claims after archive

## Why

The official terminal Change archive correctly relocates its immutable carrier,
but four architecture assertions still addressed that carrier by its former
active path. The assertions must follow the Change identity or current active
Change set so the required post-archive proof can execute without weakening any
quality threshold.

The same closeout also exposed a public-command parity defect: absorbed-ref
retirement returned ready in dry-run before compiling and admitting the Git
effect that apply would execute. Land already owns the required exact-effect
readiness path; retirement must enforce the same boundary.

## What Changes

- Resolve the terminal campaign carrier by its immutable Commitment identity.
- Validate format ownership for the current active Change set rather than one
  hard-coded historical path.
- Compile and admit the exact absorbed-ref retirement effect in dry-run and
  reuse that authority in apply, without granting generic ref mutation.

## Impact

- Affected tests: terminal product-design and format-selection architecture
  contracts, land effect parity, and absorbed-ref retirement.
- No quality threshold changes and no broad Git CAS authority.
