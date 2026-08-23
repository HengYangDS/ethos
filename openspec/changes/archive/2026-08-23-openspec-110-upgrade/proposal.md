## Why

The repository still resolves OpenSpec 1.9.0 although 1.10.0 is the current
stable release. Local, CI, package-only, and archive behavior must share one
exact dependency identity before ETHOS removes any duplicate lifecycle logic.

## What Changes

- Lock `@fission-ai/openspec` to exact stable version 1.10.0.
- Align current contracts and archive-transition expectations with that lock.
- Prove the official status, instructions, validation, doctor, and archive
  surfaces used by ETHOS against the upgraded package.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is a dependency-identity and compatibility change, so the Change
uses the official `skip_specs` marker rather than inventing product behavior.

## Impact

The npm declaration and lock, current OpenSpec contract text, runner
documentation, and focused archive test change. Historical archives remain
unchanged. Broader Python, CI Action, container, and downloaded-tool upgrades
remain separate bounded Changes discovered by the same supply-chain audit.
