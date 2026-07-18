## Context

`dirty_provenance` is the Git-native source view used by workspace status. It
currently distinguishes tracked, deleted, conflicted, and untracked paths, but
does not identify the narrowly recognizable temporary probes that can be left
in a protected checkout during diagnosis. `orient` is a derived reader view:
it must make the safe next action discoverable without becoming an ownership or
mutation authority.

## Goals / Non-Goals

**Goals:**

- Detect only an explicit, low-false-positive probe shape: an untracked
  `tests/**/test_*.py` file whose bounded file header contains `TEMP PROBE`.
- Expose a stable, bounded provenance summary: total count, at most sixteen
  repository-relative paths, and an overflow flag.
- Give accepted and candidate roots a specific, non-automating orientation:
  remove the probe or migrate it into an owned Work Lane.
- Preserve ordinary dirty-state behavior and the reader-only authority
  boundary.

**Non-Goals:**

- Heuristic attribution, marker inference, automatic deletion, or a new
  cleanup command.
- Any change to leases, handoff, landing, retirement, or foreign-lane rights.

## Decisions

### Provenance owns recognition

`dirty_provenance` will enrich its existing payload with a
`temporary_probes` summary. It will inspect only untracked entries and only a
bounded header region, then retain repository-relative paths. This keeps the
classification close to the Git evidence, avoids another repository state
store, and makes schema validation possible.

Alternatives rejected:

- A generic filename-only rule would create false positives for legitimate
  untracked tests.
- An unbounded full-file scan is unnecessary and makes a status path depend on
  arbitrary file size.
- A separate persistent probe registry would duplicate Git's local-state
  observation.

### Orientation derives remediation without granting authority

`orientation_packet` will derive a temporary-probe projection from the
provenance payload. When an accepted or candidate root has one or more
probes, its candidate action and concise human reason will state the two safe
operator choices: remove the probe or move it into an owned Work Lane. The
projection will explicitly record that automated cleanup is unavailable.

All other dirty states retain the existing generic action. Work Lanes retain
their current dirty-work semantics; a marker does not turn a reader view into
authority to touch another checkout.

### Contract and tests move together

The workspace-status schema will require the structured summary on clean,
dirty, unavailable, and non-Git paths. Focused tests will cover recognition,
negative cases, bounded output, protected-root remediation, and preservation
of ordinary dirty guidance. The OpenSpec delta carries the observable
repository-governance contract.

## Risks / Trade-offs

- **A user puts the marker in an ordinary test header** -> The explicit marker
  is an intentional opt-in; status still only advises and never deletes.
- **Many probe files obscure an operator's view** -> Count remains exact,
  paths are bounded, and an overflow flag signals that the list is partial.
- **A malformed or unreadable file causes status failure** -> Recognition fails
  closed to "not classified" for that entry; Git dirty provenance itself
  remains available.
- **A stale reader view is mistaken for permission** -> The projection retains
  `mints_truth=false`; existing prewrite and lane authority checks remain the
  mutation boundary.

## Migration Plan

1. Add the additive provenance field and schema contract.
1. Add the derived orientation behavior and tests.
1. Run schema, focused, full, and parity proof on the lane HEAD.
1. Land locally through candidate and accepted-root closeout only after all
   gates pass. Remote publication remains a separate deferred state.

Rollback is a normal revert of this additive classifier and projection; no
persisted migration or cleanup effect exists.

## Open Questions

None. The marker, scope, bounded output, and non-automating remediation are
deliberately fixed by this change.
