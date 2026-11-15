# Proposal

## Why

`provider-ids` gave every gate provider a catalog ID and kept the module names resolving for one
support window. The Change that renamed the 23 provider references of the two shipped registries
closed under DR-0016: the installed hook runtime of that day predated the catalog and refused a
registry that names an ID, so the rename was reverted before any proof.

- The hook runtime is now installed from a head that holds the catalog.

## What Changes

- Name every provider reference of the two shipped registries, and the hosted proof wrapper's
  probe, by its catalog ID.
- The table-driven test that requires an ID for every shipped reference.
- Before the commit, a predecessor probe: the installed runtime compiles the lane head's gate
  policy to the digests that the lane compiles.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

`system/gates.toml`, `system/repository-gates.toml`, one probe and one test. It lands before the
tag of the batch that carries it.

Owner: the release lead. Next action: run the predecessor probe on the reinstalled runtime. Read
again: at the cut of 0.2.0-beta.12.
