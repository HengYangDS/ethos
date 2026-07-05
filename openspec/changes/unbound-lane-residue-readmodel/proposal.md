## Why

`ethos status --json` surfaced unbound Work Lane refs only as a count and an
advisory gap. In multi-agent work this is not enough: agents need to know which
ref exists, what head it points at, whether it is ancestor/descendant/diverged
relative to accepted truth, and what kind of inspection is appropriate before
merge, supersede, or deletion.

## What Changes

- Add `data.coordination.unbound_work_lane_refs` to workspace status.
- Keep unbound refs advisory unless another gate proves they are blocking.
- Classify each unbound ref by relation to the accepted branch:
  `ancestor_of_accepted`, `descendant_of_accepted`, or `diverged_from_accepted`.
- Preserve existing branch bindings and counts for backward-readable status.

## Capabilities

- `ethos-repository`: subject=unbound-work-lane-residue-readmodel; reuse=extend;
  change=modify; facet:lifecycle=runtime,validation; facet:surface=cli,schema,test,openspec;
  facet:authority=source,schema,test,openspec,evidence,claim

## Out Of Scope

- Do not delete, merge, or supersede unbound refs automatically.
- Do not create a parallel lane lifecycle store.
- Do not treat unbound residue as blocking unless a separate policy proves it.
