## Why

The same accepted ETHOS commit builds with a different source-tree identity on
Windows because checkout text conversion and ETHOS's isolated Git observation
do not share one repository-owned byte policy. The resulting installed wheel
then cannot supply its own provenance because a native Windows `file:` URL is
interpreted as a POSIX path, so valid package-only runtime activation fails.

## What Changes

- Establish repository-owned Git content normalization so a clean checkout of
  one commit has the same source-tree identity on every supported host,
  independently of ambient text-conversion defaults.
- Resolve installed-wheel provenance from a standard `file:` URL through the
  host's native URL-to-path conversion before validating the wheel.
- Add focused regressions for Windows-style checkout semantics and Windows
  drive-letter wheel URLs, then require native hosted conformance to prove the
  same package identity on Linux, macOS, and Windows.
- Keep dirty source overlays meaningful: actual tracked or untracked source
  changes still produce a distinct effective tree.
- Do not add a provider-specific workaround, alternate build identity,
  compatibility carrier, PATH fallback, retry, or network dependency.
- Keep external-link reachability and its diagnostic projection outside this
  Change; they have a different owner and failure mechanism.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: Make source-built and installed-wheel package provenance
  resolve to one host-portable immutable build identity.
- `proof-hosts`: Require native host conformance to prove clean exact-HEAD
  package identity rather than accepting host-specific checkout projections.

## Impact

- Git-native repository content normalization.
- Focused source-identity tests of the existing effective-tree compiler.
- `src/ethos/adapters/repo/runtime/materialization/input_resolution.py` and its
  focused tests.
- Native hosted package-conformance evidence on Windows, macOS, and Linux.
