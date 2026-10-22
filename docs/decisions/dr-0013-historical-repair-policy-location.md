---
subject: ethos:decision:historical-repair-policy-location
role: decision
state: canonical
decision_id: DR-0013
decision_status: accepted
relations:
  current_owner: ../../src/ethos/adapters/repo/commit/signature.py
---

# DR-0013: Historical Repair Evidence Reads Its Own Policy Location

Status: canonical rationale. The signature-repair validation in the current source owns current
behavior.

Date: 2026-10-17.

Purpose: preserve why a repair record must be validated against the policy location that its exact
source commit declared, and why moving a policy field is not retroactive.

See also: [DR-0012: Repository paradigm](dr-0012-repository-paradigm.md) and the
`repository-paradigm` OpenSpec Change.

## Context

A signature-repair record binds the exact coordinates it observed when it ran: the unfixed commit,
the accepted branch it was founded on, a policy digest and the refs that carried the unfixed object.
Re-validation recomputes those coordinates from immutable history rather than trusting the record.

Until 2026-10-16 the release mirror was declared as `release_mirror` in the `[branch_roles]` table of
`.ethos/workspace.toml`. The paradigm then moved it to `[release] mirror` in `.ethos/release.toml`
and made every remaining `[branch_roles]` field a paradigm gap. The branch-role reader was changed
to read only the new location, and the historical validation in `signature.py` was changed with it.

## Decision

Historical repair evidence SHALL be validated against the policy location that its exact source
commit declares. A commit that declared the release mirror in `[branch_roles]` keeps that meaning;
a commit that declares it in `[release] mirror` uses the current location. A single commit that
declares both SHALL fail closed rather than choosing one.

The current working tree keeps one location only: the paradigm repair moves the field and deletes
the restated table. The historical reader is therefore the one place that admits the earlier
location, and it admits it only for commits that contain it.

## Alternatives Rejected

- **Read the mirror from whichever location is found:** rejected because a later commit's
  declaration would reinterpret earlier evidence, and the case where one commit states both would
  stay hidden.
- **Keep the field in both locations indefinitely:** rejected because it leaves two owners for one
  policy value and undoes the single-owner rule the paradigm established.

## Consequences and Boundary

- Recomputing coordinates for a record whose source commit used the earlier location yields the
  same refs the record bound, so completed repairs stay verifiable and the retirement paths that
  consume them keep working.
- A repair record created after the move, whose source commit already declares `[release] mirror`,
  needs no special handling.
- The earlier location is evidence vocabulary only. It never becomes a current declaration, and the
  paradigm still reports it in a working tree.

## Evidence and Revisit

- On 2026-10-17 three signature-repair records in the ETHOS set named source commits that declared
  the earlier location, and each failed coordinate re-derivation with
  `signature_repair_source_coordinates_mismatch`.
- The `retained-attestation-members` task 2.3 records that this blocks the proposal-retirement
  journey before the reader under test runs.
- The `repository-paradigm` task 2.24 moved the field, and that Change archived on 2026-10-18
  without the historical reader. `publication-history-repair` task 13.4.3.2 implements the rule in
  the one reader that signature-repair creation and re-validation share.

Revisit if repair records stop binding policy coordinates from their source commit. Retire this
record when the signature-repair validation itself preserves the per-commit rule and these rejected
alternatives.
