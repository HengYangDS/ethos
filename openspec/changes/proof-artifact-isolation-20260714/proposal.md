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
- Bind `ty` to the checkout's semantic runtime rather than a host-discovered
  environment.
- Keep every affected Python owner script executable by the macOS-provided
  Bash 3.2; add regression coverage for ordering, cleanup, runtime binding,
  and shell portability.

## Capabilities

- `quality`: subject=proof-artifact-terminal-seal; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=ci,openspec,test; facet:authority=source,test,openspec

## Out Of Scope

- No root cache path becomes allowed or ignored by the topology gate.
- No retry, waiver, baseline, or compatibility path is introduced.
- No host `.venv`, host site-packages, or newer Bash installation becomes a
  prerequisite for a governed proof.
- No foreign Work Lane, candidate checkout, or accepted root is mutated.
