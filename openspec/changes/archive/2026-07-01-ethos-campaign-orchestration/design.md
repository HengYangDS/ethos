## Context

Terminal ETHOS needs to complete a sequence of productization lanes: OpenSpec
protocol, archive closeout, hooked write admission, scaffolds, projection
digests, declarative gates, runtime topology, and release/evolution. A single
Work Lane would make this unreviewable and would blur proof boundaries.

The useful pattern from `reference adopter workspace` is not its domain vocabulary. The
portable lesson is that long-running objectives need a read-only adapter that
reports the current registry, the affected carriers, closeout state, and
evidence boundaries. ETHOS should express that through `campaign`, `OpenSpec`,
`Work Lane`, `claim`, and `evidence`, not through Backlog or Mission terms.

## Decision

Add a repository-native campaign manifest:

```text
evolution/campaigns/<campaign-id>/campaign.toml
```

The manifest records objective, owner, claim id, and ordered steps. Each step
names the OpenSpec change, Work Lane branch, claim id, and closeout state. The
manifest is not proof by itself; it is an orchestration record that makes the
next lane and residual work visible.

`ethos campaign status --json` reads campaign manifests and reports step
summary. `ethos campaign closeout --json` includes the same package beside the
existing local closeout, trust closeout, release, parity, and publication
packages. This keeps campaign a public ETHOS command-plane surface while leaving
promotion and closeout to normal Work Lane commands.

## Trade-offs

- A manifest can drift if it is not validated. Mitigation: add
  `campaign.schema.json` and include campaign data in closeout schema checks.
- Planned future lanes should not fail just because their OpenSpec carrier does
  not exist yet. Mitigation: carrier existence is required for active or
  non-planned steps, not for planned future steps.
- The manifest is manual in this change. Future lanes should update their own
  step state and can later add apply-mode campaign transitions.

## Rollback

Remove the campaign manifest, schema, CLI package wiring, and OpenSpec delta.
Existing hypothesis and closeout commands continue to work because this change
extends their payloads without replacing their current data sources.
