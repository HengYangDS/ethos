# Proposal

## Why

A gate declaration names each provider as `ethos.<module>:<callable>`, so every registry pins
ETHOS's module layout. The shipped registries declare 21 such names; the adopter registries read on
2026-11-14 declare six of them, two more that name callables, and one that names none. Moving a
provider module would break each registry that names it, and the module-layout rule refuses the
alias module that would keep the old path alive.

The release-candidate plan orders the repair as row A14, `provider-ids`
(`openspec/changes/archive/2026-11-07-rc-plan/design.md`, Decision 2, Family 2, and Appendix A.4):
providers resolve by catalog ID, and a packaged data table maps each legacy name for one support
window. The release candidate gate that DR-0021 applies requires it as item R2, before the
application package's stability rule freezes the names that adopters declare
(`docs/decisions/dr-0021-release-scope-0-2-0.md`). The owner approved the release-candidate scope on
2026-11-14 with this row in the first weekly batch, 0.2.0-beta.11 of 2026-11-21.

## What Changes

- A gate declaration names a provider by a catalog ID of the form `provider.<name>`, such as
  `provider.docs-registry`. The packaged table `src/ethos/contracts/gate_providers.toml` maps each
  of its 23 IDs to an implementation.
- The same table maps 23 legacy names to their IDs. A legacy name keeps resolving for one support
  window and gives the same provider report; its gate's result carries the note
  `gate_provider_legacy_name`, which names the ID to declare and blocks nothing.
- A selected gate whose provider the catalog does not resolve refuses the proof with
  `gate_provider_unresolved:<gate>:<name>` before any gate runs.
- A repository that redeclares a shared gate by a legacy name composes with a packaged registry
  that names the ID.

This Change is not Breaking: both forms are accepted. Out of scope: the shipped registries
`system/gates.toml` and `system/repository-gates.toml` name IDs in the landing after this one, once
the installed runtime reads them; removing the legacy names is a later, Breaking Change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: ADDED requirement `Gate providers resolve by catalog ID`.

## Impact

`src/ethos/contracts/` (the table, its reader and the reference form of a declaration), the gate
runner and the policy readers that resolve or recognize a provider, `system/schemas/kernel/`,
their tests, `docs/reference/configuration.md`, `CHANGELOG.md` and `openspec/specs/quality/spec.md`
through this Change's delta.
