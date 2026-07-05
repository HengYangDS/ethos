# Proposal: unbound-lane-retire

## Why

ETHOS status now exposes unbound Work Lane refs as advisory residue objects, but
maintainers still need a governed cleanup path. Raw `git branch -D` bypasses the
kernel loop: it does not prove the branch is unbound, does not bind the expected
HEAD, and does not record a reason.

## What Changes

- Add `ethos lane retire-unbound` as a maintainer command for local unbound
  Work Lane refs already visible in `data.coordination.unbound_work_lane_refs`.
- Require `--branch`, `--expect-head`, non-empty `--reason`, and `--authorize`
  when applying the deletion.
- Use a head-bound `git update-ref -d refs/heads/<branch> <expect-head>`
  transaction instead of force-deleting by name.
- Keep linked Work Lanes on `retire-landed`; this command does not remove
  worktrees and does not replace `ethos land`.

## Capabilities

- `ethos-repository`: subject=unbound-work-lane-ref-retirement; reuse=extend; change=add; facet:lifecycle=mutation; facet:surface=cli; facet:surface=git; facet:authority=source; facet:authority=test; facet:authority=evidence

## Out Of Scope

- No automatic deletion of unbound refs.
- No deletion of linked worktrees.
- No merge, supersede, or semantic conflict decision for diverged branches.
- No remote branch deletion.
