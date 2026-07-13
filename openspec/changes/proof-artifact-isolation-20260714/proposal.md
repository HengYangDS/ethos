# Proof Artifact Isolation

## Why

The product proof graph evaluates `generated-artifacts` before the Python test
and Ruff gates. Those later gates own runtime-cache routing and cleanup, so a
proof can reject denied root cache residue before the producing/cleaning
boundary has completed. The standalone topology command is correct to reject
such residue; the proof sequence is not a closed final-state observation.

## What Changes

- Make the generated-artifact topology gate a post-producer proof seal after
  Ruff and the Python test gate.
- Make test-gate exit cleanup remove the same denied root runtime residue as
  test-gate entry cleanup.
- Add regression coverage for ordering and symmetric cleanup.

## Capabilities

- `quality`: subject=proof-artifact-terminal-seal; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=ci,openspec,test; facet:authority=source,test,openspec

## Out Of Scope

- No root cache path becomes allowed or ignored by the topology gate.
- No retry, waiver, baseline, or compatibility path is introduced.
- No foreign Work Lane, candidate checkout, or accepted root is mutated.
