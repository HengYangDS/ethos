# Tasks

## 1. Registries

- 1.1 Withdrawn by DR-0016 (environment). Name every provider reference of the two shipped
  registries by its catalog ID, and the hosted proof wrapper's probe with them. Done when the
  table-driven test that requires an ID for every shipped reference passes.

## 2. Lane acceptance

- [x] 2.1 Confirm that the installed runtime carries the provider catalog. Done when the installed
      runtime compiles the lane head's gate policy without `gate_registry_invalid`, and both proof
      floors have the digests that the lane compiles. Measured on 2026-11-15: the installed
      runtime predates the catalog and refused both ID-named registries, so the rename was
      reverted in this lane; with names, both interpreters compile both registries to equal
      digests.
- 2.2 Withdrawn by DR-0016 (environment). Pass the static precheck and readiness at the lane head
  with the registries named by ID.
- [x] 2.3 Close this Change on its delivered scope: DR-0016 withdraws 1.1 and 2.2 until the
      installed runtime is built from a head that holds the provider catalog. Evidence: the revert
      of the rename in this lane and its predecessor probe.

## Workflow follow-up

- After the lane that carries `provider-ids` has landed and the hook runtime is reinstalled from
  that head, a new Change renames the 23 provider references of the two shipped registries to
  their catalog IDs in its own lane, before the tag of the batch that carries it.
