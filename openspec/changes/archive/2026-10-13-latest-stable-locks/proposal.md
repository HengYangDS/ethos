## Why

The user requires every supply input to track the latest stable release. The
2026-10-12 refresh met that when it landed, but two Python packages released
later are now behind: pre-commit 4.7.0 (2026-10-12T20:45Z) and truststore
0.10.5 (2026-10-12T22:27Z). Several npm transitive packages also have newer
releases within the ranges their dependents already declare.

## What Changes

- Refresh the Python lock to the latest stable releases its declared ranges
  admit, including pre-commit 4.7.0 and truststore 0.10.5. Raise the declared
  pre-commit floor to 4.7.0, because dependency hygiene requires each direct
  dependency's single lower bound to equal its locked version.
- Refresh the npm lock within declared ranges. Packages bundled inside the
  locked npm 12.2.0, which is already the latest npm release, move only with npm
  itself, and versions a dependent pins exactly stay at that pin.
- Leave declarations unchanged where the audit found them current: GitHub
  Actions commit pins, mise tools, mise and uv, CPython 3.14.8, and direct npm
  dependencies including OpenSpec 1.14.1.

Out of scope: newer major releases that dependents' ranges exclude, the
pre-release-only Architecture Publisher dependency of the optional integration,
which needs its own compatibility Change, and container image digests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Lock refresh changes no specified ETHOS behavior.

## Impact

The pre-commit floor in `pyproject.toml`, `uv.lock` and `package-lock.json`,
and through them the next runtime build identity. No policy, source or test
changes.
