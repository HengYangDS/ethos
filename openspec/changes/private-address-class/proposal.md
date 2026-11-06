# Proposal

## Why

The paradigm's private-address class includes the IPv4 and IPv6 loopback and link-local literals.
They disclose nothing about any peer, and in adopters they carry security controls: loopback-bound
ports, loopback-only allowlists, and assertions that a listener did not escape loopback. Two
reviews, fbee0c's and an independent one, confirmed that the class edit stands on its own. It is the
first part of the peer-identity work that replaces `peer-neutral-artifacts`.

## What Changes

- Loopback and link-local literals leave the paradigm's `private_address` pattern, its Gitleaks
  twin and the rule's keywords.
- ETHOS's product boundary keeps refusing them on ETHOS's own product surfaces. Its catalog carries
  the removed alternatives verbatim as its own pattern, beside the `localhost` pattern, so no form
  that the old pattern refused passes there.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: the private-address class no longer includes loopback and link-local
  literals.
- `proof-hosts`: the product boundary refuses loopback and link-local literals on ETHOS's product
  surfaces.

## Impact

- `src/ethos/contracts/paradigm/paradigm.toml`, `.config/checks/gitleaks/gitleaks.toml` and
  `src/ethos/repository/policy/boundary/catalog.py`.
- `tests/support/private_addresses.py`, `tests/unit/policy/test_product_boundary_remaining_public.py`,
  `CONTRIBUTING.md`.
- Adopters: nothing changes on their side (fbee0c measured wib and DDWG).
