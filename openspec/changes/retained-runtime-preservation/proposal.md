# Proposal

## Why

The retained-runtime qualification can miss staged-only and linked-worktree damage and cannot
observe a deleted tracked file. An adopter cutover needs preservation evidence for those real
states, not a successful command against one untracked file.

## What Changes

- Restore the normal upgrade and exact rollback portion of withdrawn `installed-product` task
  3.2, under DR-0016, through the existing package-acceptance owners.
- Seed a real owned linked fixture with staged, unstaged, deleted and untracked content.
- Compare native index semantics, file modes, Git bindings and user content at each transition.
- Qualify the exact successor against a distinct installed predecessor outside the source checkout.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This repairs verification of existing preservation requirements; `skip_specs: true` applies.

## Impact

The existing brownfield snapshot and retained-upgrade acceptance, their focused tests and evidence
projection change. Runtime activation, signing, project constraints and adopter source do not.

## Out of Scope

Interruption recovery, live-consumer-safe uninstall, new distribution channels and actual adopter
cutover retain their separate acceptance and authorization boundaries. This does not complete all
of withdrawn task 3.2.
