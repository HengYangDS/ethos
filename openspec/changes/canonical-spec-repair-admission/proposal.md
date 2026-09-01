## Why

An adopter can be required by official OpenSpec validation to repair an invalid
canonical specification while ETHOS simultaneously denies prewrite before it
uses the active Change's otherwise valid Commitment. This makes the exact repair
requested by the authority impossible without bypassing that authority.

## What Changes

- Admit only the exact canonical specification files named by current official
  `openspec_validation_failed:spec:<capability>` gaps when no normal material
  scope can be compiled.
- Preserve all existing Work Lane, Lease, editor-root, runtime-binding, and path
  checks; unrelated canonical files and all product paths remain blocked.
- Add regression coverage for exact admission, mixed-path rejection, malformed
  identifiers, and ordinary valid-Commitment behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: Tracked-write admission can authorize the exact
  canonical spec repair that official validation itself requires, without
  granting a general bypass around active Change scope.

## Impact

The OpenSpec lifecycle observation and prewrite material-scope resolver change.
Public command shape, stored authority, Lease schema, Commitment schema, and
normal Change attribution do not change.
