# Report Coordination Advisory Design

## Context

Work Lane coordination truth is already produced by `workspace_status` and
surfaced by `ethos status` and `ethos orient`. `ethos report` is a reader-view
scorecard over existing governance state, so it should reveal the same
non-blocking coordination signals without becoming a second lifecycle owner.

## Design

`scorecard_report()` reads the existing workspace-status payload for the audited
repository and passes only its explicit `coordination.advisory_gaps` into the
report advisory reducer. The reducer remains explicit: it does not recursively
scan provider payloads and does not turn advisory signals into required gaps.

Known Work Lane coordination advisories route to read-only inspection commands:
`ethos orient --json` and `ethos lane status --json`. Those actions reveal
ownership, dirty state, missing leases, and next coordination steps without
authorizing mutation from the current checkout.

## Alternatives

- Making coordination advisories blocking was rejected because foreign Work Lane
  presence is expected in multi-agent work and should not stop an otherwise
  proven accepted root.
- Adding a new residue command was rejected because `orient`, `status`, and
  `lane status` already own the reader views.

## Proof Strategy

- Unit tests prove report includes Work Lane coordination advisory signals while
  `ok=true` and `required_gaps=[]` remain possible.
- Focused report output proves the current multi-agent repo state now reports a
  non-zero advisory count for existing lane coordination signals.
- HEAD-bound proof validates the change with the repository proof graph before
  land.
