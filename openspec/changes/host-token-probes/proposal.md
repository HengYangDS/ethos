# Proposal

## Why

`test_a_token_names_one_ticket_exactly` checks that the host queue answers a token for its own
ticket alone. One of its probes is the token in upper case. A token's nonce is sixteen
hexadecimal digits from `secrets.token_hex(8)`, so a nonce without a letter has no upper case
of its own: the probe then equals the token, the queue rightly answers that the ticket is held,
and the test fails. That is 10 of 16 choices in each of sixteen places, about one run in 1,850,
with nothing to reproduce it from.

The same test names "only its own ticket's" and never asks with a well-formed token of another
ticket. Five of its six probes are refused for their shape before any comparison, so a queue
that compared the nonce alone, or matched the process number loosely, would pass it. The empty
token and a token without a nonce, which an earlier form of the test refused by name, are no
longer asked.

A model review of the range `1044a5cfc..20981c042` of the lane `20261123-host-slot` found both
on 2026-11-23, after the Change that owns that test, `host-slot-outlives-holder`, was archived.
The code that answers a token was read against these cases and holds; the gap is in the test.

## What Changes

- The probes of that test are derived from the token, so each differs from it whatever the
  nonce holds: the same nonce with another process number, the same process number with
  another nonce, and a process number of which the real one is a suffix.
- The empty token and a token without a nonce are asked again.
- No product code changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The requirement "Full proofs and nested work share the host admission" already says that
a token admits nothing once its ticket's lock is free; this Change only makes its test bind, so
`skip_specs: true` applies.

## Impact

`tests/unit/gates/test_host_place_lifetime.py`, one test. Nothing that a governed repository
reads.
