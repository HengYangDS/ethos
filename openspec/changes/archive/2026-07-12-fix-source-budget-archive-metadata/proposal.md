# Source Budget Archived OpenSpec Metadata

## Why

An archived OpenSpec carrier adds its required `.openspec.yaml` header to the
repository. The source-budget classifier treated that historical header as
executable YAML, so closing a valid change could exceed the YAML ratchet
without adding maintained behavior or configuration.

## What Changes

- Exclude only `.openspec.yaml` files directly below
  `openspec/changes/archive/**` from executable-source accounting.
- Keep active OpenSpec metadata and every other YAML path in the source-budget
  inventory.
- Add a focused red/green regression that proves the narrow boundary.
- Compress the generated-artifact prune-set declaration without changing its
  finite Pixi traversal behavior, restoring the per-file size ratchet.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: global executable-source accounting distinguishes archived OpenSpec
  closeout metadata from maintained YAML carriers.

## Impact

Affected code is `ethos.domain.prove`, its focused test, the generated-artifact
policy declaration, and the quality OpenSpec requirement. No dependency,
public CLI, remote, or publication behavior changes.

## Out Of Scope

- Do not exclude active OpenSpec changes from the source budget.
- Do not exclude archived proposal, design, task, or delta documents.
- Do not change the source-budget baseline, debt ledger, or terminal budget.
