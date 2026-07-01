## Why

Terminal ETHOS describes OpenSpec as the case and specification carrier, but
the lifecycle adapter only checked files and claim bindings. That allowed
active changes to omit product protocol metadata that routes ownership,
reuse stance, facets, and out-of-scope boundaries.

## What Changes

- Validate proposal capability entries during `ethos openspec --lifecycle`.
- Require each capability entry to resolve directly to a live
  `openspec/specs/<capability>/spec.md` and sibling `capability.toml`.
- Require subject, reuse stance, change direction, lifecycle facet, surface
  facet, and authority facet metadata.
- Require proposal out-of-scope boundaries.
- Keep OpenSpec as a mandatory governance dependency, not a second public
  command plane.

## Capabilities

- `ethos-adapters`: subject=openspec-product-protocol; reuse=extend;
  change=modify; facet:lifecycle=validation,runtime; facet:surface=cli;
  facet:authority=source,test,openspec
- `ethos-repository`: subject=openspec-product-protocol; reuse=extend;
  change=modify; facet:lifecycle=authoring,validation;
  facet:surface=docs,openspec,evidence; facet:authority=docs,openspec,claim,evidence

## Out Of Scope

- Do not archive existing active OpenSpec changes in this lane.
- Do not implement adopter scaffold generation.
- Do not replace the official OpenSpec CLI or create an OpenSpec public command
  plane outside `ethos ...`.
