## Why

Hosted Windows proves that the native trust-anchor design is not yet operational:
all supported Python versions fail while applying the directory DACL, but ETHOS
discards the native stderr and reports only a generic protection error. Without
the underlying Windows fact, further edits would be guesswork and could weaken
the trust boundary.

## What Changes

- Preserve the exact bounded native failure reason when Windows trust-anchor
  protection cannot be established.
- Use that Hosted evidence to correct the existing Windows ACL operation at its
  sole adapter boundary.
- Prove both successful establishment and rejection of foreign write authority
  on real Hosted Windows.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: native trust-anchor establishment must be operational on
  supported Windows hosts and must preserve a diagnostic reason when it fails.

## Impact

The change is limited to the existing trust-anchor adapter, its focused tests,
the package-conformance fixture, and this official Change. It adds no dependency,
parallel permission model, compatibility path, or persistent state.
