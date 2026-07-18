# CI Runner Boundary

## Why

`.config` is a configuration and provider-projection boundary, not an execution
home. Keeping executable quality runners under `.config/ci/scripts` makes the
repository shape teach the wrong thing: configuration, provider CI, and reusable
runner implementation appear to share one semantic owner.

ETHOS needs a smaller boundary: tool policy remains under `.config/checks/**`,
provider CI remains a projection, and reusable execution lives under `tools/ci`.
This removes the legacy review debt without adding a new command plane.

## What Changes

- Move reusable CI and quality runner shell scripts from `.config/ci/scripts/` to
  `tools/ci/scripts/`.
- Update gate registry, local fallback, hosted CI projection, hooks, tests,
  docs, skills, and active OpenSpec specs to reference the new execution owner.
- Keep tool-native configuration under `.config/checks/**`.
- Treat `.config/ci/**` as configuration or provider projection only, never as a
  script execution root.

## Capabilities

- `quality`: subject=ci-runner-boundary; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=ci,quality,config,tests,docs,skills; facet:authority=source,test,openspec
- `repository-governance`: subject=configuration-boundary; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=config,ci,tooling; facet:authority=docs,source,test,openspec

## Out Of Scope

- No new CI provider abstraction.
- No weakening of the active quality floor.
- No rewrite of historical evidence or archived OpenSpec records solely to alter
  past command text.
