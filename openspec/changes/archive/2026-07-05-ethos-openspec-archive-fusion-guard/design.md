## Context

The official OpenSpec boundary owns the archive operation. ETHOS owns repository
truth admission: accepted specs must not lose obligations because an archive
projection overwrote a requirement body.

## Design

The guard lives in the existing OpenSpec shape audit because that path already
runs on report/proof and does not require deep official CLI validation. It reads
Git diff for `openspec/specs/**/*.md` and flags deleted scenario obligation
lines that begin with `- **WHEN**`, `- **THEN**`, or `- **AND**`.

This is intentionally small. It does not try to interpret all spec prose. It
protects the lines that encode executable behavior and review obligations. Added
obligations are allowed; deleted obligations must be restored, fused, or carried
by an explicit removal decision.

## Alternatives

A full OpenSpec semantic merger was rejected as too broad for this failure mode.
A manual checklist was rejected because the prior failure happened during an
otherwise valid archive flow. A Git-diff guard is the minimal enforceable shape:
it catches the exact class of loss at the mutation/proof boundary.

## Proof Strategy

- Unit tests simulate deleted and added obligation diff lines.
- Repository report/proof exercise the shape audit on the actual work lane.
- OpenSpec lifecycle validates the carrier.
- Full Python gate and executed proof bind the result before land/closeout.
