# Runtime Cache Boundary

## Why

`pytest.ini` previously directed pytest's runtime cache into
`.config/checks/pytest/.pytest_cache`. That made the configuration plane absorb
runtime working state. The state was ignored, but its physical placement taught
the wrong boundary and required a `.config/checks/pytest/.gitignore` sidecar.

ETHOS should keep the distinction small and mechanical: `.config/checks/**`
owns tool policy, `build/runtime/**` owns ignored tool caches and working state,
and `build/evidence/**` owns generated proof evidence awaiting review or
promotion.

## What Changes

- Move pytest's `cache_dir` to `build/runtime/tool-cache/pytest`.
- Remove the obsolete `.config/checks/pytest/.gitignore` sidecar.
- Extend the generated artifact topology contract to admit `build/runtime/` as
  ignored runtime/tool-cache state.
- Update docs, DR-0001, and OpenSpec quality requirements so the boundary is
  visible to humans, agents, and proof gates.
- Add architecture and unit tests that prevent pytest runtime cache from moving
  back under `.config/`.

## Capabilities

- `quality`: subject=runtime-cache-boundary; reuse=extend; change=modify;
  facet:lifecycle=validation; facet:surface=config,ci,docs,openspec,test;
  facet:authority=source,test,docs,openspec,claim,evidence

## Out Of Scope

- No new cache subsystem, truth store, command plane, or provider abstraction.
- No change to the Python test execution owner script or coverage/JUnit evidence
  paths beyond clarifying their boundaries.
- No rewrite of historical archive text solely to alter past command output.
