## Why

The accepted hosted-runtime portability change reaches the Windows wheel build,
but immutable package publication fails because the shared content-addressed
store applies a POSIX directory-descriptor durability operation on Windows.

## What Changes

- Preserve file flush, atomic publication, collision detection, and byte
  verification on every host.
- Apply the parent-directory durability barrier only where directory file
  descriptors are supported.
- Add a focused Windows regression at the content-addressed store boundary.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: Content-addressed package storage must publish immutable bytes
  on every supported host without invoking unsupported directory operations.

## Impact

The change is limited to the shared content-addressed file writer, its focused
tests, and the distribution contract. It adds no fallback store, compatibility
state, retry framework, or provider-specific implementation.
