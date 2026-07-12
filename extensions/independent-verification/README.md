# Independent Verification Reference Extension

This bundle owns the optional, provider-local reference implementation for
independent proof re-execution. It is source for a provider to install under an
independent identity; it is not an ETHOS command, a loaded product package, or
an adopter prerequisite.

## Contents

- `extension.toml` declares the default-off provider boundary.
- `adapters/independent_identity/reference_verifier.py` is the constrained,
  one-shot reference source.
- `tests/` proves the path and its fail-closed behavior.

## Boundary

The provider, not a governed repository, owns the account, signing key, trust
anchor, receipt store, immutable source mirror, and any host scheduling. A
repository adopts independent verification only through its own explicit policy;
the absence of that policy remains local-first and requires no provider setup.

See [Optional Independent Verification Adoption](../../docs/governance/independent-verification-adoption.md)
for the policy and installation boundary.
