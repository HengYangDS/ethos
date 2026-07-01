---
subject: ethos:evidence:shadow-parity-accepted-classification
role: evidence
state: active
relations:
  supports: ethos:capability-parity-ledger
---

# Shadow Parity Accepted Classification Evidence - 2026-07-01

## Scope

This evidence records the local shadow parity reporting polish batch. The batch
keeps product ETHOS behavior generic while making cross-generation projection
differences explicit in `accepted_differences`.

Accepted classifications are limited to:

- `external_product_repository_audit_gap`: product repository audit maturation gaps reported
  by external ETHOS when the embedded adopter command has no corresponding
  required gap.
- `legacy_changed_route_noop`: legacy changed-scope playbook route gaps when
  the embedded route confirms `changed_path_count=0`.

These classifications do not hide command failures, embedded gaps, non-self-
audit proof gaps, mutation/admission gaps, or changed-scope route gaps with real
changed paths. Those remain blocking `shadow_diff:*` or command failure
packages.

## Contract

The accepted classification payload is schema checked by
`shadow-parity.schema.json`. The report-level `accepted_summary` records total
accepted difference count, affected command count, and counts by kind. Each
comparison records its own `accepted_summary` and full `accepted_differences`
records with command context, gap list, scope, classification, and reason.

## Local Evidence

The local adopter run for `/Users/yheng/projects/alphasim-dmgr-fix-b3` is
expected to produce:

```text
shadow_parity_digest: refreshed during final local closeout gate
state: matched
required_gaps: []
accepted_difference_kinds:
  - external_product_repository_audit_gap
  - legacy_changed_route_noop
```

Final closeout must refresh the command output and report the actual digest in
the operator response rather than treating this evidence page as remote
publication.
