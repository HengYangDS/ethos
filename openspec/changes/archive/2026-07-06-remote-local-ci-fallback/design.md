## Context

Remote forges and hosted CI are adapter projections. ETHOS must not block local
repository governance simply because a remote adapter is unavailable. Existing
`publish` output already deferred remote push; this change makes the reason and
fallback observable.

## Design

`ethos publish` asks the Git adapter for a read-only `remote_availability` fact
using `git remote get-url` and `git ls-remote --exit-code`. Probe failures,
missing remotes, and timeouts become advisory facts with no required gaps.

The local fallback is `.config/ci/scripts/run-local-ci.sh`, a compact owner
script that invokes existing reusable owner gates. Hosted CI YAML remains a
projection over the same scripts. The fallback evidence is explicitly labeled
`local_fallback` and sets `hosted_ci_status_claimed=false`.

This follows the same boundary as the reference repositories: local-ci can prove
repository-owned gates and projection smoke, while hosted CI success remains a
separate provider fact.

## Proof Strategy

- Unit tests cover unavailable and available remote probes.
- Publish contract tests assert local-ci fallback appears in JSON without hosted
  status claims.
- Shell lint validates the local-ci script.
- OpenSpec validates the carrier and canonical specs.
