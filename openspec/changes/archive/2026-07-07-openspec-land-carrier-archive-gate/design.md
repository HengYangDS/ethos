# Design

Land is the transition from Work Lane authoring context into candidate truth.
Therefore the Work Lane may contain active OpenSpec carriers while authoring,
but `ethos land --apply` must require the carrier to be archived/fused first.

The implementation extends the existing `_openspec_carrier_gaps` admission helper
instead of adding a new mechanism:

- candidate/accepted-root roles keep using active-carrier role violations;
- Work Lane land admission emits `openspec_active_change_unarchived:<id>:work_lane`;
- completed active carriers retain `openspec_completed_change_unarchived:<id>` so
  the repair hint remains more precise.

This keeps OpenSpec a mandatory governance carrier, not a parallel truth center.
