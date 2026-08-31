## Why

Hosted Windows proves that the native trust-anchor design is not yet operational:
all supported Python versions fail while applying the directory DACL, but ETHOS
discards the native stderr and reports only a generic protection error. Without
the underlying Windows fact, further edits would be guesswork and could weaken
the trust boundary.

## What Changes

- Preserve the exact bounded native failure reason when Windows trust-anchor
  protection cannot be established.
- Publish the proved diagnostic object to the existing `proposal/*` Hosted
  projection so the native failure can be observed without guessing or
  weakening the trust boundary.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: native trust-anchor establishment must be operational on
  supported Windows hosts and must preserve a diagnostic reason when it fails.

## Impact

The change is limited to the existing trust-anchor adapter, its focused tests,
and this official Change. It adds no dependency, parallel permission model,
compatibility path, or persistent state. Correcting the observed Windows ACL
failure is a separate successor whose design must be derived from the captured
native evidence.
