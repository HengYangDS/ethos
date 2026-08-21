## Why

ETHOS currently proves that an installed Git-hook runtime has intact package
bytes, but it does not prove that those bytes were built from the current
accepted ETHOS source. A valid old runtime can therefore remain armed after the
accepted implementation changes, making hooks execute obsolete governance while
all integrity checks report success.

## What Changes

- Bind every package-only hook runtime manifest to the ETHOS source commit and
  source tree carried by its wheel build provenance.
- Compare that installed identity with the current accepted ETHOS identity (or
  the invoking wheel identity when no ETHOS source checkout exists).
- Fail closed on missing, invalid, or stale source identity before repository
  mutation.
- Project the installed and expected identities plus one exact, copyable hook
  repair command through the existing runtime/status result.
- Replace the schema-1 integrity-only manifest contract; do not keep a second
  reader, compatibility fallback, runtime registry, or repair state machine.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `distribution`: package-only hook runtimes carry immutable source provenance.
- `repository-governance`: tracked mutation requires a current accepted hook runtime.
- `command-plane`: runtime inspection exposes one deterministic repair action.

## Impact

- Wheel build provenance and package-only installation
- Hook runtime manifest validation and launcher binding
- Status, prewrite, Git effects, and lifecycle recovery that consume hook runtime facts
- Runtime-focused unit and isolated-wheel tests

Out of scope: runtime retention/GC, SemVer, SBOM/provenance publication, a
`commit-msg` hook, adopter Lease recovery, scope expansion, break-glass, or
general dependency upgrades.
