## Why

ETHOS already exposes strong repository facts through `status --json` and
`report --json`, but the first human or agent question is still scattered:
where am I, can I write, who else is present, what is blocking, and what should I
run next. Hidden capability boundaries are especially costly in multi-agent
work, where visibility into a foreign lane must not imply write or retire
authority.

## What Changes

- Add `ethos orient` as a thin reader view over existing status and report facts.
- Keep `status --json` as the pure workspace-status contract while improving
  non-JSON status output through the same derived orientation view.
- Improve non-JSON `ethos status` output so humans see role, capability,
  coordination, readiness source, and next actions immediately.
- Document the orientation packet as a projection: it mints no truth and cannot
  satisfy proof or close gaps.

## Capabilities

- `ethos-repository`: subject=human-agent-orientation-readmodel; reuse=extend;
  change=add; facet:lifecycle=runtime,validation; facet:surface=cli,docs,openspec,test;
  facet:authority=source,test,docs,openspec,evidence

## Out Of Scope

- No new repository truth store.
- No host-specific message bus, UI state, or agent memory dependency.
- No change to land, publish, proof, or foreign Work Lane authority semantics.
- No replacement for `status --json`, `report --json`, or bound evidence.
