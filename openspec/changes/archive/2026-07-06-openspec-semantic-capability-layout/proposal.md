## Why

The accepted `openspec/specs` layout still used old implementation/package names
as capability IDs. That made OpenSpec look like a mirror of a retired package
ontology instead of a provider-neutral specification carrier for ETHOS product
semantics.

## What Changes

- Rename current OpenSpec capability directories from old `ethos-*` package-shaped
  IDs to semantic capability IDs.
- Keep the official OpenSpec shape `openspec/specs/<capability>/spec.md` intact;
  only the capability identity changes.
- Update capability profiles, scaffold defaults, repository audit requirements,
  tests, and templates so future adopters receive the semantic layout.
- Absorb the test-gate mechanisms that fit ETHOS from alternate mechanism corpus and reference-adopter:
  parallel-capable pytest, timeout protection, durations visibility, JUnit output,
  opt-in benchmark/reporting profiles, generated test artifacts under `build/evidence`,
  repository hygiene checks, and Google-style public docstring governance.
- Preserve package ownership as `owner.package` metadata instead of using package
  names as capability identity.

## Capabilities

- `repository-governance`: subject=openspec-semantic-capability-layout; reuse=extend; change=rename; facet:lifecycle=authoring,validation; facet:surface=openspec,scaffold,test; facet:authority=source,test,openspec
- `contracts`: subject=capability-profile-owner-boundary; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=schema,openspec; facet:authority=schema,openspec
- `quality`: subject=test-platform-hardening; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=ci,config,openspec,test; facet:authority=source,test,openspec

## Out Of Scope

- No nested non-OpenSpec directory shape under `openspec/specs`.
- No archive history rewrite.
- No broad rename of internal rule-owner strings that are not current OpenSpec
  capability IDs.
