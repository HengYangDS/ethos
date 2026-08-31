## Why

The exact-ref path of `ethos publish --probe-remote` calls `ls-remote` without a
timeout. More seriously, when that ref observation is unavailable the CLI
passes an empty OID to push admission, which then reports
`accepted_ref_move_not_fast_forward` as though a remote history had been
observed. The result mixes a missing fact with a contradictory history judgment
and can leave a read-only network process alive.

Remote publication needs one bounded observation per exact target. A missing
observation must remain `unknown`; only an observed OID may be classified as
current, creatable, fast-forward, or divergent.

## What Changes

- Keep the existing remote-publication adapter as the sole owner of exact
  publication target observation.
- Bound every `ls-remote` ref observation and preserve timeout, exit code,
  stderr, exact argv, and working directory in the observation.
- Prevent push admission and ancestry policy from running when a target OID is
  unavailable; project one `unknown` result and one executable retry command.
- Keep observed divergence as `block`, and keep exact-CAS apply/post-observation
  on the same adapter and request receipt.
- Add regressions for timeout, failed observation, observed fast-forward, and
  the absence of false non-fast-forward gaps.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: remote publication observation must preserve the
  distinction between unknown facts and observed divergent history.
- `command-plane`: publication must project the closed result algebra and one
  bounded continuation without duplicating remote probes.

## Impact

The change is limited to the existing remote-publication observation owner,
the publish projection, their focused tests, and the authoritative terminal
plan. It does not change Git object identity, peer topology, proof selection,
publication ordering, adopter repositories, runtime activation, or Work Lane
semantics.
