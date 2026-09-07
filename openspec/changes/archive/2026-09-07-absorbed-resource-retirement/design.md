## Context

The current terminal contract separates authoring authority from deletion-only
accepted absorption. Ref and linked-worktree retirement already own exact
observation, CAS, result evidence, and recovery; their target filters still
equate eligible resources with `work/*`. Historical objects may also predate the
current policy schema, so their policy cannot authorize their own disposal.

## Decision

Keep one native branch-role owner for the distinction between repository roots
and topic branches. Retirement consumes that distinction rather than maintaining
prefix exceptions. An explicit topic target is eligible only in conjunction with
the existing accepted-ancestry, worktree, Lease, actor, and exact-object checks.
Eligibility is not mutation authority and never enables ordinary source writes.

Reuse `retire absorbed-ref` for an unlinked, unleased local ref and `retire landed`
for an explicitly selected clean linked topic worktree. Default authoring-lane
inventory remains bounded to Work Lanes. Existing linked retirement operation
and recovery own destructive effects; no second cleanup engine is introduced.

The reference-transaction hook recognizes the prepared exact retirement under
current accepted policy. It must not require an obsolete source object to carry
current policy or grant a raw deletion merely because the ref is a topic.
Compensation remains bound to the same exact intent. A retirement does not delete
remote proposal refs or close their review records.

Repository identity belongs to the surviving control repository, not to the
historical object being removed. The retirement operation binds identity at the
exact accepted HEAD, and native worktree evidence reads the control checkout's
committed identity while retaining the historical subject HEAD in its input and
output observations. The existing absent-prestate option applies only to the
deleted ref's expected revision: accepted assertions still establish one valid
repository identity, and a conflicting valid identity remains an error.

## Rejected Alternatives

- Rename historical refs or add `codex/` to authoring policy: this manufactures
  write authority and leaves the same defect for every other prefix.
- Bypass hooks or hand-edit Lease state: this avoids rather than repairs the
  public protocol.
- Add a cleanup registry or migration schema: fresh Git/Lease observations and
  the existing retirement receipts already carry the required facts.

## Verification And Exit

Observe RED for non-Work-Lane absorbed refs and linked worktrees through public
commands and installed hooks. Verify current and pre-policy source objects,
root-resource exclusion, dirty preservation, live foreign Lease refusal, exact
coordinate drift, raw-delete refusal, and existing compensation/recovery. Keep
historical dirty trees untouched until their unique semantics are adjudicated.

This Change exits through exact-HEAD proof, archive/reproof, accepted CAS and
package readback. Only then may the repaired public command retire the observed
historical resources after a fresh dry-run. The implementation lane must also
retire; creating it is justified only because none of the historical roots grants
current write authority.
