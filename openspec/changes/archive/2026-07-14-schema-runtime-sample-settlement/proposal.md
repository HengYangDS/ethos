# Runtime Schema Sample Settlement

## Why

`ethos quality schemas` constructed nine synthetic contract payloads in product
runtime solely to validate schema shape. The samples duplicated producer
contracts, inflated product source, and could make schema validation appear
healthy without exercising real runtime output.

## What Changes

- Delete runtime-only synthetic schema sample builders and their report entries.
- Keep schema-file checks and validation of live repository producers.
- Move only focused acceptance/negative checks to their existing producer-owned
  tests; no shared replacement fixture is introduced.
- Repair historic promotion manifests that named the deleted implementation.

## Capabilities

- `quality`: subject=runtime-schema-sample-settlement; reuse=extend; change=remove; facet:lifecycle=validation,proof; facet:surface=schema,test,openspec,evidence; facet:authority=source,test,schema,openspec,claim,evidence

## Out Of Scope

- Schema format, JSON Schema validation behavior, or public command changes.
- Replacement of live producer validation with generated fixtures.
