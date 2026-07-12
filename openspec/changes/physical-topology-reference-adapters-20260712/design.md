## Context

ETHOS's terminal product design assigns ecosystem plugins and integrations to
`extensions/`; its package ontology limits product packages to `ethos-core`
and `ethos`. The existing root-level `reference_adapters/` directory therefore
has no honest physical owner. Its only accepted-root source is a default-off,
provider-local reference verifier for independent proof re-execution.

At authoring time a foreign Work Lane declares a scope that includes the legacy
source, its old unit-test path, and several affected canonical documents. This
change is a direct maintainer-requested topology correction: it does not enter,
modify, clean, or retire that lane. The carrier makes the decision explicit so
the two changes can be reconciled at the candidate boundary using fresh,
current-state evidence rather than invisible concurrent edits.

## Design

The reference implementation becomes one explicit extension bundle:

```text
extensions/independent-verification/
|-- extension.toml
|-- README.md
|-- adapters/
|   `-- independent_identity/
|       `-- reference_verifier.py
`-- tests/
    `-- test_reference_verifier.py
```

`extension.toml` declares only local ownership and boundaries: the bundle is a
default-off, provider-local reference implementation. It is not a dynamically
loaded product package, a second command plane, or an adopter configuration
requirement. The verifier remains directly executable by a provider after it
has been copied to provider-owned infrastructure; the repository ships source
and tests, never keys, accounts, receipt stores, or scheduling state.

The extension owns its README and its focused test because those artifacts
describe and verify the same optional provider integration. The product's
canonical architecture and adoption documents link to that concrete location.
The old root source and its root-oriented test directory are deleted in the
same change. No forwarding module, import alias, symlink, or compatibility
surface survives.

Historical claims and Chronicle records retain their predecessor paths as
time-bound facts. This change adds new topology evidence instead of rewriting
the historical record; current canonical docs and executable tests must contain
only the new location.

The active assurance claim is a current promotion map rather than historical
narrative. Its promotion targets and recorded focused-test command therefore
move with the source. Its dated Chronicle remains unchanged as evidence of the
predecessor state.

## Alternatives

### Keep `reference_adapters/` at the root

Rejected: it creates a third, undefined product area and makes an optional
provider implementation appear to be core repository substrate.

### Move the verifier into `packages/ethos`

Rejected: provider-local reference code would become product runtime surface,
blur the core/provider boundary, and invite accidental dependency on a
default-off implementation.

### Leave a compatibility wrapper at the old path

Rejected: the terminal design forbids forwarding residue after a topology
migration. The only migration contract is the new concrete path.

## Proof Strategy

1. Add a topology test that fails while the extension source is absent and the
   legacy root remains.
2. Move the unchanged verifier, colocate the existing behavioral tests, and
   prove the new path is the sole executable source.
3. Validate the manifest, current canonical links, affected test suite,
   OpenSpec lifecycle, changed-path plan, executed proof, and refreshed generic
   parity evidence.
4. Recheck foreign-lane coordination immediately before candidate land; no
   decision about a foreign lane is inferred from this carrier.

## Rollback

If the extension layout is found to break a declared proof or installation
boundary, revert this atomic topology change through the governed lifecycle.
Do not restore a forwarding shell; a rollback restores the prior concrete tree
only until a corrected topology change is ready.
