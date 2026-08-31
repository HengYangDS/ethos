## Why

Hosted conformance now reaches the native Windows trust-anchor operation, but
the surrounding test and CI environment is not closed: Windows loses an empty
indexed Git configuration value, and the Linux verify image lacks the
`ssh-keygen` executable required by the repository's declared signing policy.

## What Changes

- Keep the pytest Git overlay complete and portable without relying on an empty
  environment value whose meaning is not preserved on Windows.
- Make the shared Linux bootstrap install the native signing prerequisite when
  it is absent.
- Preserve the existing Git isolation and repository signing semantics without
  adding a fallback signer, provider-specific wrapper, or parallel CI path.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `proof-hosts`: host-conformance Git subprocesses receive a complete,
  platform-portable repository-local configuration overlay.
- `distribution`: Linux hosted bootstrap supplies the native signing executable
  required by governed checkout configuration.

## Impact

The change is limited to the existing pytest environment owner, the shared
hosted bootstrap, their focused architecture tests, and the two owning specs.
It adds no dependency to the ETHOS package and no new runtime or state carrier.
