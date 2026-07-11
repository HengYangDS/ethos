# lane-resolution-runtime-productization-20260711

## Why

Exceptional lane-resolution receipts currently leave the command response but
are not durably discoverable beside the retained recovery package. Retention
has no bounded manual-clear transition. Separately, a new Work Lane must rely
on an ad-hoc `uv run` invocation, which can create a root `.venv` and can run a
different checkout's installed CLI unless the operator knows the distinction.

## What Changes

- Materialize immutable, schema-validated lane-resolution receipts below the
  semantic local-artifact home and expose a read-only inventory of receipts,
  manifests, and cleared packages.
- Add a fail-closed manual-clear command for a retained preservation package;
  it requires an accepted Chronicle, exact manifest digest, break-glass, and
  irreversible confirmation.
- Make `ethos lane start` return a source-bound runner bootstrap contract.
  Add the repository-owned runner that places its uv environment under
  `build/runtime/venv` and uv cache under `build/runtime/tool-cache/uv`.
- Extend the generated-artifact topology, schemas, docs, OpenSpec, and tests
  together. Existing root `.venv` directories and retained packages are not
  deleted by this change.

## Capabilities

- `repository-governance`: subject=lane-resolution-runtime-productization;
  reuse=extend; change=modify; facet:lifecycle=work-lane-resolution,
  retention,runtime; facet:surface=cli,docs,schema,openspec,test,runner;
  facet:authority=source,test,schema,docs,openspec,chronicle

## Out of Scope

- No remote Git operation, hosted-CI claim, or publication.
- No automatic deletion or migration of existing recovery packages or legacy
  root virtual environments.
- No provider, model, or principal registry; holder references remain bounded
  lease facts.
