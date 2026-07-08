# Design

## Principle

Reveal closeout residue without creating a second lane lifecycle mechanism or a
new truth store. The source facts remain Git refs/worktrees, lane leases, claim
binding, dirty state, and accepted-root ancestry.

## Read Model

`workspace_status` adds two thin fields to each foreign Work Lane:

- `relation_to_accepted`: Git relation to accepted repository truth.
- `closeout_disposition`: one MECE disposition over existing facts:
  `none`, `retire_ready`, `landed_dirty`, `unlanded`, `diverged`, or `unknown`.

`coordination.advisory_gaps` keeps branch-level missing-lease visibility but
uses one coarse `work_lane_closeout_residue_present` signal for closeout
residue. Branch-specific disposition details stay on `foreign_work_lanes[]`.

## Non-Goals

- Do not authorize retiring foreign lanes.
- Do not make advisory residue a blocking report gap.
- Do not introduce a host chat, queue, database, package, or new command plane.
- Do not encode the entire read model as branch-level advisory gap strings.

## Sanctioned Replay Admission

`ethos lane refresh-base` is a Work Lane lifecycle transition. During Git
rebase, HEAD is temporarily detached, but Git records the original branch in
rebase `head-name`. Admission may derive the effective write role from that
metadata only when it names a configured `work/*` branch. The hook still checks
runtime binding, editor root, and target paths; detached replay for accepted,
candidate, submit, other, or unknown branches remains protected.
