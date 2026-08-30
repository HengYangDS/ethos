## Why

The accepted source passes the local full proof but fails hosted Windows
conformance and a hosted repository-hygiene gate. The local proof therefore
does not yet represent the portable release boundary it claims to prove.

## What Changes

- Make the generated adopter fixture declare byte-preserving Git attributes for
  its line-ending probes, independent of host `core.autocrlf` defaults.
- Remove test-only type suppressions by expressing the existing test doubles
  through explicit typing.
- Include repository hygiene in the canonical full proof set already used for
  accepted-source admission.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `proof-hosts`: Host conformance fixtures must control repository-local Git
  semantics instead of inheriting machine defaults.
- `quality`: The full proof must include the offline repository-hygiene owner
  that hosted quality runs.

## Impact

The change is limited to the existing adopter fixture, existing tests, and the
single gate registry. It adds no platform branch, compatibility layer, state,
or duplicate policy owner.
