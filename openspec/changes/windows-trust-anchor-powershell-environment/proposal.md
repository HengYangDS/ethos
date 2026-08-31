## Why

Hosted Windows proved that ETHOS reaches the native trust-anchor operation but
inherits PowerShell 7's `PSModulePath` while launching Windows PowerShell. The
child can discover `Get-Acl` yet cannot load `Microsoft.PowerShell.Security`, so
the ACL operation never starts on any supported Python version.

## What Changes

- Remove the incompatible inherited module-path variable at the existing child
  process boundary so Windows PowerShell reconstructs its native module path.
- Keep the current ACL program, fail-closed behavior, and bounded native error
  propagation unchanged.
- Prove the installed wheel establishes and observes the native ACL on Hosted
  Windows.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: Windows trust-anchor protection must execute under the
  native Windows PowerShell module environment even when ETHOS is launched from
  PowerShell 7 or another parent process with an incompatible `PSModulePath`.

## Impact

The change is limited to the shared subprocess environment boundary used by the
existing trust-anchor adapter, its focused tests, and this official Change. It
adds no dependency, platform bypass, alternate ACL implementation, persistent
state, or compatibility carrier.
