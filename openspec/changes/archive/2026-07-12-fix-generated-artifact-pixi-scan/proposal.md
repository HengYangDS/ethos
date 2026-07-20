# Generated Artifact Pixi Scan

## Why

A Pixi-backed adopter Work Lane creates a local `.pixi/` runtime tree. The
generated-artifact audit descends into that non-authoritative environment and
performs recursive emptiness checks from each denied directory, making an
executed proof consume CPU indefinitely rather than producing a verdict.

## What Changes

- Exclude the local `.pixi/` environment tree from generated-artifact candidate
  traversal, alongside `.venv/`, `node_modules/`, `.git/`, and `__pycache__/`.
- Add a regression test that proves the Pixi root is pruned before recursive
  candidate descent.
- Preserve audit coverage for tracked source, declared generated homes, and
  adjacent unapproved artifact drift.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: Generated-artifact topology evaluation remains finite in
  Pixi-backed Work Lanes without making Pixi runtime files repository truth.

## Impact

Affected code is `ethos.repository.policy.artifacts`, its focused governance
test, and the OpenSpec quality delta. No dependency, public CLI, remote, or
publication behavior changes.

## Out Of Scope

- Do not allow generated artifacts under arbitrary hidden directories.
- Do not delete or migrate a Pixi environment.
- Do not alter the declared semantic generated-artifact homes.
