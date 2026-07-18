## Context

Tracked generic parity evidence is deliberately excluded from the
parity-relevant semantic tree. Therefore a source commit may be evaluated,
then its evidence record may be committed, without falsely requiring the
record to predict its own Git hash. Candidate and accepted checkouts remain
write-protected by mutation admission.

The existing lifecycle projection reversed that order: it placed the parity
write after `land`, while a live unit assertion rejected any Work Lane whose
generic evidence was stale. The candidate cannot perform the prescribed write,
so the precondition was unsatisfiable.

## Decision

`quality evidence-freshness` now composes configured generic parity freshness.
It remains strict: a stale record is a required proof gap. Its refresh package
names `work_lane_before_proof`, the admitted evidence root/path, and the fact
that the evidence must be committed before proof.

The public lifecycle projection follows the same order. The redundant ambient
unit assertion is removed; focused fixture tests keep parity validation
coverage, while the governed proof gate reports lifecycle failure with the
actual remediation package.

## Invariants

- A Work Lane writes only in its own admitted checkout.
- Candidate and accepted roots remain protected from direct parity writes.
- Any parity-relevant source or contract change invalidates prior evidence.
- An evidence-only recording commit is accepted only through the recorded
  parity-relevant semantic-tree digest.
- Land carries already-proven evidence; it never repairs evidence post hoc.

## Risks And Mitigations

- **Missing generic evidence in a profile fixture:** the freshness gate engages
  only when the repository already tracks the generic carrier; the parity
  command remains authoritative for absence/adoption diagnostics.
- **A stale carrier remains hidden:** the existing product carrier is always
  discovered by the proof gate, and the structured package exposes its exact
  remediation.
- **A writer targets another checkout:** normal prewrite admission still rejects
  candidate and accepted roots; the design introduces no bypass.

## Rollback

Revert the composed freshness check and lifecycle projection together. No data
migration or authority state is introduced.
