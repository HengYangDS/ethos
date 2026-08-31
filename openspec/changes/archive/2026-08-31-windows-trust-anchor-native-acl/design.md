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
- Make a proved diagnostic object observable through the existing Hosted
  proposal projection.

**Non-Goals:**

- No Windows allow-by-platform, POSIX-mode emulation, pywin32 dependency,
  compatibility implementation, or additional authority carrier.
- No unrelated lifecycle, publication, tempfile, or adopter repair.

## Decisions

The existing `trust_anchor` subpackage remains the only owner. A failed native
operation raises one stable ETHOS code together with the child exit code and
captured stderr. A `proposal/*` Hosted run supplies the missing Windows fact to
a separate repair successor; this diagnostic Change does not guess at or modify
the ACL program.

The Windows program continues to use the host security descriptor as authority.
Producer and verifier continue to use the same product functions.

## Risks / Trade-offs

- **Hosted evidence requires a proposal projection.** This is the normal
  governed review projection of a proved candidate object, not a second product
  implementation or an authoring lane.
- **Native stderr can contain presentation noise.** The adapter retains a bounded
  single-line diagnostic sufficient to identify the failed Windows operation;
  it does not create persistent diagnostic state.

## Migration Plan

Prove and archive the diagnostic commit, land it to the local candidate, and
publish that exact object to `proposal/*`. The resulting Hosted Windows stderr
is the input to a separate bounded repair Change. The accepted failed object
remains immutable history until that successor is proved and promoted.
