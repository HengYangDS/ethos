## Context

The first native Windows trust-anchor implementation reached Hosted Windows but
failed while applying the DACL to the fixture's trust directory on Python 3.12,
3.13, and 3.14. The adapter collapsed every native failure into
`git_object_trust_anchor_protection_failed`, so the system-owned error required
to distinguish an invalid API call from a host-policy denial was lost.

## Goals / Non-Goals

**Goals:**

- Preserve the exact bounded Windows process result at the existing adapter
  boundary.
- Correct the one native ACL operation from observed Hosted evidence.
- Keep observation and establishment aligned on the same owner and DACL
  invariant.

**Non-Goals:**

- No Windows allow-by-platform, POSIX-mode emulation, pywin32 dependency,
  compatibility implementation, or additional authority carrier.
- No unrelated lifecycle, publication, tempfile, or adopter repair.

## Decisions

The existing `trust_anchor` subpackage remains the only owner. A failed native
operation raises one stable ETHOS code together with the child exit code and
captured stderr. A `proposal/*` Hosted run supplies the missing Windows fact;
the final implementation then changes only the native ACL program and its
focused regression.

The Windows program continues to use the host security descriptor as authority.
The final DACL must keep the current identity, Local System, and built-in
Administrators as the only write-capable principals. Producer and verifier use
the same product functions.

## Risks / Trade-offs

- **Hosted evidence requires one intermediate proposal projection.** This is a
  deliberate diagnostic transition, not a second product implementation.
- **Native stderr can contain presentation noise.** The adapter retains a bounded
  single-line diagnostic sufficient to identify the failed Windows operation;
  it does not create persistent diagnostic state.

## Migration Plan

Publish the diagnostic commit to an exact `proposal/*` ref, observe the Hosted
Windows failure, apply the smallest native correction in this same Change, then
prove, archive, accept, publish, and retire the lane. The old failed accepted
object remains immutable history and is superseded by the corrected object.
