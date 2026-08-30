## Why

Hosted Windows package smoke rejects a valid signed commit because Git emits
signature status with CRLF line endings while ETHOS accepts only LF. The smoke
owner then replaces the typed publication gaps with a generic exception, so the
first portable failure is both false and hard to diagnose.

## What Changes

- Accept Git's valid SSH signature status independent of LF or CRLF line endings.
- Preserve the publication command's exact required gaps when package smoke
  cannot obtain the expected full-ref transition plan.
- Add focused regressions for the Windows observation and diagnostic boundary.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: Git trust observation and package-smoke failures remain
  portable and diagnostically exact across supported hosts.

## Impact

The change is limited to the existing Git-object trust adapter, the existing
package-install smoke owner, their focused tests, and this official OpenSpec
Change. It adds no platform branch, compatibility path, state, schema, or new
runtime entity.
