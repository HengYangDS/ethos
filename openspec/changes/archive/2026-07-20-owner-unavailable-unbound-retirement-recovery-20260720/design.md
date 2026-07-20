# Design: owner-unavailable unbound retirement recovery

## Decision

The recovery is a tightly gated mode of the existing native exceptional
retirement rather than a second resolver or a general lease-takeover command.
It consumes no authority from a provider, chat thread, session, process list,
or filesystem naming convention.

## Admission

The normal exceptional admission remains mandatory. When the recovery flag is
present and the target has an active lease, the accepted Chronicle must name:

- `lease_recovery: owner_unavailable`;
- the exact lease ID, holder, epoch, and expected head observed at invocation;
- the exact absolute recorded worktree path; and
- `source_worktree_absent: true`.

The current actor must be non-empty and different from the source holder. The
recorded source path must still be absent. Any mismatch blocks before the native
CAS or ref effect.

## Effect

The implementation reuses the generation-bound lease CAS with the exact source
lease tuple, then re-observes all existing retirement bindings and requires the
absence of an active lease before the existing compare-and-delete ref effect.
The existing no-clobber attempt/receipt remains the durable evidence boundary;
it already records the exact lease binding and CAS result.

## Alternatives rejected

- **Impersonating the lost holder:** would make a provider/session string into
  authority.
- **Raw local-state or ref deletion:** bypasses the two native compare-and-
  swap boundaries and receipts.
- **Generic ownerless resolution:** the target has an active lease and no linked
  worktree, so it would weaken a distinct unbound-retirement contract.

## Stop conditions

Stop and preserve the residue if the target/head/Claim/Chronicle/protected refs
or lease tuple drift; if the source path reappears; if the CAS fails; or if the
postconditions do not prove ref, unbound entry, and lease absence.
