## Context

The canonical Work Lane coordination contract already permits bounded readers
to defer foreign path scopes and forbids them from inferring overlap, branch
relation, dirty foreign contents, or retirement readiness. `workspace_status`
knows whether the caller requested the full or bounded mode, but
`coordination_package` currently tries to recover that mode from projected lane
rows. An empty inventory removes the only row-level deferred marker, so the
aggregation incorrectly reports exact detail.

## Design

`coordination_package` will accept one keyword-only
`defer_details: bool = False` input. The default preserves the full reader.
`workspace_status` will pass
`defer_details=not include_foreign_path_scope`, making the caller-selected mode
the sole source for aggregate detail state.

When `defer_details` is true, `detail_state` remains `deferred` and these five
detail-dependent aggregates remain unknown even for an empty inventory:

- `dirty_foreign_work_lane_count`
- `overlap_count`
- `unknown_scope_count`
- `closeout_residue_count`
- `dirty_closeout_residue_count`

Observable topology signals such as foreign-lane and missing-lease counts remain
available. When `defer_details` is false, an empty full inventory remains exact
and all five detail-dependent aggregates are zero.

## Alternatives

- Continue deriving the mode with `any(lane.scope_state == "deferred")`:
  rejected because an empty list cannot preserve caller intent.
- Add a synthetic deferred lane row: rejected because it would falsify topology
  and corrupt observable lane counts.
- Change orientation tests to accept `exact`: rejected because the product
  contract requires bounded readers to preserve uncertainty rather than weaken
  the assertion.

## Proof Strategy

1. Add a zero-foreign-lane test that proves full mode is exact while bounded
   mode fails on the current `exact != deferred` behavior.
2. Implement only the explicit aggregation input and the caller wiring, then
   rerun the focused lane-status tests.
3. Run strict OpenSpec validation, lifecycle, claim/config lint, parity, and
   stable-HEAD proof before archive or integration.
4. Keep local proof, remote publication, and hosted CI as separate evidence
   planes.

## Rollback

Revert the bounded repair if full inventory output or schema validation changes.
Do not replace the repair by accepting fabricated exactness in bounded mode.
