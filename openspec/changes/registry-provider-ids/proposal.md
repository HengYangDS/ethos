# Proposal

## Why

The `provider-ids` Change added the gate provider catalog and kept the shipped registries on their
legacy `ethos.<module>:<callable>` names, because the runtime that judged its landing refused a
catalog ID in a registry. That Change is the release-candidate plan's row A14
(`openspec/changes/archive/2026-11-07-rc-plan/design.md`, Decision 2, Family 2), and this Change
completes the row once the installed runtime reads catalog IDs: until then every shipped gate
carries the note `gate_provider_legacy_name`, and each adopter's proof carries it for shared gates
that the adopter does not declare.

## What Changes

- `system/gates.toml` and `system/repository-gates.toml` name each of their 23 provider references
  by its catalog ID.
- The hosted proof wrapper reads the Python test gate's report under the ID that the registry now
  declares.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The requirement `Gate providers resolve by catalog ID` already states the rule, so
`skip_specs: true` applies.

## Impact

`system/gates.toml`, `system/repository-gates.toml`, `tools/ci/hosted_verification.py`, one comment
in `src/ethos/application/docs_registry.py`, two unit tests and a CHANGELOG line. A proof of a
shared gate records its provider under the catalog ID, so a proof made before this Change is stale.
