# Proposal

## Why

On 2026-11-06 the owner ruled that a GitLab peer's port must not be exposed either: the protected
unit is the whole peer identity, not only its address (relayed from the adopter-owner session).
ETHOS's public test `tests/unit/cli/land/publication/test_retirement_reviews.py` uses a neutral
host with the real peer port. It is the only tracked occurrence in ETHOS's current content.

## What Changes

- The fixture uses a neutral non-default port. The test needs only a non-default port, to prove
  that the port reaches `GITLAB_HOST`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None, so `skip_specs: true` applies.

## Impact

- `tests/unit/cli/land/publication/test_retirement_reviews.py` only. History on the public forges
  stays with the history rebuild track.
