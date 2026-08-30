## Why

Hosted Windows rejects valid signed publication objects because ETHOS treats
POSIX mode bits as the cross-platform authority for trust-anchor protection.
Windows protects files through security descriptors and DACLs, so `chmod(0600)`
does not prove the intended invariant there.

## What Changes

- Define trust-anchor protection by effective write authority rather than one
  platform's permission representation.
- Preserve the existing POSIX owner/mode check and use the native Windows ACL
  authority on Windows.
- Make ETHOS-created anchors and the installed-package fixture establish the
  same protection that the verifier requires.
- Add positive and negative regressions for supported host protection models.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: Git object trust must validate repository-external trust
  anchors through the host's native file protection model.

## Impact

The change is limited to Git-object trust-anchor observation and creation, the
existing runtime-input declaration, the package-smoke fixture, focused tests,
and this official Change. It adds no compatibility state, policy registry,
alternate trust model, or third-party runtime dependency.
