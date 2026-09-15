## Why

Frequent iterations spend most proof time in lifecycle tests. A measured journey
creates 2,075 subprocesses; native hook notifications repeatedly initialize the
CLI, schemas and admission dependencies even when no admission is required.
Remove that accidental execution boundary without weakening fresh governance.

## What Changes

- Give native Git hook execution its existing package-owned protocol entrypoint,
  independent of the interactive CLI command tree.
- Load admission only for protocol input that actually requires it. Keep one
  full selected-runtime observation per admitted prepared batch.
- Consolidate hook protocol and policy under their semantic package; delete the
  old sibling implementation and superseded internal CLI transport.
- Verify malformed input, real rejection, launcher binding and lifecycle effects,
  then compare the same workload's duration and process/import counts.
- Record the full iteration-cost diagnosis and remaining supply, observation,
  fixture and evidence-reuse work in the existing terminal plan.

## Capabilities

### Modified Capabilities

- `quality`: subject=hook-execution; reuse=extend; change=modify

## Impact

The hook execution owner, native launcher declaration, CLI transport and direct
consumers change together. Installation derives a new launcher generation from
the accepted package. No dependency, persistent cache or alternate policy is added.

## Out Of Scope

- Reusing stale authorization or skipping prepared admission.
- Increasing workers, weakening coverage or removing behavioral obligations.
- Claiming whole-proof reuse, sustained resource bounds or hosted acceptance
  from a focused performance measurement.
