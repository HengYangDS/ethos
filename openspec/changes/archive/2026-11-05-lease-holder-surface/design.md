# Design

## Context

See [proposal.md](proposal.md).

- **Status.** `inspect_repository` resolves the current authority on every call and puts its
  projection in `data.authority`. `apply_payload_budget` moves the whole `data` into an artifact
  when a status result exceeds 16 KiB, and keeps `summary` inline. `summary` names root, branch,
  role, dirty state and coordination counts.
- **Renewal.** `lane lease renew` and `resume` share `DeclaredLeaseOperationOptions`, whose four
  coordinates are required parameters. `execute_lease_operation` previews or applies one exact
  compare-and-swap on those coordinates.

## Goals / Non-Goals

Goals:

- The holder reads its Lease from the inline status result, whatever the payload size.
- The holder renews or resumes its Lease in two steps, preview then apply, without reading the
  coordinates from anywhere else.

Non-goals:

- Relaxing the compare-and-swap. An apply still binds all four coordinates.
- Other operator verbs from the operator-verbs design. Each gets its own Change.

## Decisions

- **The summary carries the Lease.** For a Work Lane, `summary` gains `lease_generation`,
  `lease_expires_at` and `lease_seconds_left`, taken from the same authority projection as
  `data.authority`. Other roles carry none of them.
- **A renewal threshold.** With less than two hours left, status's next action is
  `ethos lane lease renew --root <root>`, after any repair of its runtime, commit policy or
  authority and before closeout. An expired Lease cannot be renewed, so status then names
  `ethos lane lease resume --root <root>`. Two hours covers the longest full proof observed on a
  loaded host, with margin.
- **Coordinates become optional only for a preview.** Without coordinates, renew and resume read
  the current branch and its Lease and plan the same exact operation. The result's next action is
  the apply command with all four coordinates. `--apply` without all four refuses with
  `lease_coordinates_required`.

## Risks / Trade-offs

- A preview reads the Lease that the apply will compare. If another process renews it in between,
  the apply's compare-and-swap fails as it does today, and a fresh preview names the new
  coordinates.
