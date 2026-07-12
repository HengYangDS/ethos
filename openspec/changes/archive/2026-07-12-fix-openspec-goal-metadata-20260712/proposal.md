# OpenSpec Goal Metadata Compatibility

## Why

OpenSpec 1.6 creates `.openspec.yaml` files with a `goal` field when callers
use the official `openspec new change --goal` workflow. ETHOS currently rejects
that official metadata as unsupported, so a valid change cannot pass lifecycle
or proof closeout.

## What Changes

- Admit the official `goal` key in active and archived OpenSpec metadata.
- Preserve fail-closed rejection of unknown metadata such as `owner`.
- Add regression tests across metadata and archive closeout paths.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: OpenSpec metadata compatibility accepts the official
  OpenSpec 1.6 `goal` field.

## Impact

The metadata compatibility allowlist and focused tests change. No external
provider, remote, or publication behavior changes.

## Out Of Scope

- Do not accept arbitrary metadata keys.
- Do not change OpenSpec archive naming, task, or delta validation.
